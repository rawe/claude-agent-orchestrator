"""
Running Jobs Registry - tracks active subprocess executions.

Thread-safe storage for mapping job_id to subprocess.Popen objects.
"""

import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RunningJob:
    """Information about a running job."""
    process: subprocess.Popen
    started_at: datetime
    job_id: str
    session_name: str


class RunningJobsRegistry:
    """Thread-safe registry for tracking running job subprocesses."""

    def __init__(self):
        self._jobs: dict[str, RunningJob] = {}
        self._lock = threading.Lock()

    def add_job(self, job_id: str, session_name: str, process: subprocess.Popen) -> None:
        """Add a running job to the registry."""
        running_job = RunningJob(
            process=process,
            started_at=datetime.now(),
            job_id=job_id,
            session_name=session_name,
        )

        with self._lock:
            self._jobs[job_id] = running_job

    def remove_job(self, job_id: str) -> Optional[RunningJob]:
        """Remove and return a job from the registry.

        Returns the removed job or None if not found.
        """
        with self._lock:
            return self._jobs.pop(job_id, None)

    def get_job(self, job_id: str) -> Optional[RunningJob]:
        """Get a running job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_all_jobs(self) -> dict[str, RunningJob]:
        """Get a copy of all running jobs."""
        with self._lock:
            return dict(self._jobs)

    def count(self) -> int:
        """Get number of running jobs."""
        with self._lock:
            return len(self._jobs)
