"""
HTTP client for communicating with Agent Runtime.

Wraps the Launcher API endpoints with typed methods.
"""

import httpx
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RegistrationResponse:
    """Response from launcher registration."""
    launcher_id: str
    poll_endpoint: str
    poll_timeout_seconds: int
    heartbeat_interval_seconds: int


@dataclass
class Job:
    """Job to execute."""
    job_id: str
    type: str  # "start_session" or "resume_session"
    session_name: str
    agent_name: Optional[str]
    prompt: str
    project_dir: Optional[str]


class RuntimeAPIClient:
    """HTTP client for Agent Runtime Launcher API."""

    def __init__(self, base_url: str, timeout: float = 35.0):
        """Initialize client with base URL.

        Args:
            base_url: Agent Runtime URL (e.g., http://localhost:8765)
            timeout: Request timeout in seconds (slightly longer than poll timeout)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def register(
        self,
        hostname: Optional[str] = None,
        project_dir: Optional[str] = None,
    ) -> RegistrationResponse:
        """Register this launcher with Agent Runtime.

        Args:
            hostname: The machine hostname where the launcher is running
            project_dir: The default project directory for this launcher

        Returns registration info including launcher_id.
        """
        # Build metadata payload
        metadata = {}
        if hostname:
            metadata["hostname"] = hostname
        if project_dir:
            metadata["project_dir"] = project_dir

        response = self._client.post(
            f"{self.base_url}/launcher/register",
            json=metadata if metadata else None,
        )
        response.raise_for_status()
        data = response.json()

        return RegistrationResponse(
            launcher_id=data["launcher_id"],
            poll_endpoint=data["poll_endpoint"],
            poll_timeout_seconds=data["poll_timeout_seconds"],
            heartbeat_interval_seconds=data["heartbeat_interval_seconds"],
        )

    def poll_job(self, launcher_id: str) -> Optional[Job]:
        """Long-poll for a job to execute.

        Returns Job if available, None if timeout with no jobs.
        """
        try:
            response = self._client.get(
                f"{self.base_url}/launcher/jobs",
                params={"launcher_id": launcher_id},
            )

            if response.status_code == 204:
                # No jobs available
                return None

            response.raise_for_status()
            data = response.json()
            job_data = data["job"]

            return Job(
                job_id=job_data["job_id"],
                type=job_data["type"],
                session_name=job_data["session_name"],
                agent_name=job_data.get("agent_name"),
                prompt=job_data["prompt"],
                project_dir=job_data.get("project_dir"),
            )
        except httpx.TimeoutException:
            # Timeout is expected for long-polling
            logger.debug("Poll timeout (expected)")
            return None

    def report_started(self, launcher_id: str, job_id: str) -> None:
        """Report that job execution has started."""
        response = self._client.post(
            f"{self.base_url}/launcher/jobs/{job_id}/started",
            json={"launcher_id": launcher_id},
        )
        response.raise_for_status()

    def report_completed(self, launcher_id: str, job_id: str) -> None:
        """Report that job completed successfully."""
        response = self._client.post(
            f"{self.base_url}/launcher/jobs/{job_id}/completed",
            json={"launcher_id": launcher_id, "status": "success"},
        )
        response.raise_for_status()

    def report_failed(self, launcher_id: str, job_id: str, error: str) -> None:
        """Report that job execution failed."""
        response = self._client.post(
            f"{self.base_url}/launcher/jobs/{job_id}/failed",
            json={"launcher_id": launcher_id, "error": error},
        )
        response.raise_for_status()

    def heartbeat(self, launcher_id: str) -> None:
        """Send heartbeat to keep registration alive."""
        response = self._client.post(
            f"{self.base_url}/launcher/heartbeat",
            json={"launcher_id": launcher_id},
        )
        response.raise_for_status()

    def get_session_by_name(self, session_name: str) -> Optional[dict]:
        """Get session by session_name.

        Returns session dict if found, None if not found.
        """
        try:
            response = self._client.get(
                f"{self.base_url}/sessions/by-name/{session_name}",
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("session")
        except Exception as e:
            logger.error(f"Failed to get session {session_name}: {e}")
            return None

    def get_session_result(self, session_name: str) -> Optional[str]:
        """Get result text from a finished session by session_name.

        Returns result text if found and session is finished, None otherwise.
        """
        try:
            # First get session to get session_id
            session = self.get_session_by_name(session_name)
            if not session:
                return None

            session_id = session.get("session_id")
            if not session_id:
                return None

            # Get result
            response = self._client.get(
                f"{self.base_url}/sessions/{session_id}/result",
            )
            if response.status_code != 200:
                return None
            data = response.json()
            return data.get("result")
        except Exception as e:
            logger.debug(f"Failed to get result for session {session_name}: {e}")
            return None

    def create_resume_job(
        self,
        session_name: str,
        prompt: str,
        project_dir: Optional[str] = None,
    ) -> Optional[str]:
        """Create a resume_session job.

        Returns job_id if successful, None on error.
        """
        try:
            job_request = {
                "type": "resume_session",
                "session_name": session_name,
                "prompt": prompt,
            }
            if project_dir:
                job_request["project_dir"] = project_dir

            response = self._client.post(
                f"{self.base_url}/jobs",
                json=job_request,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("job_id")
        except Exception as e:
            logger.error(f"Failed to create resume job for {session_name}: {e}")
            return None
