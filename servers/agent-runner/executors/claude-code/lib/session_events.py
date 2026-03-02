"""
Session Event Emission

Encapsulates all communication with the Runner Gateway for session lifecycle
events: binding, user/assistant messages, tool events, and results.

All event emission is fire-and-forget (silent failure) to avoid blocking
the agent execution loop.
"""

import sys
from typing import Optional
from datetime import datetime, UTC

from session_client import SessionClient, SessionClientError


class SessionEventEmitter:
    """Emits session events to the Runner Gateway via SessionClient.

    All methods are safe to call even if session_id is not yet known -
    they silently no-op. All SessionClientError exceptions are caught
    to prevent blocking agent execution.
    """

    def __init__(self, api_url: str, session_id: str):
        self._client = SessionClient(api_url)
        self._session_id = session_id
        self._bound = False

    @property
    def client(self) -> SessionClient:
        """Access the underlying SessionClient (for hook context)."""
        return self._client

    @property
    def session_id(self) -> str:
        return self._session_id

    def bind(self, executor_session_id: str, project_dir: str) -> bool:
        """Bind executor session to coordinator session (ADR-010). Returns True on success."""
        if self._bound:
            return True
        try:
            self._client.bind(
                session_id=self._session_id,
                executor_session_id=executor_session_id,
                project_dir=project_dir,
            )
            self._bound = True
            return True
        except SessionClientError as e:
            print(f"Warning: Session bind failed: {e}", file=sys.stderr)
            return False

    def update_resumed(self) -> None:
        """Update last_resumed_at timestamp for resumed sessions."""
        try:
            self._client.update_session(
                session_id=self._session_id,
                last_resumed_at=datetime.now(UTC).isoformat()
            )
        except SessionClientError as e:
            print(f"Warning: Session update failed: {e}", file=sys.stderr)

    def emit_user_message(self, prompt: str) -> None:
        """Emit a user message event."""
        try:
            self._client.add_event(self._session_id, {
                "event_type": "message",
                "session_id": self._session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            })
        except SessionClientError:
            pass

    def emit_assistant_message(self, text: str) -> None:
        """Emit an assistant message event (for conversation history)."""
        try:
            self._client.add_event(self._session_id, {
                "event_type": "message",
                "session_id": self._session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "role": "assistant",
                "content": [{"type": "text", "text": text}]
            })
        except SessionClientError:
            pass

    def emit_post_tool(self, input_data: dict) -> None:
        """Emit a post_tool event (called from SDK hook)."""
        try:
            self._client.add_event(self._session_id, {
                "event_type": "post_tool",
                "session_id": self._session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "tool_name": input_data.get("tool_name", "unknown"),
                "tool_input": input_data.get("tool_input", {}),
                "tool_output": input_data.get("tool_response", ""),
                "error": input_data.get("error"),
            })
        except SessionClientError:
            pass

    def emit_result(self, result_text: Optional[str] = None, result_data=None) -> None:
        """Emit a result event (text or structured data)."""
        try:
            self._client.add_event(self._session_id, {
                "event_type": "result",
                "session_id": self._session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "result_text": result_text,
                "result_data": result_data,
            })
        except SessionClientError:
            pass


# =============================================================================
# Module-level state for SDK post_tool hook
# =============================================================================
_emitter: Optional[SessionEventEmitter] = None


def set_hook_emitter(emitter: SessionEventEmitter) -> None:
    """Set the emitter for the post_tool hook function."""
    global _emitter
    _emitter = emitter


async def post_tool_hook(
    input_data: dict,
    tool_use_id: Optional[str],
    context: dict
) -> dict:
    """PostToolUse hook - sends post_tool event to session manager."""
    if _emitter:
        _emitter.emit_post_tool(input_data)
    return {}
