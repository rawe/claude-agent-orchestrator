"""
Poll Thread - continuously polls Agent Runtime for new jobs.

Runs in a background thread, spawning subprocesses for each job.
"""

import threading
import time
import logging
from typing import Callable

from api_client import RuntimeAPIClient, Job
from executor import JobExecutor
from registry import RunningJobsRegistry

logger = logging.getLogger(__name__)


class JobPoller:
    """Background thread that polls for and executes jobs."""

    def __init__(
        self,
        api_client: RuntimeAPIClient,
        executor: JobExecutor,
        registry: RunningJobsRegistry,
        launcher_id: str,
    ):
        """Initialize the poller.

        Args:
            api_client: HTTP client for Agent Runtime
            executor: Job executor for spawning subprocesses
            registry: Registry for tracking running jobs
            launcher_id: This launcher's ID
        """
        self.api_client = api_client
        self.executor = executor
        self.registry = registry
        self.launcher_id = launcher_id

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._backoff_seconds = 1.0
        self._max_backoff = 30.0

    def start(self) -> None:
        """Start the polling thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Poller already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Poller started")

    def stop(self) -> None:
        """Stop the polling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Poller stopped")

    def _poll_loop(self) -> None:
        """Main polling loop."""
        while not self._stop_event.is_set():
            try:
                job = self.api_client.poll_job(self.launcher_id)

                if job:
                    self._handle_job(job)
                    # Reset backoff on success
                    self._backoff_seconds = 1.0
                # If no job (timeout), continue immediately

            except Exception as e:
                logger.error(f"Poll error: {e}")
                # Backoff on error
                time.sleep(self._backoff_seconds)
                self._backoff_seconds = min(self._backoff_seconds * 2, self._max_backoff)

    def _handle_job(self, job: Job) -> None:
        """Handle a received job by spawning subprocess."""
        logger.info(f"Received job {job.job_id}: type={job.type}, session={job.session_name}")

        try:
            # Spawn subprocess
            process = self.executor.execute(job)

            # Add to registry
            self.registry.add_job(job.job_id, job.session_name, process)

            # Report started
            self.api_client.report_started(self.launcher_id, job.job_id)
            logger.info(f"Job {job.job_id} started (pid={process.pid})")

        except Exception as e:
            logger.error(f"Failed to start job {job.job_id}: {e}")
            try:
                self.api_client.report_failed(self.launcher_id, job.job_id, str(e))
            except Exception:
                logger.error(f"Failed to report job failure for {job.job_id}")
