"""
Run Demands Service - computes and sets demands for agent runs.

Centralizes the demands computation logic that ensures runs are routed
to the correct runner based on:
- Executor type (autonomous/procedural)
- Session affinity (for resume runs)
- Blueprint demands (from agent definition)
- Script demands (if agent references a script)
- Runner owner demands (for runner-owned agents)
- Additional demands (from request)

This module is called by both:
- POST /runs endpoint (for API-created runs)
- Callback processor (for callback-created resume runs)
"""

import logging
import os
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.run_queue import Run

from models import RunnerDemands
from database import get_session_by_id
import agent_storage
import script_storage
from services.runner_registry import runner_registry

logger = logging.getLogger(__name__)

# Debug logging toggle
DEBUG = os.getenv("DEBUG_LOGGING", "").lower() in ("true", "1", "yes")

# Default timeout for runs waiting for a matching runner (5 minutes)
DEFAULT_NO_MATCH_TIMEOUT_SECONDS = 300


def _agent_from_runner_data(agent_data: dict) -> "agent_storage.Agent":
    """Convert runner-owned agent dict to Agent model.

    Runner-owned agents are stored as dicts in the runner registry.
    This converts them to the Agent model format for uniform handling.
    """
    from models import Agent
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    return Agent(
        name=agent_data["name"],
        description=agent_data.get("description", ""),
        type="procedural",  # Runner-owned agents are always procedural
        command=agent_data.get("command"),
        parameters_schema=agent_data.get("parameters_schema"),
        output_schema=agent_data.get("output_schema"),
        runner_id=agent_data.get("runner_id"),
        created_at=now,
        modified_at=now,
    )


def compute_and_set_run_demands(
    run: "Run",
    additional_demands: Optional[dict] = None,
    timeout_seconds: int = DEFAULT_NO_MATCH_TIMEOUT_SECONDS,
) -> Optional[dict]:
    """
    Compute and set demands for a run after creation.

    This function handles all demand sources and merges them according to
    priority rules defined in ADR-011:

    Priority (highest to lowest):
    1. Runner owner demands (for runner-owned procedural agents)
    2. Session affinity (hostname, executor_profile for resume runs)
    3. Blueprint demands (from agent definition)
    4. Script demands (if agent references a script)
    5. Executor type demand (from agent.type or default "autonomous")
    6. Additional demands (from request)

    Args:
        run: The created Run object (needs run_id, session_id, type, agent_name)
        additional_demands: Extra demands dict from the request (optional)
        timeout_seconds: Timeout for no-match scenarios (default 5 minutes)

    Returns:
        The merged demands dict if any demands were set, None otherwise
    """
    # Lazy import to avoid issues with run_queue singleton initialization
    from services.run_queue import run_queue, RunType

    # Initialize all demand components as empty
    runner_owner_demands = RunnerDemands()
    affinity_demands = RunnerDemands()
    blueprint_demands = RunnerDemands()
    script_demands = RunnerDemands()
    additional_demands_obj = RunnerDemands()

    # Look up agent by name (file-based or runner-owned)
    agent = None
    if run.agent_name:
        agent = agent_storage.get_agent(run.agent_name)
        # Check runner-owned agents if not found in file-based
        if not agent:
            runner_agent_result = runner_registry.get_runner_agent_by_name(run.agent_name)
            if runner_agent_result:
                agent_data, runner_id = runner_agent_result
                agent_data_with_runner = {**agent_data, "runner_id": runner_id}
                agent = _agent_from_runner_data(agent_data_with_runner)

    # Look up script if agent references one
    script = None
    if agent and agent.script:
        script = script_storage.get_script(agent.script)

    # For RESUME_SESSION, compute affinity demands from existing session
    # This ensures resume runs go to the same runner that owns the session
    if run.type == RunType.RESUME_SESSION:
        existing_session = get_session_by_id(run.session_id)
        if existing_session:
            affinity_demands = RunnerDemands(
                hostname=existing_session.get('hostname'),
                executor_profile=existing_session.get('executor_profile'),
            )
            if DEBUG:
                logger.debug(
                    f"Resume run {run.run_id}: enforcing affinity demands "
                    f"hostname={existing_session.get('hostname')}, "
                    f"executor_profile={existing_session.get('executor_profile')}"
                )

    # For runner-owned agents, route to the owning runner
    if agent and agent.runner_id:
        runner = runner_registry.get_runner(agent.runner_id)
        if runner:
            runner_owner_demands = RunnerDemands(
                hostname=runner.hostname,
                project_dir=runner.project_dir,
                executor_profile=runner.executor_profile,
            )
            if DEBUG:
                logger.debug(
                    f"Run {run.run_id}: routing to runner {agent.runner_id} "
                    f"(procedural agent '{agent.name}')"
                )
        else:
            # Runner is offline - run will fail after timeout
            if DEBUG:
                logger.debug(
                    f"Run {run.run_id}: runner {agent.runner_id} not online "
                    f"(procedural agent '{agent.name}')"
                )

    # Load blueprint demands from agent
    if agent and agent.demands:
        blueprint_demands = agent.demands

    # Load script demands
    if script and script.demands:
        script_demands = script.demands
        if DEBUG:
            logger.debug(
                f"Run {run.run_id}: script '{script.name}' has demands: "
                f"{script.demands.model_dump(exclude_none=True)}"
            )

    # Merge script demands into blueprint demands (combined tags)
    blueprint_demands = RunnerDemands.merge(script_demands, blueprint_demands)

    # Parse additional_demands from request
    if additional_demands:
        additional_demands_obj = RunnerDemands(**additional_demands)

    # Determine required executor type based on agent type
    # This ensures procedural runners only claim procedural agent runs
    # and autonomous runners only claim autonomous agent runs
    if agent:
        required_executor_type = agent.type  # "autonomous" or "procedural"
    else:
        # No agent specified - default to autonomous (AI agents)
        required_executor_type = "autonomous"

    # Create executor_type demand
    executor_type_demands = RunnerDemands(executor_type=required_executor_type)

    # Merge demands with priority:
    # runner_owner > affinity > blueprint > executor_type > additional
    merged_demands = RunnerDemands.merge(
        RunnerDemands.merge(
            RunnerDemands.merge(
                RunnerDemands.merge(runner_owner_demands, affinity_demands),
                blueprint_demands
            ),
            executor_type_demands
        ),
        additional_demands_obj
    )

    # Only store and set timeout if there are actual demands
    if not merged_demands.is_empty():
        demands_dict = merged_demands.model_dump(exclude_none=True)
        run_queue.set_run_demands(
            run.run_id,
            demands_dict,
            timeout_seconds=timeout_seconds,
        )
        if DEBUG:
            logger.debug(f"Run {run.run_id} has demands: {demands_dict}")
        return demands_dict

    return None
