"""
Executor Logic

Handles start and resume flows for the Claude SDK executor.
Bridges invocation parsing (entry point) and SDK session execution (sdk_client).

Two-phase design:
  1. Mode-specific preparation (run_start / run_resume)
     - Resolves project_dir, api_url, and (for resume) executor_session_id
  2. Shared execution (_execute_session)
     - Extracts blueprint, formats prompt, calls SDK, outputs result
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import sys

from executor_config import load_config, get_api_url
from invocation import ExecutorInvocation
from sdk_client import run_session_sync, run_multi_turn_session_sync
from session_client import SessionClient, SessionClientError, SessionNotFoundError
from utils import debug_log, format_autonomous_inputs


@dataclass
class BlueprintData:
    """Fields extracted from agent_blueprint, with mode-aware defaults."""
    agent_name: Optional[str] = None
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict] = None
    has_custom_schema: bool = False
    output_schema: Optional[dict] = None


def _extract_blueprint(
    blueprint: Optional[dict], *,
    is_resume: bool = False,
    agent_name_fallback: Optional[str] = None,
) -> BlueprintData:
    """Extract agent blueprint fields for session execution.

    Args:
        blueprint: Raw agent_blueprint dict from invocation (may be None)
        is_resume: If True, skip system_prompt (only used for new sessions)
        agent_name_fallback: Default agent_name when blueprint doesn't provide one
    """
    data = BlueprintData(agent_name=agent_name_fallback)

    if not blueprint:
        return data

    data.agent_name = blueprint.get("name") or agent_name_fallback
    data.mcp_servers = blueprint.get("mcp_servers")
    data.has_custom_schema = blueprint.get("parameters_schema") is not None
    data.output_schema = blueprint.get("output_schema")

    if not is_resume:
        data.system_prompt = blueprint.get("system_prompt")

    debug_log("ao-claude-code-exec blueprint", {
        "agent_name": data.agent_name or "unnamed",
        "has_system_prompt": data.system_prompt is not None,
        "has_mcp_servers": data.mcp_servers is not None,
        "has_custom_schema": data.has_custom_schema,
        "has_output_schema": data.output_schema is not None,
    })

    return data


def _execute_session(
    inv: ExecutorInvocation, *,
    project_dir: Path,
    api_url: str,
    resume_executor_session_id: Optional[str] = None,
    agent_name_fallback: Optional[str] = None,
):
    """Shared execution path for both start and resume.

    1. Extract blueprint data (agent config, MCP servers, output schema)
    2. Format prompt per ADR-015 (custom schema -> <inputs> block)
    3. Run SDK session (binding, events, hooks handled by sdk_client)
    4. Output result to stdout
    """
    is_resume = resume_executor_session_id is not None

    blueprint = _extract_blueprint(
        inv.agent_blueprint,
        is_resume=is_resume,
        agent_name_fallback=agent_name_fallback,
    )

    formatted_prompt = format_autonomous_inputs(inv.parameters, blueprint.has_custom_schema)

    mode = "run_resume" if is_resume else "run_start"
    debug_log(f"ao-claude-code-exec {mode}", {
        "session_id": inv.session_id,
        "executor_session_id": resume_executor_session_id or "N/A",
        "project_dir": str(project_dir),
        "agent_name": blueprint.agent_name or "None",
        "has_system_prompt": blueprint.system_prompt is not None,
        "has_mcp_servers": blueprint.mcp_servers is not None,
        "has_custom_schema": blueprint.has_custom_schema,
        "prompt_length": len(formatted_prompt),
        "schema_version": inv.schema_version,
    })

    _, result = run_session_sync(
        prompt=formatted_prompt,
        project_dir=project_dir,
        session_id=inv.session_id,
        mcp_servers=blueprint.mcp_servers,
        resume_executor_session_id=resume_executor_session_id,
        api_url=api_url,
        agent_name=blueprint.agent_name,
        executor_config=inv.executor_config,
        system_prompt=blueprint.system_prompt,
        output_schema=blueprint.output_schema,
    )

    print(result)


def run_start(inv: ExecutorInvocation):
    """Start a new session.

    Resolves project_dir and api_url from configuration,
    then delegates to the shared execution path.

    Session is already created in coordinator with status='pending' (ADR-010).
    Executor binds to session after Claude SDK starts (handled by sdk_client).
    """
    config = load_config(cli_project_dir=inv.project_dir)

    _execute_session(
        inv,
        project_dir=config.project_dir,
        api_url=config.api_url,
    )


def run_resume(inv: ExecutorInvocation):
    """Resume an existing session.

    Fetches session data to get executor_session_id (needed for SDK resume)
    and project_dir, then delegates to the shared execution path.
    """
    api_url = get_api_url()

    try:
        client = SessionClient(api_url)
        session_data = client.get_session(inv.session_id)
    except SessionNotFoundError:
        raise ValueError(
            f"Resume failed: Session '{inv.session_id}' not found. "
            "The session may have been deleted or never created."
        )
    except SessionClientError as e:
        raise ValueError(
            f"Resume failed: Cannot connect to session manager for '{inv.session_id}'. "
            f"API URL: {api_url}. Error: {e}"
        )

    if not session_data:
        raise ValueError(
            f"Resume failed: Session '{inv.session_id}' returned empty data. "
            "Use mode='start' to create a new session."
        )

    executor_session_id = session_data.get("executor_session_id")
    session_status = session_data.get("status", "unknown")
    session_project_dir = Path(session_data.get("project_dir") or str(Path.cwd()))
    session_agent = session_data.get("agent_name")
    print(f"[DIAG] resume: fetched executor_session_id={executor_session_id} for session {inv.session_id}", file=sys.stderr)

    if not executor_session_id:
        raise ValueError(
            f"Resume failed: Session '{inv.session_id}' has no executor_session_id "
            f"(status={session_status}, agent={session_agent or 'none'}). "
            "The session may not have started successfully or was never bound to an executor."
        )

    _execute_session(
        inv,
        project_dir=session_project_dir,
        api_url=api_url,
        resume_executor_session_id=executor_session_id,
        agent_name_fallback=session_agent,
    )


def run_multi_turn(inv: ExecutorInvocation):
    """Start a multi-turn session.

    Keeps the ClaudeSDKClient alive across multiple turns, receiving
    subsequent turn requests via NDJSON on stdin and writing turn_complete
    messages to stdout.

    Resolves project_dir and api_url from configuration, then delegates
    to run_multi_turn_session_sync which handles the turn loop.
    """
    config = load_config(cli_project_dir=inv.project_dir)

    debug_log("ao-claude-code-exec run_multi_turn", {
        "session_id": inv.session_id,
        "project_dir": str(config.project_dir),
        "has_agent_blueprint": inv.agent_blueprint is not None,
    })

    run_multi_turn_session_sync(
        initial_invocation=inv,
        project_dir=config.project_dir,
        session_id=inv.session_id,
        api_url=config.api_url,
        executor_config=inv.executor_config,
    )
