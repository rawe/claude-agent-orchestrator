"""
Async HTTP Client for Agent Coordinator API.

Provides async methods for calling the Coordinator API with Auth0 token injection.
Used by MCP tools to forward requests to the Coordinator.
"""

import asyncio
import logging
import time
from typing import Optional, Any, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from auth0_client import Auth0M2MClient

logger = logging.getLogger(__name__)


class CoordinatorClientError(Exception):
    """Error communicating with Agent Coordinator."""
    pass


class RunTimeoutError(CoordinatorClientError):
    """Run did not complete within timeout."""
    pass


class RunFailedError(CoordinatorClientError):
    """Run failed to execute."""
    pass


class CoordinatorClient:
    """
    Async HTTP client for Agent Coordinator API.

    Injects Bearer token from Auth0 client when available.
    All methods are async for use with FastMCP.

    IMPORTANT: This client reuses the Auth0 client instance from the parent
    Agent Runner. This ensures token caching is shared - we don't create
    duplicate M2M token requests. The Auth0 client handles token refresh
    automatically.
    """

    DEFAULT_POLL_INTERVAL = 2.0  # seconds
    DEFAULT_TIMEOUT = 600.0  # 10 minutes

    def __init__(
        self,
        base_url: str,
        auth0_client: Optional["Auth0M2MClient"] = None,
        timeout: float = 30.0,
    ):
        """Initialize CoordinatorClient.

        Args:
            base_url: Agent Coordinator API URL
            auth0_client: Shared Auth0 client from Agent Runner (reuses token cache)
            timeout: Request timeout in seconds
        """
        self._base_url = base_url.rstrip("/")
        # Store reference to shared Auth0 client - token caching is shared
        self._auth0_client = auth0_client
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    def _get_auth_headers(self) -> dict:
        """Get Authorization header if auth configured."""
        if self._auth0_client and self._auth0_client.is_configured:
            token = self._auth0_client.get_access_token()
            if token:
                return {"Authorization": f"Bearer {token}"}
        return {}

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ========== Runs API ==========

    async def create_run(
        self,
        run_type: str,
        prompt: str,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        project_dir: Optional[str] = None,
        parent_session_id: Optional[str] = None,
        execution_mode: Optional[str] = None,
        additional_demands: Optional[dict] = None,
    ) -> dict:
        """Create a run via POST /runs.

        Args:
            run_type: "start_session" or "resume_session"
            prompt: User prompt
            session_id: Session ID (required for resume_session)
            agent_name: Agent blueprint name (for start_session)
            project_dir: Project directory (for start_session)
            parent_session_id: Parent session for callbacks (ADR-003/ADR-005)
            execution_mode: "sync", "async_poll", or "async_callback" (ADR-003)
            additional_demands: Extra runner demands (ADR-011)

        Returns:
            {"run_id": "run_xxx", "session_id": "ses_xxx", "status": "pending"}
        """
        client = await self._ensure_client()

        data: dict[str, Any] = {
            "type": run_type,
            "prompt": prompt,
        }
        if session_id:
            data["session_id"] = session_id
        if agent_name:
            data["agent_name"] = agent_name
        if project_dir:
            data["project_dir"] = project_dir
        if parent_session_id:
            data["parent_session_id"] = parent_session_id
        if execution_mode:
            data["execution_mode"] = execution_mode
        if additional_demands:
            data["additional_demands"] = additional_demands

        try:
            response = await client.post(
                f"{self._base_url}/runs",
                json=data,
                headers=self._get_auth_headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise CoordinatorClientError(f"Failed to create run: {e.response.text}")
        except httpx.RequestError as e:
            raise CoordinatorClientError(f"Request failed: {e}")

    async def get_run(self, run_id: str) -> dict:
        """Get run status via GET /runs/{run_id}."""
        client = await self._ensure_client()

        try:
            response = await client.get(
                f"{self._base_url}/runs/{run_id}",
                headers=self._get_auth_headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise CoordinatorClientError(f"Failed to get run: {e.response.text}")
        except httpx.RequestError as e:
            raise CoordinatorClientError(f"Request failed: {e}")

    async def wait_for_run(
        self,
        run_id: str,
        session_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> str:
        """Wait for run to complete and return session result.

        Args:
            run_id: Run ID to wait for
            session_id: Session ID for getting result
            poll_interval: Seconds between polls
            timeout: Maximum wait time in seconds

        Returns:
            Session result text

        Raises:
            RunTimeoutError: If run doesn't complete in time
            RunFailedError: If run fails
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise RunTimeoutError(
                    f"Run {run_id} did not complete within {timeout}s"
                )

            run = await self.get_run(run_id)
            status = run.get("status")

            if status == "completed":
                return await self.get_session_result(session_id)
            elif status == "failed":
                error = run.get("error", "Unknown error")
                raise RunFailedError(f"Run failed: {error}")
            elif status in ("pending", "claimed", "running"):
                await asyncio.sleep(poll_interval)
            else:
                raise CoordinatorClientError(f"Unknown run status: {status}")

    # ========== Sessions API ==========

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID via GET /sessions/{session_id}."""
        client = await self._ensure_client()

        try:
            response = await client.get(
                f"{self._base_url}/sessions/{session_id}",
                headers=self._get_auth_headers(),
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json().get("session")
        except httpx.HTTPStatusError as e:
            raise CoordinatorClientError(f"Failed to get session: {e.response.text}")
        except httpx.RequestError as e:
            raise CoordinatorClientError(f"Request failed: {e}")

    async def get_session_status(self, session_id: str) -> str:
        """Get session status via GET /sessions/{session_id}/status."""
        client = await self._ensure_client()

        try:
            response = await client.get(
                f"{self._base_url}/sessions/{session_id}/status",
                headers=self._get_auth_headers(),
            )
            if response.status_code == 404:
                return "not_existent"
            response.raise_for_status()
            return response.json().get("status", "not_existent")
        except httpx.HTTPStatusError as e:
            raise CoordinatorClientError(f"Failed to get status: {e.response.text}")
        except httpx.RequestError as e:
            raise CoordinatorClientError(f"Request failed: {e}")

    async def get_session_result(self, session_id: str) -> str:
        """Get session result via GET /sessions/{session_id}/result."""
        client = await self._ensure_client()

        try:
            response = await client.get(
                f"{self._base_url}/sessions/{session_id}/result",
                headers=self._get_auth_headers(),
            )
            response.raise_for_status()
            return response.json().get("result", "")
        except httpx.HTTPStatusError as e:
            raise CoordinatorClientError(f"Failed to get result: {e.response.text}")
        except httpx.RequestError as e:
            raise CoordinatorClientError(f"Request failed: {e}")

    async def list_sessions(self) -> list[dict]:
        """List all sessions via GET /sessions."""
        client = await self._ensure_client()

        try:
            response = await client.get(
                f"{self._base_url}/sessions",
                headers=self._get_auth_headers(),
            )
            response.raise_for_status()
            return response.json().get("sessions", [])
        except httpx.HTTPStatusError as e:
            raise CoordinatorClientError(f"Failed to list sessions: {e.response.text}")
        except httpx.RequestError as e:
            raise CoordinatorClientError(f"Request failed: {e}")

    async def delete_session(self, session_id: str) -> bool:
        """Delete session via DELETE /sessions/{session_id}."""
        client = await self._ensure_client()

        try:
            response = await client.delete(
                f"{self._base_url}/sessions/{session_id}",
                headers=self._get_auth_headers(),
            )
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            raise CoordinatorClientError(f"Failed to delete session: {e.response.text}")
        except httpx.RequestError as e:
            raise CoordinatorClientError(f"Request failed: {e}")

    async def delete_all_sessions(self) -> int:
        """Delete all sessions. Returns count of deleted sessions."""
        sessions = await self.list_sessions()
        deleted = 0
        for session in sessions:
            session_id = session.get("session_id")
            if session_id:
                if await self.delete_session(session_id):
                    deleted += 1
        return deleted

    # ========== Agents API ==========

    async def list_agents(self, tags: Optional[str] = None) -> list[dict]:
        """List agent blueprints via GET /agents.

        Args:
            tags: Comma-separated tags to filter by (AND logic)

        Returns:
            List of active agent dictionaries
        """
        client = await self._ensure_client()

        params = {}
        if tags:
            params["tags"] = tags

        try:
            response = await client.get(
                f"{self._base_url}/agents",
                params=params,
                headers=self._get_auth_headers(),
            )
            response.raise_for_status()
            agents = response.json()
            # Filter to active agents only
            return [a for a in agents if a.get("status") == "active"]
        except httpx.HTTPStatusError as e:
            raise CoordinatorClientError(f"Failed to list agents: {e.response.text}")
        except httpx.RequestError as e:
            raise CoordinatorClientError(f"Request failed: {e}")

    async def get_agent(self, agent_name: str) -> Optional[dict]:
        """Get agent blueprint by name via GET /agents/{name}."""
        client = await self._ensure_client()

        try:
            response = await client.get(
                f"{self._base_url}/agents/{agent_name}",
                headers=self._get_auth_headers(),
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("agent", data)
        except httpx.HTTPStatusError as e:
            raise CoordinatorClientError(f"Failed to get agent: {e.response.text}")
        except httpx.RequestError as e:
            raise CoordinatorClientError(f"Request failed: {e}")
