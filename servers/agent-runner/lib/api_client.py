"""
HTTP client for communicating with Agent Coordinator.

Wraps the Runner API endpoints with typed methods.

Note: Uses session_id (coordinator-generated) per ADR-010.
"""

import httpx
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DuplicateRunnerError(Exception):
    """Raised when trying to register a runner with an identity that's already online."""

    def __init__(self, runner_id: str, hostname: str, project_dir: str, executor_type: str, message: str):
        self.runner_id = runner_id
        self.hostname = hostname
        self.project_dir = project_dir
        self.executor_type = executor_type
        super().__init__(message)


@dataclass
class RegistrationResponse:
    """Response from runner registration."""
    runner_id: str
    poll_endpoint: str
    poll_timeout_seconds: int
    heartbeat_interval_seconds: int


@dataclass
class Run:
    """Agent run to execute.

    session_id is coordinator-generated per ADR-010.
    """
    run_id: str
    type: str  # "start_session" or "resume_session"
    session_id: str
    agent_name: Optional[str]
    prompt: str
    project_dir: Optional[str]
    parent_session_id: Optional[str] = None


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
    """HTTP client for Agent Coordinator Runner API."""

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
        hostname: str,
        project_dir: str,
        executor_type: str,
        tags: Optional[list[str]] = None,
    ) -> RegistrationResponse:
        """Register this runner with Agent Coordinator.

        All parameters are required for deterministic runner_id derivation.
        Same parameters produce the same runner_id (enables reconnection recognition).

        Args:
            hostname: The machine hostname where the runner is running
            project_dir: The default project directory for this runner
            executor_type: The type of executor (folder name, e.g., 'claude-code')
            tags: Optional list of capability tags this runner offers (ADR-011)

        Returns:
            Registration info including runner_id derived from properties
        """
        payload = {
            "hostname": hostname,
            "project_dir": project_dir,
            "executor_type": executor_type,
        }
        if tags:
            payload["tags"] = tags

        response = self._client.post(
            f"{self.base_url}/runner/register",
            json=payload,
        )

        # Handle duplicate runner error (409 Conflict)
        if response.status_code == 409:
            data = response.json()
            detail = data.get("detail", {})
            raise DuplicateRunnerError(
                runner_id=detail.get("runner_id", "unknown"),
                hostname=detail.get("hostname", hostname),
                project_dir=detail.get("project_dir", project_dir),
                executor_type=detail.get("executor_type", executor_type),
                message=detail.get("message", "A runner with this identity is already online"),
            )

        response.raise_for_status()
        data = response.json()

        return RegistrationResponse(
            runner_id=data["runner_id"],
            poll_endpoint=data["poll_endpoint"],
            poll_timeout_seconds=data["poll_timeout_seconds"],
            heartbeat_interval_seconds=data["heartbeat_interval_seconds"],
        )

    def poll_run(self, runner_id: str) -> PollResult:
        """Long-poll for an agent run to execute or stop commands.

        Returns PollResult with:
        - run: Run if available
        - deregistered: True if runner has been deregistered externally
        - stop_runs: List of run IDs to stop
        """
        try:
            response = self._client.get(
                f"{self.base_url}/runner/runs",
                params={"runner_id": runner_id},
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
                session_id=run_data["session_id"],
                agent_name=run_data.get("agent_name"),
                prompt=run_data["prompt"],
                project_dir=run_data.get("project_dir"),
                parent_session_id=run_data.get("parent_session_id"),
            )
            return PollResult(run=run)
        except httpx.TimeoutException:
            # Timeout is expected for long-polling
            logger.debug("Poll timeout (expected)")
            return PollResult()

    def report_started(self, runner_id: str, run_id: str) -> None:
        """Report that agent run execution has started."""
        response = self._client.post(
            f"{self.base_url}/runner/runs/{run_id}/started",
            json={"runner_id": runner_id},
        )
        response.raise_for_status()

    def report_completed(self, runner_id: str, run_id: str) -> None:
        """Report that agent run completed successfully."""
        response = self._client.post(
            f"{self.base_url}/runner/runs/{run_id}/completed",
            json={"runner_id": runner_id, "status": "success"},
        )
        response.raise_for_status()

    def report_failed(self, runner_id: str, run_id: str, error: str) -> None:
        """Report that agent run execution failed."""
        response = self._client.post(
            f"{self.base_url}/runner/runs/{run_id}/failed",
            json={"runner_id": runner_id, "error": error},
        )
        response.raise_for_status()

    def report_stopped(self, runner_id: str, run_id: str, signal: str = "SIGTERM") -> None:
        """Report that agent run was stopped (terminated by stop command)."""
        response = self._client.post(
            f"{self.base_url}/runner/runs/{run_id}/stopped",
            json={"runner_id": runner_id, "signal": signal},
        )
        response.raise_for_status()

    def heartbeat(self, runner_id: str) -> None:
        """Send heartbeat to keep registration alive."""
        response = self._client.post(
            f"{self.base_url}/runner/heartbeat",
            json={"runner_id": runner_id},
        )
        response.raise_for_status()

    def deregister(self, runner_id: str) -> None:
        """Deregister this runner (graceful shutdown).

        Called when runner is shutting down to immediately remove
        itself from the registry.
        """
        try:
            response = self._client.delete(
                f"{self.base_url}/runners/{runner_id}",
                params={"self": "true"},
            )
            response.raise_for_status()
            logger.info(f"Deregistered runner {runner_id}")
        except Exception as e:
            # Don't fail shutdown if deregistration fails
            logger.warning(f"Failed to deregister: {e}")

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by session_id.

        Returns session dict if found, None if not found.
        """
        try:
            response = self._client.get(
                f"{self.base_url}/sessions/{session_id}",
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("session")
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    def get_session_affinity(self, session_id: str) -> Optional[dict]:
        """Get session affinity information for resume routing.

        Returns affinity dict (hostname, project_dir, executor_type, executor_session_id)
        or None if not found.
        """
        try:
            response = self._client.get(
                f"{self.base_url}/sessions/{session_id}/affinity",
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("affinity")
        except Exception as e:
            logger.error(f"Failed to get session affinity {session_id}: {e}")
            return None

    def get_session_result(self, session_id: str) -> Optional[str]:
        """Get result text from a finished session.

        Returns result text if found and session is finished, None otherwise.
        """
        try:
            response = self._client.get(
                f"{self.base_url}/sessions/{session_id}/result",
            )
            if response.status_code != 200:
                return None
            data = response.json()
            return data.get("result")
        except Exception as e:
            logger.debug(f"Failed to get result for session {session_id}: {e}")
            return None

    def create_resume_run(
        self,
        session_id: str,
        prompt: str,
        project_dir: Optional[str] = None,
    ) -> Optional[str]:
        """Create a resume_session agent run.

        Returns run_id if successful, None on error.
        """
        try:
            run_request = {
                "type": "resume_session",
                "session_id": session_id,
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
            logger.error(f"Failed to create resume run for {session_id}: {e}")
            return None
