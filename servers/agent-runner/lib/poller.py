"""
Poll Thread - continuously polls Agent Coordinator for new agent runs.

Runs in a background thread, spawning subprocesses for each agent run.
"""

import os
import json
import stat
import threading
import time
import tarfile
import shutil
import logging
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional

from api_client import CoordinatorAPIClient, Run, PollResult
from executor import RunExecutor
from registry import RunningRunsRegistry

logger = logging.getLogger(__name__)


def get_scripts_dir() -> Path:
    """
    Get scripts directory for synced scripts.

    Scripts are stored in {PROJECT_DIR}/scripts/ where PROJECT_DIR
    is the runner's working directory.
    """
    project_dir = os.environ.get("PROJECT_DIR", os.getcwd())
    return Path(project_dir) / "scripts"

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

        # Scripts directory for synced scripts
        self._scripts_dir = get_scripts_dir()
        self._scripts_dir.mkdir(parents=True, exist_ok=True)

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

                # Handle script sync commands
                if result.sync_scripts or result.remove_scripts:
                    for script_name in result.sync_scripts:
                        self._handle_script_sync(script_name)
                    for script_name in result.remove_scripts:
                        self._handle_script_remove(script_name)
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

    def _handle_script_sync(self, script_name: str) -> None:
        """Download and extract a script from the coordinator."""
        logger.info(f"Syncing script: {script_name}")

        try:
            # Download the script tarball
            tarball = self.api_client.download_script(script_name)
            if not tarball:
                logger.error(f"Failed to download script {script_name}")
                return

            logger.debug(f"Downloaded tarball for {script_name}: {len(tarball)} bytes")

            # Ensure scripts directory exists
            self._scripts_dir.mkdir(parents=True, exist_ok=True)

            # Extract to scripts directory
            script_dir = self._scripts_dir / script_name

            # Remove existing script directory if it exists
            if script_dir.exists():
                shutil.rmtree(script_dir)

            # Extract tarball (contains script_name/ prefix, extracts to scripts/script_name/)
            with tarfile.open(fileobj=BytesIO(tarball), mode="r:gz") as tar:
                # Log tarball contents for debugging
                members = tar.getnames()
                logger.debug(f"Tarball contains: {members}")
                # filter='tar' for security: blocks dangerous paths but allows directory creation
                tar.extractall(path=self._scripts_dir, filter='tar')

            # Verify extraction succeeded
            script_json_path = script_dir / "script.json"
            if not script_json_path.exists():
                logger.error(f"Extraction failed: {script_json_path} not found after extraction")
                return

            # Read script.json to get script_file and make it executable
            with open(script_json_path, "r") as f:
                script_meta = json.load(f)

            script_file = script_meta.get("script_file")
            if script_file:
                script_file_path = script_dir / script_file
                if script_file_path.exists():
                    # Add executable permission (owner, group, others)
                    current_mode = script_file_path.stat().st_mode
                    script_file_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    logger.debug(f"Made script executable: {script_file_path}")
                else:
                    logger.warning(f"Script file not found: {script_file_path}")

            logger.info(f"Script synced: {script_name} -> {script_dir}")

        except Exception as e:
            logger.error(f"Error syncing script {script_name}: {e}", exc_info=True)

    def _handle_script_remove(self, script_name: str) -> None:
        """Remove a script from the local scripts directory."""
        logger.info(f"Removing script: {script_name}")

        try:
            script_dir = self._scripts_dir / script_name
            if script_dir.exists():
                shutil.rmtree(script_dir)
                logger.info(f"Script removed: {script_name}")
            else:
                logger.debug(f"Script not found locally, nothing to remove: {script_name}")

        except Exception as e:
            logger.error(f"Error removing script {script_name}: {e}")
