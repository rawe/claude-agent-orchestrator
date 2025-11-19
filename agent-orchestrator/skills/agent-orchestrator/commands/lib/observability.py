"""
Observability Client

Thin HTTP client for sending events to the observability backend.
Matches the API contract used by the hook scripts.

Also contains SDK hook functions for observability integration.
"""

import httpx
from datetime import datetime, UTC
from typing import Any, Optional


# Module-level variable to store observability URL for hooks
_observability_url: str = "http://127.0.0.1:8765"


def set_observability_url(url: str) -> None:
    """Set the observability URL used by hook functions."""
    global _observability_url
    _observability_url = url


def get_observability_url() -> str:
    """Get the current observability URL."""
    return _observability_url


def send_event(base_url: str, event: dict) -> None:
    """
    Send event to observability backend. Fails silently.

    Args:
        base_url: Base URL of observability backend (e.g., http://127.0.0.1:8765)
        event: Event dictionary matching the API schema
    """
    try:
        httpx.post(
            f"{base_url}/events",
            json=event,
            timeout=2.0
        )
    except Exception:
        # Silent failure - don't block agent execution
        pass


def send_session_start(base_url: str, session_id: str) -> None:
    """Send session_start event."""
    send_event(base_url, {
        "event_type": "session_start",
        "session_id": session_id,
        "session_name": session_id,  # Use session_id as name (matching hooks)
        "timestamp": datetime.now(UTC).isoformat(),
    })


def send_pre_tool(
    base_url: str,
    session_id: str,
    tool_name: str,
    tool_input: dict
) -> None:
    """Send pre_tool event."""
    send_event(base_url, {
        "event_type": "pre_tool",
        "session_id": session_id,
        "session_name": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "tool_name": tool_name,
        "tool_input": tool_input,
    })


def send_post_tool(
    base_url: str,
    session_id: str,
    tool_name: str,
    tool_input: dict,
    tool_output: Any,
    error: Optional[str] = None
) -> None:
    """Send post_tool event."""
    send_event(base_url, {
        "event_type": "post_tool",
        "session_id": session_id,
        "session_name": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "error": error,
    })


def send_message(
    base_url: str,
    session_id: str,
    role: str,
    content: list
) -> None:
    """Send message event."""
    send_event(base_url, {
        "event_type": "message",
        "session_id": session_id,
        "session_name": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "role": role,
        "content": content,
    })


def send_session_stop(
    base_url: str,
    session_id: str,
    exit_code: int = 0,
    reason: str = "completed"
) -> None:
    """Send session_stop event."""
    send_event(base_url, {
        "event_type": "session_stop",
        "session_id": session_id,
        "session_name": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "exit_code": exit_code,
        "reason": reason,
    })


def update_session_metadata(
    base_url: str,
    session_id: str,
    session_name: Optional[str] = None,
    project_dir: Optional[str] = None
) -> None:
    """
    Update session metadata (name and/or project directory).

    Sends a PATCH request to /sessions/{session_id}/metadata.
    At least one of session_name or project_dir should be provided.

    Args:
        base_url: Base URL of observability backend (e.g., http://127.0.0.1:8765)
        session_id: Claude session ID
        session_name: Human-readable session name (optional)
        project_dir: Project directory path (optional)
    """
    # Build request body with only provided fields
    metadata = {}
    if session_name is not None:
        metadata["session_name"] = session_name
    if project_dir is not None:
        metadata["project_dir"] = project_dir

    # Skip if no metadata to update
    if not metadata:
        return

    try:
        httpx.patch(
            f"{base_url}/sessions/{session_id}/metadata",
            json=metadata,
            timeout=2.0
        )
    except Exception:
        # Silent failure - don't block agent execution
        pass


# =============================================================================
# SDK Hook Functions
#
# These async functions are registered with ClaudeAgentOptions.hooks to capture
# observability events during session execution.
# =============================================================================


# NOTE: SessionStart hook is defined but not used.
# The Claude Agent SDK does not call the SessionStart hook when using ClaudeSDKClient.
# Instead, we send the session_start event from the message loop when we first
# receive a ResultMessage with a session_id. See claude_client.run_claude_session().
# Keeping this function for reference in case SDK behavior changes in the future.
async def session_start_hook(
    input_data: dict,
    tool_use_id: Optional[str],
    context: dict
) -> dict:
    """
    SessionStart hook - sends session_start event to observability backend.

    NOTE: This hook is not called by the SDK. Session start is handled
    in the message loop as a fallback.
    """
    session_id = input_data.get("session_id", "unknown")
    send_session_start(_observability_url, session_id)
    return {}


# Track if session_start has been sent (per-process)
_session_started: bool = False


async def user_prompt_hook(
    input_data: dict,
    tool_use_id: Optional[str],
    context: dict
) -> dict:
    """
    UserPromptSubmit hook - sends session_start and user message events.

    This is the first hook called, so we send session_start here since
    the SessionStart hook is not called by the SDK.
    """
    global _session_started
    session_id = input_data.get("session_id", "unknown")
    prompt = input_data.get("prompt", "")

    # Send session_start on first prompt (since SessionStart hook doesn't fire)
    if not _session_started:
        send_session_start(_observability_url, session_id)
        _session_started = True

    send_message(
        _observability_url,
        session_id,
        "user",
        [{"type": "text", "text": prompt}]
    )
    return {}


async def pre_tool_hook(
    input_data: dict,
    tool_use_id: Optional[str],
    context: dict
) -> dict:
    """
    PreToolUse hook - sends pre_tool event to observability backend.
    """
    session_id = input_data.get("session_id", "unknown")
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    send_pre_tool(_observability_url, session_id, tool_name, tool_input)
    return {}


async def post_tool_hook(
    input_data: dict,
    tool_use_id: Optional[str],
    context: dict
) -> dict:
    """
    PostToolUse hook - sends post_tool event to observability backend.
    """
    session_id = input_data.get("session_id", "unknown")
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})
    tool_response = input_data.get("tool_response", "")
    error = input_data.get("error")

    send_post_tool(
        _observability_url,
        session_id,
        tool_name,
        tool_input,
        tool_response,
        error
    )
    return {}


# NOTE: Stop hook is defined but not used.
# The SDK's Stop hook fires before the message loop completes, which causes
# session_stop to be sent before the assistant message. Instead, we send
# session_stop manually from the message loop after all messages are processed.
# See claude_client.run_claude_session().
# Keeping this function for reference in case SDK behavior changes in the future.
async def session_stop_hook(
    input_data: dict,
    tool_use_id: Optional[str],
    context: dict
) -> dict:
    """
    Stop hook - sends session_stop event to observability backend.

    NOTE: This hook is not used. Session stop is sent manually from the
    message loop to ensure correct event order.
    """
    session_id = input_data.get("session_id", "unknown")
    send_session_stop(_observability_url, session_id)
    return {}
