"""
Run Client

HTTP client for Agent Coordinator Runs API.
Creates runs and polls for completion.

Note: Uses session_id (coordinator-generated) per ADR-010.
"""

import httpx
import time
from typing import Optional, Tuple


class RunClientError(Exception):
    """Base exception for run client errors."""
    pass


class RunTimeoutError(RunClientError):
    """Run did not complete within timeout."""
    pass


class RunFailedError(RunClientError):
    """Run failed to execute."""
    pass


class RunClient:
    """HTTP client for Runs API with synchronous completion."""

    DEFAULT_POLL_INTERVAL = 2.0  # seconds
    DEFAULT_TIMEOUT = 600.0  # 10 minutes

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        completion_timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.completion_timeout = completion_timeout

    def _create_run(
        self,
        run_type: str,
        prompt: str,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        project_dir: Optional[str] = None,
        parent_session_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Create a run via POST /runs.

        Request body (RunCreate):
            type: "start_session" | "resume_session"
            prompt: str
            session_id: Optional[str] - only for resume_session
            agent_name: Optional[str] - only for start_session
            project_dir: Optional[str] - only for start_session
            parent_session_id: Optional[str] - for callback support

        Response:
            {"run_id": "run_xxx", "session_id": "ses_xxx", "status": "pending"}

        Returns tuple of (run_id, session_id).
        """
        url = f"{self.base_url}/runs"
        data = {
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

        try:
            response = httpx.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result["run_id"], result["session_id"]
        except httpx.HTTPStatusError as e:
            raise RunClientError(f"Failed to create run: {e.response.text}")
        except httpx.RequestError as e:
            raise RunClientError(f"Request failed: {e}")

    def _get_run(self, run_id: str) -> dict:
        """
        Get run status via GET /runs/{run_id}.

        Response (Run):
            run_id: str
            type: "start_session" | "resume_session"
            session_id: str
            agent_name: Optional[str]
            prompt: str
            project_dir: Optional[str]
            status: "pending" | "claimed" | "running" | "completed" | "failed"
            runner_id: Optional[str]
            error: Optional[str]
            created_at: str
            claimed_at: Optional[str]
            started_at: Optional[str]
            completed_at: Optional[str]
        """
        url = f"{self.base_url}/runs/{run_id}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise RunClientError(f"Failed to get run status: {e.response.text}")
        except httpx.RequestError as e:
            raise RunClientError(f"Request failed: {e}")

    def _get_session(self, session_id: str) -> Optional[dict]:
        """
        Get session by ID via GET /sessions/{session_id}.

        Response:
            {"session": {...}} or 404 if not found
        """
        url = f"{self.base_url}/sessions/{session_id}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json().get("session")
        except httpx.HTTPStatusError as e:
            raise RunClientError(f"Failed to get session: {e.response.text}")
        except httpx.RequestError as e:
            raise RunClientError(f"Request failed: {e}")

    def _get_session_result(self, session_id: str) -> str:
        """
        Get session result via GET /sessions/{session_id}/result.

        Response:
            {"result": "..."} or 400 if not finished, 404 if not found
        """
        url = f"{self.base_url}/sessions/{session_id}/result"
        try:
            response = httpx.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("result", "")
        except httpx.HTTPStatusError as e:
            raise RunClientError(f"Failed to get session result: {e.response.text}")
        except httpx.RequestError as e:
            raise RunClientError(f"Request failed: {e}")

    def _wait_for_completion(self, run_id: str, session_id: str) -> str:
        """
        Wait for run to complete and return the session result.

        Strategy:
        1. Poll run status until completed/failed
        2. Once run is completed, get result from session
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.completion_timeout:
                raise RunTimeoutError(
                    f"Run {run_id} did not complete within {self.completion_timeout}s"
                )

            run = self._get_run(run_id)
            status = run.get("status")

            if status == "completed":
                # Run completed - get result from session using session_id directly
                return self._get_session_result(session_id)

            elif status == "failed":
                error = run.get("error", "Unknown error")
                raise RunFailedError(f"Run failed: {error}")

            elif status in ("pending", "claimed", "running"):
                # Still in progress - wait and poll again
                time.sleep(self.poll_interval)

            else:
                raise RunClientError(f"Unknown run status: {status}")

    def start_session(
        self,
        prompt: str,
        agent_name: Optional[str] = None,
        project_dir: Optional[str] = None,
        parent_session_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Create a start_session run and wait for completion.

        Session ID is generated by the coordinator (ADR-010).

        Args:
            prompt: User prompt
            agent_name: Optional agent blueprint name
            project_dir: Optional project directory path
            parent_session_id: Optional parent session for callbacks

        Returns:
            Tuple of (session_id, result_text)
        """
        run_id, session_id = self._create_run(
            run_type="start_session",
            prompt=prompt,
            agent_name=agent_name,
            project_dir=project_dir,
            parent_session_id=parent_session_id,
        )
        result = self._wait_for_completion(run_id, session_id)
        return session_id, result

    def resume_session(
        self,
        session_id: str,
        prompt: str,
        parent_session_id: Optional[str] = None,
    ) -> str:
        """
        Create a resume_session run and wait for completion.

        Args:
            session_id: ID of existing session to resume (coordinator-generated)
            prompt: Continuation prompt
            parent_session_id: Optional parent session for callbacks

        Returns:
            The session result text
        """
        run_id, _ = self._create_run(
            run_type="resume_session",
            session_id=session_id,
            prompt=prompt,
            parent_session_id=parent_session_id,
        )
        return self._wait_for_completion(run_id, session_id)
