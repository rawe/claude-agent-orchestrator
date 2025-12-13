"""
Claude SDK Integration

Wrapper around Claude Agent SDK for session creation and resumption.
Uses SessionClient for API-based session management.

NOTE: This module expects the launcher lib to already be in sys.path.
      The parent executor (ao-claude-code-exec) is responsible for
      setting up the path before importing this module.
"""

from pathlib import Path
from typing import Optional
import asyncio
import copy
import os
import re
from datetime import datetime, UTC

from session_client import SessionClient, SessionClientError


# =============================================================================
# MCP Config Placeholder Replacement
# =============================================================================

def _replace_env_placeholders(value: str) -> str:
    """
    Replace ${VAR_NAME} placeholders with environment variable values.

    If the environment variable is not set, the placeholder is left unchanged.
    """
    def replace_match(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(r'\$\{([^}]+)\}', replace_match, value)


def _process_mcp_servers(mcp_servers: dict) -> dict:
    """
    Process MCP server config to replace environment variable placeholders.

    Handles ${AGENT_SESSION_NAME} and similar placeholders in header values.
    Creates a deep copy to avoid modifying the original config.

    Example:
        Input:  {"headers": {"X-Agent-Session-Name": "${AGENT_SESSION_NAME}"}}
        Output: {"headers": {"X-Agent-Session-Name": "orchestrator"}}
    """
    result = copy.deepcopy(mcp_servers)

    for server_name, server_config in result.items():
        if isinstance(server_config, dict):
            # Process headers if present (HTTP servers)
            headers = server_config.get('headers')
            if isinstance(headers, dict):
                for header_name, header_value in headers.items():
                    if isinstance(header_value, str):
                        headers[header_name] = _replace_env_placeholders(header_value)

            # Process env if present (stdio servers)
            env = server_config.get('env')
            if isinstance(env, dict):
                for env_name, env_value in env.items():
                    if isinstance(env_value, str):
                        env[env_name] = _replace_env_placeholders(env_value)

    return result


# =============================================================================
# Module-level state for SDK hooks
# =============================================================================
_session_client: Optional[SessionClient] = None
_current_session_id: Optional[str] = None
_current_session_name: Optional[str] = None


def _set_hook_context(
    client: SessionClient,
    session_id: str,
    session_name: Optional[str] = None
) -> None:
    """Set the session context for hook functions."""
    global _session_client, _current_session_id, _current_session_name
    _session_client = client
    _current_session_id = session_id
    _current_session_name = session_name


# =============================================================================
# SDK Hook Functions
# =============================================================================

async def post_tool_hook(
    input_data: dict,
    tool_use_id: Optional[str],
    context: dict
) -> dict:
    """
    PostToolUse hook - sends post_tool event to session manager.
    """
    if _session_client and _current_session_id:
        try:
            _session_client.add_event(_current_session_id, {
                "event_type": "post_tool",
                "session_id": _current_session_id,
                "session_name": _current_session_name or _current_session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "tool_name": input_data.get("tool_name", "unknown"),
                "tool_input": input_data.get("tool_input", {}),
                "tool_output": input_data.get("tool_response", ""),
                "error": input_data.get("error"),
            })
        except SessionClientError:
            pass  # Silent failure - don't block agent execution
    return {}


async def run_claude_session(
    prompt: str,
    project_dir: Path,
    session_name: Optional[str] = None,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
    api_url: str = "http://127.0.0.1:8765",
    agent_name: Optional[str] = None,
) -> tuple[str, str]:
    """
    Run Claude session with API-based session management.

    This function uses the Claude Agent SDK to create or resume a session,
    with session state managed via the AgentRuntime API.

    NOTE: parent_session_name is now handled automatically by Agent Runtime
    via the Jobs API. The launcher sets AGENT_SESSION_NAME env var which
    flows through the job to the session. See mcp-server-api-refactor.md.

    Args:
        prompt: User prompt (may include prepended system prompt from agent)
        project_dir: Working directory for Claude (sets cwd)
        session_name: Session name for the session manager
        mcp_servers: MCP server configuration dict (from agent blueprint)
        resume_session_id: If provided, resume existing session
        api_url: Base URL of Agent Orchestrator API
        agent_name: Agent name (optional, for session metadata)

    Returns:
        Tuple of (session_id, result)

    Raises:
        ValueError: If session_id or result not found in messages
        ImportError: If claude-agent-sdk is not installed
        Exception: SDK errors are propagated

    Example:
        >>> project_dir = Path.cwd()
        >>> session_id, result = await run_claude_session(
        ...     prompt="What is 2+2?",
        ...     project_dir=project_dir,
        ...     session_name="test"
        ... )
    """
    # Create session client for API calls
    session_client = SessionClient(api_url)

    # Import SDK here to give better error message if not installed
    try:
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage, SystemMessage
    except ImportError as e:
        raise ImportError(
            "claude-agent-sdk is not installed. "
            "Commands using the SDK should have 'claude-agent-sdk' "
            "in their uv script header dependencies."
        ) from e

    # Build ClaudeAgentOptions
    options = ClaudeAgentOptions(
        cwd=str(project_dir.resolve()),
        permission_mode="bypassPermissions",
        setting_sources=["user", "project", "local"],
    )

    # Add programmatic hooks for post_tool events
    try:
        from claude_agent_sdk.types import HookMatcher

        options.hooks = {
            "PostToolUse": [
                HookMatcher(hooks=[post_tool_hook]),
            ],
        }
    except ImportError as e:
        # If HookMatcher is not available, continue without hooks
        import sys
        print(
            f"Warning: Could not import HookMatcher for hooks: {e}",
            file=sys.stderr
        )

    # Add resume session ID if provided
    if resume_session_id:
        options.resume = resume_session_id

    # Add MCP servers if provided (with placeholder replacement)
    if mcp_servers:
        options.mcp_servers = _process_mcp_servers(mcp_servers)

    # Initialize tracking variables
    session_id = None
    result = None

    # Stream session using ClaudeSDKClient
    try:
        async with ClaudeSDKClient(options=options) as client:
            # Send the query
            await client.query(prompt)

            # Stream messages from client
            async for message in client.receive_response():
                # Extract session_id from FIRST SystemMessage (arrives early!)
                # SystemMessage with subtype='init' contains session_id in data dict
                if isinstance(message, SystemMessage) and session_id is None:
                    # Extract session_id from SystemMessage.data
                    if message.subtype == 'init' and message.data:
                        extracted_session_id = message.data.get('session_id')
                        if extracted_session_id:
                            session_id = extracted_session_id

                            # Create or update session via API
                            try:
                                if not resume_session_id:
                                    # New session: create via API
                                    # NOTE: parent_session_name is set by Agent Runtime
                                    # from the Job's parent_session_name field
                                    session_client.create_session(
                                        session_id=session_id,
                                        session_name=session_name or session_id,
                                        project_dir=str(project_dir),
                                        agent_name=agent_name,
                                    )
                                else:
                                    # Resume: update last_resumed_at
                                    session_client.update_session(
                                        session_id=session_id,
                                        last_resumed_at=datetime.now(UTC).isoformat()
                                    )
                                    # Send session_start event to notify frontend of running state
                                    session_client.add_event(session_id, {
                                        "event_type": "session_start",
                                        "session_id": session_id,
                                        "session_name": session_name or session_id,
                                        "timestamp": datetime.now(UTC).isoformat(),
                                    })

                                # Set hook context so post_tool_hook can send events
                                _set_hook_context(
                                    session_client,
                                    session_id,
                                    session_name
                                )

                                # Send user message event
                                session_client.add_event(session_id, {
                                    "event_type": "message",
                                    "session_id": session_id,
                                    "session_name": session_name or session_id,
                                    "timestamp": datetime.now(UTC).isoformat(),
                                    "role": "user",
                                    "content": [{"type": "text", "text": prompt}]
                                })
                            except SessionClientError as e:
                                # Don't fail the session if API call fails
                                import sys
                                print(f"Warning: Session API error: {e}", file=sys.stderr)

                # Extract result from ResultMessage
                if isinstance(message, ResultMessage):
                    # Capture session_id if we somehow didn't get it from SystemMessage
                    if session_id is None:
                        session_id = message.session_id

                    # Capture result (overwrite each time to get final result)
                    result = message.result

                    # Send assistant message event to API
                    if message.result and session_id:
                        try:
                            session_client.add_event(session_id, {
                                "event_type": "message",
                                "session_id": session_id,
                                "session_name": session_name or session_id,
                                "timestamp": datetime.now(UTC).isoformat(),
                                "role": "assistant",
                                "content": [{"type": "text", "text": message.result}]
                            })
                        except SessionClientError:
                            pass  # Silent failure

            # Send session_stop event after message loop completes
            if session_id:
                try:
                    session_client.add_event(session_id, {
                        "event_type": "session_stop",
                        "session_id": session_id,
                        "session_name": session_name or session_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "exit_code": 0,
                        "reason": "completed"
                    })
                except SessionClientError:
                    pass  # Silent failure

    except Exception as e:
        # Propagate SDK errors with context
        raise Exception(f"Claude SDK error during session execution: {e}") from e

    # Validate we received required data
    if not session_id:
        raise ValueError(
            "No session_id received from Claude SDK. "
            "This may indicate an SDK version mismatch or API error."
        )

    if not result:
        raise ValueError(
            "No result received from Claude SDK. "
            "The session may have been interrupted or encountered an error."
        )

    return session_id, result


def run_session_sync(
    prompt: str,
    project_dir: Path,
    session_name: Optional[str] = None,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
    api_url: str = "http://127.0.0.1:8765",
    agent_name: Optional[str] = None,
) -> tuple[str, str]:
    """
    Synchronous wrapper for run_claude_session.

    This allows command scripts to remain synchronous while using
    the SDK's async API internally.

    NOTE: parent_session_name is now handled automatically by Agent Runtime
    via the Jobs API. See mcp-server-api-refactor.md.

    Args:
        prompt: User prompt (may include prepended system prompt from agent)
        project_dir: Working directory for Claude (sets cwd)
        session_name: Session name for the session manager
        mcp_servers: MCP server configuration dict (from agent blueprint)
        resume_session_id: If provided, resume existing session
        api_url: Base URL of Agent Orchestrator API
        agent_name: Agent name (optional, for session metadata)

    Returns:
        Tuple of (session_id, result)

    Raises:
        ValueError: If session_id or result not found in messages
        ImportError: If claude-agent-sdk is not installed
        Exception: SDK errors are propagated

    Example:
        >>> project_dir = Path.cwd()
        >>> session_id, result = run_session_sync(
        ...     prompt="What is 2+2?",
        ...     project_dir=project_dir,
        ...     session_name="test"
        ... )
    """
    return asyncio.run(
        run_claude_session(
            prompt=prompt,
            project_dir=project_dir,
            session_name=session_name,
            mcp_servers=mcp_servers,
            resume_session_id=resume_session_id,
            api_url=api_url,
            agent_name=agent_name,
        )
    )
