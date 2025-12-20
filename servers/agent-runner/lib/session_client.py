"""
Session Client

HTTP client for Agent Session Manager API.
Replaces file-based session operations with API calls.

Note: Uses session_id (coordinator-generated) per ADR-010.
"""

import httpx
from typing import Optional, List, Dict, Any


class SessionClientError(Exception):
    """Base exception for session client errors."""
    pass


class SessionNotFoundError(SessionClientError):
    """Session does not exist."""
    pass


class SessionClient:
    """HTTP client for Agent Session Manager API."""

    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request and handle errors."""
        url = f"{self.base_url}{path}"
        try:
            response = httpx.request(
                method=method,
                url=url,
                json=json_data,
                timeout=self.timeout
            )
            if response.status_code == 404:
                raise SessionNotFoundError(f"Session not found: {path}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise SessionClientError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise SessionClientError(f"Request failed: {e}")

    def create_session(
        self,
        session_id: str,
        project_dir: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create new session with full metadata.

        session_id is coordinator-generated (ADR-010).
        parent_session_id is set by Agent Coordinator from the Run.
        """
        data = {
            "session_id": session_id,
        }
        if project_dir is not None:
            data["project_dir"] = project_dir
        if agent_name is not None:
            data["agent_name"] = agent_name

        result = self._request("POST", "/sessions", json_data=data)
        return result.get("session", result)

    def bind_session_executor(
        self,
        session_id: str,
        executor_session_id: str,
        hostname: str,
        executor_type: str,
        project_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bind executor information to a session after framework starts.

        Called by executor after it gets the framework's session ID.
        Updates session status to 'running'.
        See ADR-010 for details.

        Args:
            session_id: Coordinator-generated session ID
            executor_session_id: Framework's session ID (e.g., Claude SDK UUID)
            hostname: Machine where session is running
            executor_type: Type of executor (e.g., "claude-code")
            project_dir: Optional project directory override

        Returns:
            Updated session dict
        """
        data = {
            "executor_session_id": executor_session_id,
            "hostname": hostname,
            "executor_type": executor_type,
        }
        if project_dir is not None:
            data["project_dir"] = project_dir

        result = self._request("POST", f"/sessions/{session_id}/bind", json_data=data)
        return result.get("session", result)

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details. Raises SessionNotFoundError if not found."""
        result = self._request("GET", f"/sessions/{session_id}")
        return result.get("session", result)

    def get_status(self, session_id: str) -> str:
        """Get session status: 'running', 'finished', or 'not_existent'."""
        result = self._request("GET", f"/sessions/{session_id}/status")
        return result.get("status", "not_existent")

    def get_result(self, session_id: str) -> str:
        """Get session result. Raises if not finished or not found."""
        result = self._request("GET", f"/sessions/{session_id}/result")
        return result.get("result", "")

    def get_affinity(self, session_id: str) -> Dict[str, Any]:
        """Get session affinity information for resume routing.

        Returns hostname, project_dir, executor_type, executor_session_id.
        """
        result = self._request("GET", f"/sessions/{session_id}/affinity")
        return result.get("affinity", {})

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        result = self._request("GET", "/sessions")
        return result.get("sessions", [])

    def add_event(self, session_id: str, event: Dict[str, Any]) -> None:
        """Add event to session. Handles session_stop specially on server."""
        # Ensure session_id is set in event
        event_data = dict(event)
        event_data["session_id"] = session_id
        self._request("POST", f"/sessions/{session_id}/events", json_data=event_data)

    def update_session(
        self,
        session_id: str,
        last_resumed_at: Optional[str] = None,
        executor_session_id: Optional[str] = None,
        executor_type: Optional[str] = None,
        hostname: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update session metadata."""
        data = {}
        if last_resumed_at is not None:
            data["last_resumed_at"] = last_resumed_at
        if executor_session_id is not None:
            data["executor_session_id"] = executor_session_id
        if executor_type is not None:
            data["executor_type"] = executor_type
        if hostname is not None:
            data["hostname"] = hostname

        result = self._request("PATCH", f"/sessions/{session_id}/metadata", json_data=data)
        return result.get("session", result)

    def delete_session(self, session_id: str) -> bool:
        """Delete session and events. Returns True if deleted, False if not found."""
        try:
            self._request("DELETE", f"/sessions/{session_id}")
            return True
        except SessionNotFoundError:
            return False


def get_client(base_url: str) -> SessionClient:
    """Get a SessionClient instance."""
    return SessionClient(base_url)
