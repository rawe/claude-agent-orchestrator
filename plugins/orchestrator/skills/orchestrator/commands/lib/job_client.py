"""
Job Client

HTTP client for Agent Runtime Jobs API.
Creates jobs and polls for completion.
"""

import httpx
import time
from typing import Optional


class JobClientError(Exception):
    """Base exception for job client errors."""
    pass


class JobTimeoutError(JobClientError):
    """Job did not complete within timeout."""
    pass


class JobFailedError(JobClientError):
    """Job failed to execute."""
    pass


class JobClient:
    """HTTP client for Jobs API with synchronous completion."""

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

    def _create_job(
        self,
        job_type: str,
        session_name: str,
        prompt: str,
        agent_name: Optional[str] = None,
        project_dir: Optional[str] = None,
    ) -> str:
        """
        Create a job via POST /jobs.

        Request body (JobCreate):
            type: "start_session" | "resume_session"
            session_name: str
            prompt: str
            agent_name: Optional[str]
            project_dir: Optional[str]

        Response:
            {"job_id": "job_xxx", "status": "pending"}

        Returns the job_id.
        """
        url = f"{self.base_url}/jobs"
        data = {
            "type": job_type,
            "session_name": session_name,
            "prompt": prompt,
        }
        if agent_name:
            data["agent_name"] = agent_name
        if project_dir:
            data["project_dir"] = project_dir

        try:
            response = httpx.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result["job_id"]
        except httpx.HTTPStatusError as e:
            raise JobClientError(f"Failed to create job: {e.response.text}")
        except httpx.RequestError as e:
            raise JobClientError(f"Request failed: {e}")

    def _get_job(self, job_id: str) -> dict:
        """
        Get job status via GET /jobs/{job_id}.

        Response (Job):
            job_id: str
            type: "start_session" | "resume_session"
            session_name: str
            agent_name: Optional[str]
            prompt: str
            project_dir: Optional[str]
            status: "pending" | "claimed" | "running" | "completed" | "failed"
            launcher_id: Optional[str]
            error: Optional[str]
            created_at: str
            claimed_at: Optional[str]
            started_at: Optional[str]
            completed_at: Optional[str]
        """
        url = f"{self.base_url}/jobs/{job_id}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise JobClientError(f"Failed to get job status: {e.response.text}")
        except httpx.RequestError as e:
            raise JobClientError(f"Request failed: {e}")

    def _get_session_by_name(self, session_name: str) -> Optional[dict]:
        """
        Get session by name via GET /sessions/by-name/{session_name}.

        Response:
            {"session": {...}} or 404 if not found
        """
        url = f"{self.base_url}/sessions/by-name/{session_name}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json().get("session")
        except httpx.HTTPStatusError as e:
            raise JobClientError(f"Failed to get session: {e.response.text}")
        except httpx.RequestError as e:
            raise JobClientError(f"Request failed: {e}")

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
            raise JobClientError(f"Failed to get session result: {e.response.text}")
        except httpx.RequestError as e:
            raise JobClientError(f"Request failed: {e}")

    def _wait_for_completion(self, job_id: str, session_name: str) -> str:
        """
        Wait for job to complete and return the session result.

        Strategy:
        1. Poll job status until completed/failed
        2. Once job is completed, get result from session
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.completion_timeout:
                raise JobTimeoutError(
                    f"Job {job_id} did not complete within {self.completion_timeout}s"
                )

            job = self._get_job(job_id)
            status = job.get("status")

            if status == "completed":
                # Job completed - get result from session
                session = self._get_session_by_name(session_name)
                if session:
                    session_id = session.get("session_id")
                    if session_id:
                        return self._get_session_result(session_id)
                    else:
                        raise JobClientError(
                            f"Session '{session_name}' has no session_id"
                        )
                else:
                    raise JobClientError(
                        f"Session '{session_name}' not found after job completed"
                    )

            elif status == "failed":
                error = job.get("error", "Unknown error")
                raise JobFailedError(f"Job failed: {error}")

            elif status in ("pending", "claimed", "running"):
                # Still in progress - wait and poll again
                time.sleep(self.poll_interval)

            else:
                raise JobClientError(f"Unknown job status: {status}")

    def start_session(
        self,
        session_name: str,
        prompt: str,
        agent_name: Optional[str] = None,
        project_dir: Optional[str] = None,
    ) -> str:
        """
        Create a start_session job and wait for completion.

        Args:
            session_name: Name for the new session
            prompt: User prompt
            agent_name: Optional agent blueprint name
            project_dir: Optional project directory path

        Returns:
            The session result text
        """
        job_id = self._create_job(
            job_type="start_session",
            session_name=session_name,
            prompt=prompt,
            agent_name=agent_name,
            project_dir=project_dir,
        )
        return self._wait_for_completion(job_id, session_name)

    def resume_session(
        self,
        session_name: str,
        prompt: str,
    ) -> str:
        """
        Create a resume_session job and wait for completion.

        Args:
            session_name: Name of existing session to resume
            prompt: Continuation prompt

        Returns:
            The session result text
        """
        job_id = self._create_job(
            job_type="resume_session",
            session_name=session_name,
            prompt=prompt,
        )
        return self._wait_for_completion(job_id, session_name)
