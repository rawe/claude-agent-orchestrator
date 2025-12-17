"""
HTTP client for communicating with Agent Coordinator.

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
class Run:
    """Agent run to execute."""
    run_id: str
    type: str  # "start_session" or "resume_session"
    session_name: str
    agent_name: Optional[str]
    prompt: str
    project_dir: Optional[str]


@dataclass
class PollResult:
    """Result from polling for agent runs."""
    run: Optional[Run] = None
    deregistered: bool = False
    stop_runs: list[str] = None  # Run IDs to stop

    def __post_init__(self):
        if self.stop_runs is None:
            self.stop_runs = []


class CoordinatorAPIClient:
    """HTTP client for Agent Coordinator Launcher API."""

    def __init__(self, base_url: str, timeout: float = 35.0):
        """Initialize client with base URL.

        Args:
            base_url: Agent Coordinator URL (e.g., http://localhost:8765)
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
        executor_type: Optional[str] = None,
    ) -> RegistrationResponse:
        """Register this launcher with Agent Coordinator.

        Args:
            hostname: The machine hostname where the launcher is running
            project_dir: The default project directory for this launcher
            executor_type: The type of executor (folder name, e.g., 'claude-code')

        Returns registration info including launcher_id.
        """
        # Build metadata payload
        metadata = {}
        if hostname:
            metadata["hostname"] = hostname
        if project_dir:
            metadata["project_dir"] = project_dir
        if executor_type:
            metadata["executor_type"] = executor_type

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

    def poll_run(self, launcher_id: str) -> PollResult:
        """Long-poll for an agent run to execute or stop commands.

        Returns PollResult with:
        - run: Run if available
        - deregistered: True if launcher has been deregistered externally
        - stop_runs: List of run IDs to stop
        """
        try:
            response = self._client.get(
                f"{self.base_url}/launcher/runs",
                params={"launcher_id": launcher_id},
            )

            if response.status_code == 204:
                # No runs available
                return PollResult()

            response.raise_for_status()
            data = response.json()

            # Check for deregistration signal
            if data.get("deregistered"):
                return PollResult(deregistered=True)

            # Check for stop commands
            if "stop_runs" in data:
                return PollResult(stop_runs=data["stop_runs"])

            # Normal run response
            run_data = data["run"]
            run = Run(
                run_id=run_data["run_id"],
                type=run_data["type"],
                session_name=run_data["session_name"],
                agent_name=run_data.get("agent_name"),
                prompt=run_data["prompt"],
                project_dir=run_data.get("project_dir"),
            )
            return PollResult(run=run)
        except httpx.TimeoutException:
            # Timeout is expected for long-polling
            logger.debug("Poll timeout (expected)")
            return PollResult()

    def report_started(self, launcher_id: str, run_id: str) -> None:
        """Report that agent run execution has started."""
        response = self._client.post(
            f"{self.base_url}/launcher/runs/{run_id}/started",
            json={"launcher_id": launcher_id},
        )
        response.raise_for_status()

    def report_completed(self, launcher_id: str, run_id: str) -> None:
        """Report that agent run completed successfully."""
        response = self._client.post(
            f"{self.base_url}/launcher/runs/{run_id}/completed",
            json={"launcher_id": launcher_id, "status": "success"},
        )
        response.raise_for_status()

    def report_failed(self, launcher_id: str, run_id: str, error: str) -> None:
        """Report that agent run execution failed."""
        response = self._client.post(
            f"{self.base_url}/launcher/runs/{run_id}/failed",
            json={"launcher_id": launcher_id, "error": error},
        )
        response.raise_for_status()

    def report_stopped(self, launcher_id: str, run_id: str, signal: str = "SIGTERM") -> None:
        """Report that agent run was stopped (terminated by stop command)."""
        response = self._client.post(
            f"{self.base_url}/launcher/runs/{run_id}/stopped",
            json={"launcher_id": launcher_id, "signal": signal},
        )
        response.raise_for_status()

    def heartbeat(self, launcher_id: str) -> None:
        """Send heartbeat to keep registration alive."""
        response = self._client.post(
            f"{self.base_url}/launcher/heartbeat",
            json={"launcher_id": launcher_id},
        )
        response.raise_for_status()

    def deregister(self, launcher_id: str) -> None:
        """Deregister this launcher (graceful shutdown).

        Called when launcher is shutting down to immediately remove
        itself from the registry.
        """
        try:
            response = self._client.delete(
                f"{self.base_url}/launchers/{launcher_id}",
                params={"self": "true"},
            )
            response.raise_for_status()
            logger.info(f"Deregistered launcher {launcher_id}")
        except Exception as e:
            # Don't fail shutdown if deregistration fails
            logger.warning(f"Failed to deregister: {e}")

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

    def create_resume_run(
        self,
        session_name: str,
        prompt: str,
        project_dir: Optional[str] = None,
    ) -> Optional[str]:
        """Create a resume_session agent run.

        Returns run_id if successful, None on error.
        """
        try:
            run_request = {
                "type": "resume_session",
                "session_name": session_name,
                "prompt": prompt,
            }
            if project_dir:
                run_request["project_dir"] = project_dir

            response = self._client.post(
                f"{self.base_url}/runs",
                json=run_request,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("run_id")
        except Exception as e:
            logger.error(f"Failed to create resume run for {session_name}: {e}")
            return None
