"""
Session Client

HTTP client for executor-to-runner communication via the Runner Gateway.

Executors use this client to communicate with the Agent Coordinator through
the Runner Gateway. The gateway:
- Handles authentication (Auth0 M2M tokens)
- Enriches requests with runner-owned data (hostname, executor_profile)
- Routes requests to the appropriate Coordinator endpoints

Gateway endpoints:
- POST /bind      - Bind executor to session (gateway adds runner data)
- POST /events    - Add event to session
- PATCH /metadata - Update session metadata

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
        self._headers = {}

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
                headers=self._headers,
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

    def bind(
        self,
        session_id: str,
        executor_session_id: str,
        project_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bind executor to a session via the Runner Gateway.

        Called by executor after it gets the framework's session ID.
        The Runner Gateway enriches this request with runner-owned data
        (hostname, executor_profile) before forwarding to the Coordinator.

        Args:
            session_id: Coordinator-generated session ID
            executor_session_id: Framework's session ID (e.g., Claude SDK UUID)
            project_dir: Project directory (executor provides this per-invocation)

        Returns:
            Updated session dict
        """
        data = {
            "session_id": session_id,
            "executor_session_id": executor_session_id,
        }
        if project_dir is not None:
            data["project_dir"] = project_dir

        # Calls the Runner Gateway's /bind endpoint (not coordinator directly)
        result = self._request("POST", "/bind", json_data=data)
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

        Returns hostname, project_dir, executor_profile, executor_session_id.
        """
        result = self._request("GET", f"/sessions/{session_id}/affinity")
        return result.get("affinity", {})

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        result = self._request("GET", "/sessions")
        return result.get("sessions", [])

    def add_event(self, session_id: str, event: Dict[str, Any]) -> None:
        """Add event to session via the Runner Gateway.

        The gateway extracts session_id from the body to route to the
        correct coordinator endpoint: POST /sessions/{session_id}/events
        """
        # Ensure session_id is set in event
        event_data = dict(event)
        event_data["session_id"] = session_id
        # Calls the Runner Gateway's /events endpoint
        self._request("POST", "/events", json_data=event_data)

    def update_session(
        self,
        session_id: str,
        last_resumed_at: Optional[str] = None,
        executor_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update session metadata via the Runner Gateway.

        The gateway extracts session_id from the body to route to the
        correct coordinator endpoint: PATCH /sessions/{session_id}/metadata
        """
        data = {"session_id": session_id}
        if last_resumed_at is not None:
            data["last_resumed_at"] = last_resumed_at
        if executor_session_id is not None:
            data["executor_session_id"] = executor_session_id

        # Calls the Runner Gateway's /metadata endpoint
        result = self._request("PATCH", "/metadata", json_data=data)
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
