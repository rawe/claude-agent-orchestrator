"""
Runner registry for tracking registered runner instances.

Runners register on startup and send periodic heartbeats to stay alive.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel


class RunnerInfo(BaseModel):
    """Information about a registered runner."""
    runner_id: str
    registered_at: str
    last_heartbeat: str
    # Metadata provided by the runner
    hostname: Optional[str] = None
    project_dir: Optional[str] = None
    executor_type: Optional[str] = None


class RunnerRegistry:
    """Thread-safe registry for tracking runners."""

    def __init__(self, heartbeat_timeout_seconds: int = 120):
        self._runners: dict[str, RunnerInfo] = {}
        self._deregistered: set[str] = set()  # IDs pending deregistration signal
        self._lock = threading.Lock()
        self._heartbeat_timeout = heartbeat_timeout_seconds

    def register_runner(
        self,
        hostname: Optional[str] = None,
        project_dir: Optional[str] = None,
        executor_type: Optional[str] = None,
    ) -> RunnerInfo:
        """Register a new runner and return its info.

        Args:
            hostname: The machine hostname where the runner is running
            project_dir: The default project directory for this runner
            executor_type: The type of executor (folder name, e.g., 'claude-code')
        """
        runner_id = f"rnr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        runner = RunnerInfo(
            runner_id=runner_id,
            registered_at=now,
            last_heartbeat=now,
            hostname=hostname,
            project_dir=project_dir,
            executor_type=executor_type,
        )

        with self._lock:
            self._runners[runner_id] = runner

        return runner

    def heartbeat(self, runner_id: str) -> bool:
        """Update last heartbeat timestamp.

        Returns True if runner exists, False otherwise.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            runner = self._runners.get(runner_id)
            if not runner:
                return False

            runner.last_heartbeat = now
            return True

    def get_runner(self, runner_id: str) -> Optional[RunnerInfo]:
        """Get runner info by ID."""
        with self._lock:
            return self._runners.get(runner_id)

    def get_seconds_since_heartbeat(self, runner_id: str) -> float | None:
        """Get seconds since last heartbeat for a runner.

        Returns None if runner not found.
        """
        with self._lock:
            runner = self._runners.get(runner_id)
            if not runner:
                return None

            last_hb = datetime.fromisoformat(runner.last_heartbeat.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return (now - last_hb).total_seconds()

    def is_runner_alive(self, runner_id: str) -> bool:
        """Check if runner is registered and has sent a recent heartbeat."""
        seconds = self.get_seconds_since_heartbeat(runner_id)
        if seconds is None:
            return False
        return seconds < self._heartbeat_timeout

    def get_all_runners(self) -> list[RunnerInfo]:
        """Get all registered runners."""
        with self._lock:
            return list(self._runners.values())

    def remove_runner(self, runner_id: str) -> bool:
        """Remove a runner from the registry.

        Returns True if runner was removed, False if not found.
        """
        with self._lock:
            if runner_id in self._runners:
                del self._runners[runner_id]
                return True
            return False

    def mark_deregistered(self, runner_id: str) -> bool:
        """Mark a runner for deregistration.

        The runner will be signaled on its next poll and then removed.
        Returns True if runner exists, False otherwise.
        """
        with self._lock:
            if runner_id not in self._runners:
                return False
            self._deregistered.add(runner_id)
            return True

    def is_deregistered(self, runner_id: str) -> bool:
        """Check if runner has been marked for deregistration."""
        with self._lock:
            return runner_id in self._deregistered

    def confirm_deregistered(self, runner_id: str) -> bool:
        """Confirm deregistration and remove runner from registry.

        Called after runner has been notified of deregistration.
        Returns True if runner was removed, False if not found.
        """
        with self._lock:
            self._deregistered.discard(runner_id)
            if runner_id in self._runners:
                del self._runners[runner_id]
                return True
            return False


# Module-level singleton
runner_registry = RunnerRegistry()
