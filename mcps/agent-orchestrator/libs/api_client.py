"""
HTTP client for Agent Coordinator API.

This module provides an async HTTP client using httpx to communicate
with the Agent Coordinator API for agent run management and session operations.
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from logger import logger


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class APIClient:
    """Async HTTP client for Agent Coordinator API."""

    DEFAULT_TIMEOUT = 10.0
    DEFAULT_POLL_INTERVAL = 2.0
    DEFAULT_COMPLETION_TIMEOUT = 600.0  # 10 minutes

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        """Make async HTTP request using httpx."""
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    response = await client.post(url, json=data)
                elif method == "DELETE":
                    response = await client.delete(url)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if response.status_code >= 400:
                    error_body = response.text
                    raise APIError(
                        f"HTTP {response.status_code}: {error_body}",
                        status_code=response.status_code,
                    )

                # Handle empty responses (e.g., 204 No Content)
                if response.status_code == 204 or not response.content:
                    return {}

                return response.json()

            except httpx.TimeoutException as e:
                raise APIError(f"Request timed out: {e}")
            except httpx.ConnectError as e:
                raise APIError(f"Connection failed: {e}")
            except httpx.HTTPError as e:
                raise APIError(f"HTTP error: {e}")

    # -------------------------------------------------------------------------
    # Agent Runs API
    # -------------------------------------------------------------------------

    async def create_run(
        self,
        run_type: str,
        session_name: str,
        prompt: str,
        agent_name: Optional[str] = None,
        project_dir: Optional[str] = None,
        parent_session_name: Optional[str] = None,
        additional_demands: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create an agent run. Returns run_id.

        Args:
            run_type: "start_session" or "resume_session"
            session_name: Name for the session
            prompt: The prompt to send
            agent_name: Blueprint name (for start_session)
            project_dir: Project directory
            parent_session_name: Parent session for orchestration
            additional_demands: Additional demands to merge with blueprint (ADR-011)

        Returns:
            run_id
        """
        data: Dict[str, Any] = {
            "type": run_type,
            "session_name": session_name,
            "prompt": prompt,
        }
        if agent_name:
            data["agent_name"] = agent_name
        if project_dir:
            data["project_dir"] = project_dir
        if parent_session_name:
            data["parent_session_name"] = parent_session_name
        if additional_demands:
            data["additional_demands"] = additional_demands

        result = await self._request("POST", "/runs", data)
        return result["run_id"]

    async def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get agent run status."""
        return await self._request("GET", f"/runs/{run_id}")

    async def wait_for_run(
        self,
        run_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_COMPLETION_TIMEOUT,
    ) -> Dict[str, Any]:
        """Poll agent run until completed or failed."""
        elapsed = 0.0

        while elapsed < timeout:
            run = await self.get_run(run_id)
            status = run.get("status")

            logger.debug(f"Run {run_id} status: {status}", {"elapsed": elapsed})

            if status == "completed":
                return run
            elif status == "failed":
                error = run.get("error", "Unknown error")
                raise APIError(f"Run failed: {error}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise APIError(f"Run {run_id} timed out after {timeout}s")

    # -------------------------------------------------------------------------
    # Sessions API
    # -------------------------------------------------------------------------

    async def get_session_by_name(self, session_name: str) -> Optional[Dict[str, Any]]:
        """Get session by name. Returns None if not found."""
        try:
            result = await self._request("GET", f"/sessions/by-name/{session_name}")
            return result.get("session")
        except APIError as e:
            if e.status_code == 404:
                return None
            raise

    async def get_session_status(self, session_id: str) -> str:
        """Get session status."""
        result = await self._request("GET", f"/sessions/{session_id}/status")
        return result.get("status", "not_existent")

    async def get_session_result(self, session_id: str) -> str:
        """Get session result."""
        result = await self._request("GET", f"/sessions/{session_id}/result")
        return result.get("result", "")

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        result = await self._request("GET", "/sessions")
        return result.get("sessions", [])

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            await self._request("DELETE", f"/sessions/{session_id}")
            return True
        except APIError:
            return False

    # -------------------------------------------------------------------------
    # Agents API
    # -------------------------------------------------------------------------

    async def list_agents(self, tags: Optional[str] = None) -> List[Dict[str, Any]]:
        """List agent blueprints, optionally filtered by tags."""
        path = "/agents"
        if tags:
            path = f"/agents?tags={tags}"
        return await self._request("GET", path)

    async def get_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get agent by name."""
        try:
            return await self._request("GET", f"/agents/{agent_name}")
        except APIError as e:
            if e.status_code == 404:
                return None
            raise
