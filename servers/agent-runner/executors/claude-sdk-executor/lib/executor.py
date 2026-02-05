"""
Executor Logic

Handles start and resume flows for the Claude SDK executor.
Bridges invocation parsing (entry point) and SDK session execution (sdk_client).
"""

from pathlib import Path

from invocation import ExecutorInvocation
from sdk_client import run_session_sync
from utils import debug_log, format_autonomous_inputs


def run_start(inv: ExecutorInvocation):
    """
    Start a new session.

    Session is already created in coordinator with status='pending' (ADR-010).
    Executor binds to session after Claude SDK starts.

    Schema 2.0: Uses agent_blueprint directly (Runner handles fetching/resolution).

    For autonomous agents (ADR-015):
    - Without custom schema: prompt is passed directly to the agent
    - With custom schema: ALL parameters formatted as <inputs> block
    """
    from executor_config import load_config

    # 1. Load configuration
    config = load_config(
        cli_project_dir=inv.project_dir,
    )

    # 2. Get agent config from blueprint (Runner provides resolved blueprint)
    mcp_servers = None
    agent_name = None
    system_prompt = None
    has_custom_schema = False
    output_schema = None

    if inv.agent_blueprint:
        # Schema 2.0: Use resolved blueprint directly (no API call needed)
        agent_name = inv.agent_blueprint.get("name")
        system_prompt = inv.agent_blueprint.get("system_prompt")
        mcp_servers = inv.agent_blueprint.get("mcp_servers")
        # ADR-015: Check if agent has custom parameters_schema
        has_custom_schema = inv.agent_blueprint.get("parameters_schema") is not None
        # Output schema for structured JSON output validation
        output_schema = inv.agent_blueprint.get("output_schema")

        debug_log("ao-claude-code-exec using agent_blueprint", {
            "agent_name": agent_name or "unnamed",
            "has_system_prompt": system_prompt is not None,
            "has_mcp_servers": mcp_servers is not None,
            "has_custom_schema": has_custom_schema,
            "has_output_schema": output_schema is not None,
        })

    # 3. Format inputs based on schema presence (ADR-015)
    # - No schema: return prompt directly
    # - Custom schema: format ALL parameters as <inputs> block
    formatted_prompt = format_autonomous_inputs(inv.parameters, has_custom_schema)

    # DEBUG LOGGING
    debug_log("ao-claude-code-exec run_start", {
        "session_id": inv.session_id,
        "project_dir": str(config.project_dir),
        "agent_name": agent_name or "None",
        "has_system_prompt": system_prompt is not None,
        "has_mcp_servers": mcp_servers is not None,
        "has_custom_schema": has_custom_schema,
        "prompt_length": len(formatted_prompt),
        "schema_version": inv.schema_version,
    })

    # 4. Run Claude session (binds to coordinator session automatically)
    # Auth is handled by Agent Coordinator Proxy
    executor_session_id, result = run_session_sync(
        prompt=formatted_prompt,
        project_dir=config.project_dir,
        session_id=inv.session_id,
        mcp_servers=mcp_servers,
        api_url=config.api_url,
        agent_name=agent_name,
        executor_config=inv.executor_config,
        system_prompt=system_prompt,
        output_schema=output_schema,
    )

    # Print result to stdout
    print(result)


def run_resume(inv: ExecutorInvocation):
    """
    Resume an existing session.

    Fetches session affinity to get executor_session_id for Claude SDK resume.

    Schema 2.0: Uses agent_blueprint for MCP servers (Runner handles fetching/resolution).

    For autonomous agents (ADR-015):
    - Without custom schema: prompt is passed directly to the agent
    - With custom schema: ALL parameters formatted as <inputs> block
    """
    from executor_config import get_api_url
    from session_client import SessionClient, SessionClientError, SessionNotFoundError

    # 1. Get API URL (auth handled by Agent Coordinator Proxy)
    api_url = get_api_url()

    # 2. Get session and affinity data
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

    # Extract session data
    executor_session_id = session_data.get("executor_session_id")
    session_status = session_data.get("status", "unknown")
    # Use 'or' to handle both missing and explicitly None project_dir
    session_project_dir = Path(session_data.get("project_dir") or str(Path.cwd()))
    session_agent = session_data.get("agent_name")

    # Validate executor_session_id exists (needed for Claude SDK resume)
    if not executor_session_id:
        raise ValueError(
            f"Resume failed: Session '{inv.session_id}' has no executor_session_id "
            f"(status={session_status}, agent={session_agent or 'none'}). "
            "The session may not have started successfully or was never bound to an executor."
        )

    # 3. Get MCP servers from blueprint (Runner provides resolved blueprint)
    # NOTE: system_prompt is only passed for new sessions, not resume
    mcp_servers = None
    agent_name = session_agent
    has_custom_schema = False
    output_schema = None

    if inv.agent_blueprint:
        # Schema 2.0: Use resolved blueprint directly (no API call needed)
        mcp_servers = inv.agent_blueprint.get("mcp_servers")
        # Use agent name from blueprint if available, otherwise from session
        agent_name = inv.agent_blueprint.get("name") or session_agent
        # ADR-015: Check if agent has custom parameters_schema
        has_custom_schema = inv.agent_blueprint.get("parameters_schema") is not None
        # Output schema for structured JSON output validation
        output_schema = inv.agent_blueprint.get("output_schema")

        debug_log("ao-claude-code-exec resume using agent_blueprint", {
            "agent_name": agent_name or "None",
            "has_mcp_servers": mcp_servers is not None,
            "has_custom_schema": has_custom_schema,
            "has_output_schema": output_schema is not None,
        })

    # 4. Format inputs based on schema presence (ADR-015)
    # - No schema: return prompt directly
    # - Custom schema: format ALL parameters as <inputs> block
    formatted_prompt = format_autonomous_inputs(inv.parameters, has_custom_schema)

    # DEBUG LOGGING
    debug_log("ao-claude-code-exec run_resume", {
        "session_id": inv.session_id,
        "executor_session_id": executor_session_id,
        "project_dir": str(session_project_dir),
        "agent_name": agent_name or "None",
        "has_mcp_servers": mcp_servers is not None,
        "has_custom_schema": has_custom_schema,
        "prompt_length": len(formatted_prompt),
        "schema_version": inv.schema_version,
    })

    # 5. Run Claude session with resume (uses executor_session_id for SDK resume)
    # Auth is handled by Agent Coordinator Proxy
    # NOTE: system_prompt is not passed for resume - only for new sessions
    new_executor_session_id, result = run_session_sync(
        prompt=formatted_prompt,
        project_dir=session_project_dir,
        session_id=inv.session_id,
        mcp_servers=mcp_servers,
        resume_executor_session_id=executor_session_id,
        api_url=api_url,
        agent_name=agent_name,
        executor_config=inv.executor_config,
        output_schema=output_schema,
    )

    # Print result to stdout
    print(result)
