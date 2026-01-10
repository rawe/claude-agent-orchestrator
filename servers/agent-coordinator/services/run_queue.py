"""
Thread-safe run queue with write-through cache to SQLite.

Architecture:
- All writes go to database first, then update in-memory cache
- Reads come from cache for fast polling performance
- Active runs loaded from database on startup
- Terminal runs removed from cache (but remain in database)

Runs are created via POST /runs and claimed by the Runner via GET /runner/runs.
Supports demand-based matching per ADR-011.
Session ID is coordinator-generated at run creation per ADR-010.
Execution mode controls callback behavior per ADR-003.
"""

import json
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel

if TYPE_CHECKING:
    from models import RunnerDemands, ExecutionMode as ExecutionModeType
    from services.runner_registry import RunnerInfo

# Import ExecutionMode for runtime use
from models import ExecutionMode, Agent

# JSON Schema validation for parameters
from jsonschema import Draft7Validator

# Import database functions for persistence
from database import (
    create_run as db_create_run,
    get_run_by_id as db_get_run,
    get_run_by_session_id as db_get_run_by_session,
    get_all_runs as db_get_all_runs,
    get_active_runs as db_get_active_runs,
    update_run_status as db_update_run_status,
    claim_run as db_claim_run,
    update_run_demands as db_update_run_demands,
    fail_timed_out_runs as db_fail_timed_out_runs,
    get_session_by_id,
    recover_stale_runs as db_recover_stale_runs,
    recover_all_active_runs as db_recover_all_active_runs,
)


# ==============================================================================
# Parameter Validation (Phase 3: Schema Discovery & Validation)
# ==============================================================================

# Implicit schema for autonomous agents (no explicit parameters_schema)
# Ensures {"prompt": string} requirement for AI agents
IMPLICIT_AUTONOMOUS_SCHEMA = {
    "type": "object",
    "required": ["prompt"],
    "properties": {
        "prompt": {"type": "string", "minLength": 1}
    },
    "additionalProperties": False
}


class ParameterValidationError(Exception):
    """Raised when parameters don't match agent's parameters_schema."""

    def __init__(self, agent_name: str, errors: list, schema: dict):
        self.agent_name = agent_name
        self.errors = errors  # jsonschema ValidationError list
        self.schema = schema
        super().__init__(f"Parameter validation failed for agent '{agent_name}'")


def validate_parameters(parameters: dict, agent: Agent) -> None:
    """
    Validate parameters against agent's schema.

    For autonomous agents (ADR-015):
    - Without explicit parameters_schema: uses IMPLICIT_AUTONOMOUS_SCHEMA (prompt only)
    - With explicit parameters_schema: uses custom schema as-is (no implicit prompt)
      The custom schema is authoritative - if prompt is needed, the agent designer
      must include it in their schema.

    For procedural agents:
    - Uses the agent's parameters_schema directly

    Args:
        parameters: The parameters dict to validate
        agent: The agent whose schema to validate against

    Raises:
        ParameterValidationError: If parameters don't match schema
    """
    if agent.type == "procedural":
        # Procedural agents use their schema directly
        schema = agent.parameters_schema or {"type": "object", "additionalProperties": True}
    elif agent.parameters_schema:
        # Autonomous agent with custom schema - use as-is (ADR-015)
        # The custom schema is authoritative, no implicit prompt requirement
        schema = agent.parameters_schema
    else:
        # Autonomous agent without custom schema - use implicit schema
        schema = IMPLICIT_AUTONOMOUS_SCHEMA

    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(parameters))
    if errors:
        raise ParameterValidationError(agent.name, errors, schema)


# ==============================================================================
# Resume Run Enrichment
# ==============================================================================

