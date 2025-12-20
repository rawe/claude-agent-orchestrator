"""
Running Runs Registry - tracks active agent run subprocess executions.

Thread-safe storage for mapping run_id to subprocess.Popen objects.
"""

import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RunningRun:
    """Information about a running agent run."""
    process: subprocess.Popen
    started_at: datetime
    run_id: str
    session_id: str


class RunningRunsRegistry:
    """Thread-safe registry for tracking running agent run subprocesses."""

    def __init__(self):
        self._runs: dict[str, RunningRun] = {}
        self._lock = threading.Lock()

    def add_run(self, run_id: str, session_id: str, process: subprocess.Popen) -> None:
        """Add a running agent run to the registry."""
        running_run = RunningRun(
            process=process,
            started_at=datetime.now(),
            run_id=run_id,
            session_id=session_id,
        )

        with self._lock:
            self._runs[run_id] = running_run

    def remove_run(self, run_id: str) -> Optional[RunningRun]:
        """Remove and return an agent run from the registry.

        Returns the removed run or None if not found.
        """
        with self._lock:
            return self._runs.pop(run_id, None)

    def get_run(self, run_id: str) -> Optional[RunningRun]:
        """Get a running agent run by ID."""
        with self._lock:
            return self._runs.get(run_id)

    def get_all_runs(self) -> dict[str, RunningRun]:
        """Get a copy of all running agent runs."""
        with self._lock:
            return dict(self._runs)

    def count(self) -> int:
        """Get number of running agent runs."""
        with self._lock:
            return len(self._runs)
