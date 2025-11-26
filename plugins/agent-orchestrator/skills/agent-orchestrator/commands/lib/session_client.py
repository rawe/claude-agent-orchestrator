"""
Session Client

HTTP client for Agent Session Manager API.
Replaces file-based session operations with API calls.
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
        session_name: str,
        project_dir: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new session with full metadata."""
        data = {
            "session_id": session_id,
            "session_name": session_name,
        }
        if project_dir is not None:
            data["project_dir"] = project_dir
        if agent_name is not None:
            data["agent_name"] = agent_name

        result = self._request("POST", "/sessions", json_data=data)
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
        session_name: Optional[str] = None,
        last_resumed_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update session metadata."""
        data = {}
        if session_name is not None:
            data["session_name"] = session_name
        if last_resumed_at is not None:
            data["last_resumed_at"] = last_resumed_at

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