def enrich_resume_run_create(run_create: "RunCreate") -> "RunCreate":
    """Enrich a resume run with data from its existing session.

    For RESUME_SESSION runs, looks up the session and populates
    agent_name and project_dir if not already provided in the request.

    This is THE centralized place where resume run enrichment happens.
    Called from add_run() to ensure all resume runs are properly enriched.

    Args:
        run_create: The run creation request to enrich

    Returns:
        The enriched run_create (modified in place, also returned for convenience)
    """
    # Only enrich resume runs
    if run_create.type != RunType.RESUME_SESSION:
        return run_create

    if not run_create.session_id:
        return run_create

    # Look up existing session
    existing_session = get_session_by_id(run_create.session_id)
    if not existing_session:
        return run_create

    # Enrich with session data (only if not already provided)
    if not run_create.agent_name:
        run_create.agent_name = existing_session.get("agent_name")
    if not run_create.project_dir:
        run_create.project_dir = existing_session.get("project_dir")

    return run_create


class RunType(str, Enum):
    START_SESSION = "start_session"
    RESUME_SESSION = "resume_session"


class RunStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    STOPPING = "stopping"  # Stop requested, waiting for runner
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"    # Successfully stopped


class RunCreate(BaseModel):
    """Request body for creating a new run.

    session_id is optional - coordinator generates it if not provided (ADR-010).
    execution_mode controls callback behavior per ADR-003.
    parameters is the unified input dict - for AI agents, use {"prompt": "..."}.
    """
    type: RunType
    session_id: Optional[str] = None  # Coordinator generates if not provided
    agent_name: Optional[str] = None
    parameters: dict  # Unified input - e.g., {"prompt": "..."} for AI agents
    project_dir: Optional[str] = None
    parent_session_id: Optional[str] = None
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    # Additional demands to merge with blueprint demands (additive only)
    additional_demands: Optional[dict] = None


class Run(BaseModel):
    """Full run representation."""
    run_id: str
    type: RunType
    session_id: str  # Coordinator-generated (ADR-010)
    agent_name: Optional[str] = None
    parameters: dict  # Unified input - e.g., {"prompt": "..."} for AI agents
    project_dir: Optional[str] = None
    parent_session_id: Optional[str] = None
    execution_mode: ExecutionMode = ExecutionMode.SYNC  # ADR-003
    # Merged demands (blueprint + additional) - stored as dict for serialization
    demands: Optional[dict] = None
    status: RunStatus = RunStatus.PENDING
    runner_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    claimed_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    # Timeout for no-match scenarios (ISO timestamp)
    timeout_at: Optional[str] = None

    @property
    def prompt(self) -> Optional[str]:
        """Helper to extract prompt from parameters (for AI agents)."""
        return self.parameters.get("prompt") if self.parameters else None


def generate_session_id() -> str:
    """Generate a coordinator session_id per ADR-010.

    Format: ses_{12-char-hex}
    Example: ses_abc123def456
    """
    return f"ses_{uuid.uuid4().hex[:12]}"


# Default timeout for runs waiting for a matching runner (5 minutes)
DEFAULT_NO_MATCH_TIMEOUT_SECONDS = 300


# Demand field names (matching RunnerDemands model in models.py)
class DemandFields:
    """Field names for demands matching."""
    HOSTNAME = "hostname"
    PROJECT_DIR = "project_dir"
    EXECUTOR_PROFILE = "executor_profile"
    EXECUTOR_TYPE = "executor_type"  # Must match agent type: "autonomous" | "procedural"
    TAGS = "tags"


