"""
Poll Thread - continuously polls Agent Coordinator for new jobs.

Runs in a background thread, spawning subprocesses for each job.
"""

import threading
import time
import logging
from typing import Callable, Optional

from api_client import CoordinatorAPIClient, Job, PollResult
from executor import JobExecutor
from registry import RunningJobsRegistry

logger = logging.getLogger(__name__)

# Number of consecutive connection failures before giving up
MAX_CONNECTION_RETRIES = 3


class JobPoller:
    """Background thread that polls for and executes jobs."""

    def __init__(
        self,
        api_client: CoordinatorAPIClient,
        executor: JobExecutor,
        registry: RunningJobsRegistry,
        launcher_id: str,
        on_deregistered: Optional[Callable[[], None]] = None,
    ):
        """Initialize the poller.

        Args:
            api_client: HTTP client for Agent Coordinator
            executor: Job executor for spawning subprocesses
            registry: Registry for tracking running jobs
            launcher_id: This launcher's ID
            on_deregistered: Callback when launcher is deregistered externally
        """
        self.api_client = api_client
        self.executor = executor
        self.registry = registry
        self.launcher_id = launcher_id
        self.on_deregistered = on_deregistered

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
        consecutive_failures = 0

        while not self._stop_event.is_set():
            try:
                result = self.api_client.poll_job(self.launcher_id)

                # Successful connection - reset failure counter
                consecutive_failures = 0
                self._backoff_seconds = 1.0

                # Check for deregistration signal
                if result.deregistered:
                    logger.warning("Received deregistration signal from Agent Coordinator")
                    if self.on_deregistered:
                        self.on_deregistered()
                    return  # Exit poll loop

                # Handle stop commands
                if result.stop_jobs:
                    for job_id in result.stop_jobs:
                        self._handle_stop(job_id)
                    continue  # Check for more commands

                if result.job:
                    self._handle_job(result.job)

            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Poll error ({consecutive_failures}/{MAX_CONNECTION_RETRIES}): {e}")

                if consecutive_failures >= MAX_CONNECTION_RETRIES:
                    logger.error(f"Agent Coordinator unreachable after {MAX_CONNECTION_RETRIES} attempts - shutting down")
                    if self.on_deregistered:
                        self.on_deregistered()
                    return  # Exit poll loop

                # Backoff before retry
                time.sleep(self._backoff_seconds)
                self._backoff_seconds = min(self._backoff_seconds * 2, self._max_backoff)

    def _handle_job(self, job: Job) -> None:
        """Handle a received job by spawning subprocess."""
        logger.debug(f"Received job {job.job_id}: type={job.type}, session={job.session_name}")

        try:
            # Spawn subprocess
            process = self.executor.execute(job)

            # Add to registry
            self.registry.add_job(job.job_id, job.session_name, process)

            # Report started
            self.api_client.report_started(self.launcher_id, job.job_id)
            logger.debug(f"Job {job.job_id} started (pid={process.pid})")

        except Exception as e:
            logger.error(f"Failed to start job {job.job_id}: {e}")
            try:
                self.api_client.report_failed(self.launcher_id, job.job_id, str(e))
            except Exception:
                logger.error(f"Failed to report job failure for {job.job_id}")

    def _handle_stop(self, job_id: str) -> None:
        """Stop a running job by terminating its process."""
        running_job = self.registry.get_job(job_id)

        if not running_job:
            # Job not running (already completed or never started)
            logger.debug(f"Stop command for job {job_id} ignored - job not running")
            return

        logger.info(f"Stopping job {job_id} (session={running_job.session_name}, pid={running_job.process.pid})")

        signal_used = "SIGTERM"

        try:
            # Send SIGTERM first (graceful)
            running_job.process.terminate()

            # Wait briefly for graceful shutdown
            try:
                running_job.process.wait(timeout=5)
            except Exception:
                # Force kill if not responding
                running_job.process.kill()
                signal_used = "SIGKILL"
                logger.warning(f"Job {job_id} did not respond to SIGTERM, sent SIGKILL")

            # Remove from registry
            self.registry.remove_job(job_id)

            # Report stopped
            try:
                self.api_client.report_stopped(self.launcher_id, job_id, signal=signal_used)
                logger.info(f"Job {job_id} stopped successfully (signal={signal_used})")
            except Exception as e:
                logger.error(f"Failed to report stopped for {job_id}: {e}")

        except Exception as e:
            logger.error(f"Error stopping job {job_id}: {e}")
