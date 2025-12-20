"""
Poll Thread - continuously polls Agent Coordinator for new agent runs.

Runs in a background thread, spawning subprocesses for each agent run.
"""

import threading
import time
import logging
from typing import Callable, Optional

from api_client import CoordinatorAPIClient, Run, PollResult
from executor import RunExecutor
from registry import RunningRunsRegistry

logger = logging.getLogger(__name__)

# Number of consecutive connection failures before giving up
MAX_CONNECTION_RETRIES = 3


class RunPoller:
    """Background thread that polls for and executes agent runs."""

    def __init__(
        self,
        api_client: CoordinatorAPIClient,
        executor: RunExecutor,
        registry: RunningRunsRegistry,
        runner_id: str,
        on_deregistered: Optional[Callable[[], None]] = None,
    ):
        """Initialize the poller.

        Args:
            api_client: HTTP client for Agent Coordinator
            executor: Run executor for spawning subprocesses
            registry: Registry for tracking running agent runs
            runner_id: This runner's ID
            on_deregistered: Callback when runner is deregistered externally
        """
        self.api_client = api_client
        self.executor = executor
        self.registry = registry
        self.runner_id = runner_id
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
                result = self.api_client.poll_run(self.runner_id)

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
                if result.stop_runs:
                    for run_id in result.stop_runs:
                        self._handle_stop(run_id)
                    continue  # Check for more commands

                if result.run:
                    self._handle_run(result.run)

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

    def _handle_run(self, run: Run) -> None:
        """Handle a received agent run by spawning subprocess."""
        logger.debug(f"Received agent run {run.run_id}: type={run.type}, session={run.session_id}")

        try:
            # Spawn subprocess
            process = self.executor.execute_run(run)

            # Add to registry
            self.registry.add_run(run.run_id, run.session_id, process)

            # Report started
            self.api_client.report_started(self.runner_id, run.run_id)
            logger.debug(f"Agent run {run.run_id} started (pid={process.pid})")

        except Exception as e:
            logger.error(f"Failed to start agent run {run.run_id}: {e}")
            try:
                self.api_client.report_failed(self.runner_id, run.run_id, str(e))
            except Exception:
                logger.error(f"Failed to report agent run failure for {run.run_id}")

    def _handle_stop(self, run_id: str) -> None:
        """Stop a running agent run by terminating its process."""
        running_run = self.registry.get_run(run_id)

        if not running_run:
            # Agent run not running (already completed or never started)
            logger.debug(f"Stop command for agent run {run_id} ignored - run not running")
            return

        logger.info(f"Stopping agent run {run_id} (session={running_run.session_id}, pid={running_run.process.pid})")

        signal_used = "SIGTERM"

        try:
            # Send SIGTERM first (graceful)
            running_run.process.terminate()

            # Wait briefly for graceful shutdown
            try:
                running_run.process.wait(timeout=5)
            except Exception:
                # Force kill if not responding
                running_run.process.kill()
                signal_used = "SIGKILL"
                logger.warning(f"Agent run {run_id} did not respond to SIGTERM, sent SIGKILL")

            # Remove from registry
            self.registry.remove_run(run_id)

            # Report stopped
            try:
                self.api_client.report_stopped(self.runner_id, run_id, signal=signal_used)
                logger.info(f"Agent run {run_id} stopped successfully (signal={signal_used})")
            except Exception as e:
                logger.error(f"Failed to report stopped for {run_id}: {e}")

        except Exception as e:
            logger.error(f"Error stopping agent run {run_id}: {e}")