def capabilities_satisfy_demands(
    runner: "RunnerInfo",
    demands: Optional[dict],
) -> bool:
    """
    Check if runner capabilities satisfy run demands.

    All specified demands must be met (hard requirements).
    Additionally, if runner.require_matching_tags is True, the run must have
    at least one tag that matches the runner's tags.
    See ADR-011 for details.

    Args:
        runner: Runner info with properties and tags
        demands: Demands dict with hostname, project_dir, executor_profile, tags

    Returns:
        True if runner satisfies all demands, False otherwise
    """
    if demands is None:
        # No demands - check require_matching_tags filter
        if runner.require_matching_tags:
            # Runner requires matching tags but run has no demands/tags
            return False
        return True

    # Property demands (exact match required)
    demanded_hostname = demands.get(DemandFields.HOSTNAME)
    if demanded_hostname and runner.hostname != demanded_hostname:
        return False

    demanded_project_dir = demands.get(DemandFields.PROJECT_DIR)
    if demanded_project_dir and runner.project_dir != demanded_project_dir:
        return False

    demanded_executor_profile = demands.get(DemandFields.EXECUTOR_PROFILE)
    if demanded_executor_profile and runner.executor_profile != demanded_executor_profile:
        return False

    # Executor type demand - must match runner's executor type (autonomous/procedural)
    # This ensures procedural runners only claim procedural agent runs
    demanded_executor_type = demands.get(DemandFields.EXECUTOR_TYPE)
    if demanded_executor_type:
        runner_executor_type = runner.executor.get("type") if runner.executor else None
        if runner_executor_type != demanded_executor_type:
            return False

    # Tag demands - runner must have ALL demanded tags
    demanded_tags = demands.get(DemandFields.TAGS, [])
    if demanded_tags:
        runner_tags = set(runner.tags or [])
        if not set(demanded_tags).issubset(runner_tags):
            return False

    # require_matching_tags - runner only accepts runs with matching tags
    if runner.require_matching_tags:
        run_tags = set(demands.get(DemandFields.TAGS, []))
        runner_tags = set(runner.tags or [])
        # Reject if run has no tags OR no intersection with runner tags
        if not run_tags or not run_tags.intersection(runner_tags):
            return False

    return True


