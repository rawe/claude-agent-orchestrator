"""
Supervisor Thread - monitors running agent run subprocesses for completion.

Checks subprocess status periodically and reports completion/failure.

NOTE: Callback processing has been moved to agent-coordinator (callback_processor.py).
The agent-coordinator now handles callbacks when it receives session_stop events,
which allows proper queuing when the parent is busy. See:
- docs/features/06-callback-queue-busy-parent.md
- servers/agent-coordinator/services/callback_processor.py
"""

import threading
import time
import logging

from api_client import CoordinatorAPIClient
from registry import RunningRunsRegistry

logger = logging.getLogger(__name__)


class RunSupervisor:
    """Background thread that monitors running agent runs for completion."""

    def __init__(
        self,
        api_client: CoordinatorAPIClient,
        registry: RunningRunsRegistry,
        launcher_id: str,
        check_interval: float = 1.0,
    ):
        """Initialize the supervisor.

        Args:
            api_client: HTTP client for Agent Coordinator
            registry: Registry of running agent runs
            launcher_id: This launcher's ID
            check_interval: How often to check subprocess status (seconds)
        """
        self.api_client = api_client
        self.registry = registry
        self.launcher_id = launcher_id
        self.check_interval = check_interval

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the supervisor thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Supervisor already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._supervision_loop, daemon=True)
        self._thread.start()
        logger.info("Supervisor started")

    def stop(self) -> None:
        """Stop the supervisor thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Supervisor stopped")

    def _supervision_loop(self) -> None:
        """Main supervision loop."""
        while not self._stop_event.is_set():
            try:
                self._check_runs()
            except Exception as e:
                logger.error(f"Supervision error: {e}")

            time.sleep(self.check_interval)

    def _check_runs(self) -> None:
        """Check all running agent runs for completion."""
        runs = self.registry.get_all_runs()

        for run_id, running_run in runs.items():
            # Check if process has finished
            return_code = running_run.process.poll()

            if return_code is not None:
                # Process has finished
                self._handle_completion(run_id, running_run, return_code)

    def _handle_completion(self, run_id: str, running_run, return_code: int) -> None:
        """Handle agent run completion (success or failure).

        Reports completion status to agent-coordinator. Callback processing
        is handled by agent-coordinator when it receives the session_stop event.
        """
        # Remove from registry first
        self.registry.remove_run(run_id)

        # Get any output
        stdout, stderr = "", ""
        try:
            stdout, stderr = running_run.process.communicate(timeout=1.0)
        except Exception:
            pass

        if return_code == 0:
            logger.info(f"Agent run {run_id} completed successfully (session={running_run.session_name})")
            try:
                self.api_client.report_completed(self.launcher_id, run_id)
            except Exception as e:
                logger.error(f"Failed to report completion for {run_id}: {e}")
        else:
            error_msg = stderr.strip() if stderr else f"Process exited with code {return_code}"
            logger.error(f"Agent run {run_id} failed: {error_msg}")
            try:
                self.api_client.report_failed(self.launcher_id, run_id, error_msg)
            except Exception as e:
                logger.error(f"Failed to report failure for {run_id}: {e}")