class RunQueue:
    """
    Thread-safe run queue with write-through cache to SQLite.

    Architecture:
    - All writes go to database first, then update in-memory cache
    - Reads come from cache for fast polling performance
    - All runs loaded from database on startup
    """

    def __init__(self, recovery_mode: str = "stale"):
        """
        Initialize RunQueue with optional recovery.

        Args:
            recovery_mode: How to handle non-terminal runs from previous session
                - "none": Load as-is (may have stale claimed/running runs)
                - "stale": Recover runs older than 5 minutes (default)
                - "all": Aggressively recover all non-terminal runs
        """
        self._runs: dict[str, Run] = {}  # Cache for all runs
        self._lock = threading.Lock()

        # Run recovery before loading
        self._run_recovery(recovery_mode)

        # Load all runs from database
        self._load_runs()

    def _run_recovery(self, mode: str) -> None:
        """Handle recovery of stale runs from previous coordinator session."""
        if mode == "none":
            print("[RunQueue] Recovery disabled (mode=none)", flush=True)
            return

        if mode == "all":
            results = db_recover_all_active_runs()
            if any(results.values()):
                print(f"[RunQueue] Recovery (all): {results}", flush=True)
            else:
                print("[RunQueue] Recovery (all): No runs to recover", flush=True)
            return

        # Default: stale recovery
        results = db_recover_stale_runs(stale_threshold_seconds=300)
        if any(results.values()):
            print(f"[RunQueue] Recovery (stale): {results}", flush=True)
        else:
            print("[RunQueue] Recovery (stale): No stale runs to recover", flush=True)

    def _load_runs(self) -> None:
        """Load all runs from database into cache on startup."""
        all_runs = db_get_all_runs()
        for run_dict in all_runs:
            run = self._dict_to_run(run_dict)
            self._runs[run.run_id] = run

    def _dict_to_run(self, d: dict) -> Run:
        """Convert database dict to Run model."""
        return Run(
            run_id=d["run_id"],
            session_id=d["session_id"],
            type=RunType(d["type"]),
            agent_name=d.get("agent_name"),
            parameters=json.loads(d["parameters"]) if d.get("parameters") else {},
            project_dir=d.get("project_dir"),
            parent_session_id=d.get("parent_session_id"),
            execution_mode=ExecutionMode(d.get("execution_mode", "sync")),
            demands=json.loads(d["demands"]) if d.get("demands") else None,
            status=RunStatus(d["status"]),
            runner_id=d.get("runner_id"),
            error=d.get("error"),
            created_at=d["created_at"],
            claimed_at=d.get("claimed_at"),
            started_at=d.get("started_at"),
            completed_at=d.get("completed_at"),
            timeout_at=d.get("timeout_at"),
        )

    def add_run(self, run_create: RunCreate) -> Run:
        """Create a new run. Persists to database, then updates cache.

        If session_id is not provided, generates one per ADR-010.
        For resume runs, enriches with agent_name/project_dir via enrich_resume_run_create().
        """
        # Enrich resume runs with session data (centralized enrichment)
        enrich_resume_run_create(run_create)

        with self._lock:
            # Generate IDs
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            session_id = run_create.session_id or generate_session_id()
            created_at = datetime.now(timezone.utc).isoformat()

            # Write to database first
            db_create_run(
                run_id=run_id,
                session_id=session_id,
                run_type=run_create.type.value,
                parameters=json.dumps(run_create.parameters),
                created_at=created_at,
                agent_name=run_create.agent_name,
                project_dir=run_create.project_dir,
                parent_session_id=run_create.parent_session_id,
                execution_mode=run_create.execution_mode.value,
                status=RunStatus.PENDING.value,
            )

            # Create Run model for cache
            run = Run(
                run_id=run_id,
                session_id=session_id,
                type=run_create.type,
                agent_name=run_create.agent_name,
                parameters=run_create.parameters,
                project_dir=run_create.project_dir,
                parent_session_id=run_create.parent_session_id,
                execution_mode=run_create.execution_mode,
                status=RunStatus.PENDING,
                created_at=created_at,
            )

            # Update cache
            self._runs[run_id] = run
            return run

    def claim_run(self, runner: "RunnerInfo") -> Optional[Run]:
        """
        Claim the first pending run matching runner's capabilities.
        Uses database for atomic claim to prevent race conditions.

        Args:
            runner: The runner attempting to claim a run

        Returns:
            The claimed run or None if no matching pending runs.
        """
        with self._lock:
            claimed_at = datetime.now(timezone.utc).isoformat()

            # Find first pending run in cache that matches demands
            for run in self._runs.values():
                if run.status != RunStatus.PENDING:
                    continue
                if not capabilities_satisfy_demands(runner, run.demands):
                    continue

                # Try to claim in database (atomic)
                if db_claim_run(run.run_id, runner.runner_id, claimed_at):
                    # Success - update cache
                    run.status = RunStatus.CLAIMED
                    run.runner_id = runner.runner_id
                    run.claimed_at = claimed_at
                    return run
                else:
                    # Someone else claimed it - remove from cache (stale)
                    # This shouldn't happen with single coordinator, but be safe
                    del self._runs[run.run_id]

            return None

    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by ID. Reads from cache for speed."""
        with self._lock:
            return self._runs.get(run_id)

    def remove_runs_for_session(self, session_id: str) -> int:
        """Remove all runs for a session from cache.

        Called when session is deleted to keep cache synchronized with DB.
        Returns count of removed runs.
        """
        with self._lock:
            run_ids_to_remove = [
                run_id for run_id, run in self._runs.items()
                if run.session_id == session_id
            ]

            for run_id in run_ids_to_remove:
                del self._runs[run_id]

            return len(run_ids_to_remove)

    def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        error: Optional[str] = None,
    ) -> Optional[Run]:
        """Update run status. Persists to database, then updates cache."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return None

            # Determine timestamps based on status transition
            started_at = None
            completed_at = None
            now = datetime.now(timezone.utc).isoformat()

            if status == RunStatus.RUNNING:
                started_at = now
            elif status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.STOPPED):
                completed_at = now

            # Write to database first
            success = db_update_run_status(
                run_id=run_id,
                status=status.value,
                error=error,
                started_at=started_at,
                completed_at=completed_at,
            )

            if not success:
                return None

            # Update cache
            run.status = status
            if error:
                run.error = error
            if started_at:
                run.started_at = started_at
            if completed_at:
                run.completed_at = completed_at

            return run

    def get_pending_runs(self) -> list[Run]:
        """Get all pending runs. Reads from cache."""
        with self._lock:
            return [r for r in self._runs.values() if r.status == RunStatus.PENDING]

    def get_all_runs(self) -> list[Run]:
        """Get all runs in cache (active runs only)."""
        with self._lock:
            return list(self._runs.values())

    def get_run_by_session_id(self, session_id: str) -> Optional[Run]:
        """Find active run by session ID. Reads from cache."""
        with self._lock:
            for run in self._runs.values():
                if run.session_id == session_id:
                    return run
            return None

    def fail_timed_out_runs(self) -> list[Run]:
        """Check for and fail any pending runs past their timeout."""
        with self._lock:
            current_time = datetime.now(timezone.utc).isoformat()

            # Use database to find and fail timed out runs
            failed_run_ids = db_fail_timed_out_runs(current_time)

            # Update cache for failed runs
            failed_runs = []
            for run_id in failed_run_ids:
                run = self._runs.get(run_id)
                if run:
                    run.status = RunStatus.FAILED
                    run.error = "No matching runner available within timeout"
                    run.completed_at = current_time
                    failed_runs.append(run)

            return failed_runs

    def set_run_demands(
        self,
        run_id: str,
        demands: Optional[dict],
        timeout_seconds: int = DEFAULT_NO_MATCH_TIMEOUT_SECONDS,
    ) -> Optional[Run]:
        """Set run demands and timeout. Persists to database, then updates cache."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return None

            # Calculate timeout
            timeout_at = None
            if demands and not all(v is None or v == [] for v in demands.values()):
                timeout_at = (
                    datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)
                ).isoformat()

            # Write to database first
            demands_json = json.dumps(demands) if demands else None
            success = db_update_run_demands(run_id, demands_json, timeout_at)

            if not success:
                return None

            # Update cache
            run.demands = demands
            run.timeout_at = timeout_at

            return run

    def get_all_runs_from_db(self, status_filter: Optional[list[str]] = None) -> list[Run]:
        """Get all runs from database (including completed). For historical queries."""
        run_dicts = db_get_all_runs(status_filter)
        return [self._dict_to_run(d) for d in run_dicts]

    def get_run_with_fallback(self, run_id: str) -> Optional[Run]:
        """Get run from cache, falling back to database for completed runs.

        Active runs are served from cache for fast performance.
        Completed runs (removed from cache) are fetched from database.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run:
                return run

        # Check database for completed runs
        run_dict = db_get_run(run_id)
        if run_dict:
            return self._dict_to_run(run_dict)

        return None


# Module-level singleton (initialized lazily via init_run_queue)
run_queue: RunQueue = None  # type: ignore


def init_run_queue(recovery_mode: str = "stale") -> RunQueue:
    """
    Initialize the module-level run_queue singleton.

    Must be called once at startup before using run_queue.
    Should be called after init_db() to ensure database tables exist.

    Args:
        recovery_mode: How to handle non-terminal runs from previous session
            - "none": Load as-is (may have stale claimed/running runs)
            - "stale": Recover runs older than 5 minutes (default)
            - "all": Aggressively recover all non-terminal runs

    Returns:
        The initialized RunQueue instance
    """
    global run_queue
    if run_queue is not None:
        return run_queue  # Idempotent: return existing instance (handles uvicorn reload)
    run_queue = RunQueue(recovery_mode=recovery_mode)
    return run_queue
