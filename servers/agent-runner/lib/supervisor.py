"""
Supervisor Thread - monitors running agent run subprocesses for completion.

Checks subprocess status periodically and reports completion/failure.

NOTE: Callback processing has been moved to agent-coordinator (callback_processor.py).
The agent-coordinator now handles callbacks when it receives run_completed events,
which allows proper queuing when the parent is busy. See:
- docs/features/06-callback-queue-busy-parent.md
- servers/agent-coordinator/services/callback_processor.py
"""

import json
import subprocess
import threading
import time
import logging

from api_client import CoordinatorAPIClient
from registry import ProcessRegistry

logger = logging.getLogger(__name__)


class RunSupervisor:
    """Background thread that monitors running agent runs for completion."""

    def __init__(
        self,
        api_client: CoordinatorAPIClient,
        registry: ProcessRegistry,
        runner_id: str,
        check_interval: float = 1.0,
    ):
        """Initialize the supervisor.

        Args:
            api_client: HTTP client for Agent Coordinator
            registry: Registry of running agent runs
            runner_id: This runner's ID
            check_interval: How often to check subprocess status (seconds)
        """
        self.api_client = api_client
        self.registry = registry
        self.runner_id = runner_id
        self.check_interval = check_interval

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Dedup set for reported runs (prevents double-reporting between stdout reader and poll loop)
        self._reported_runs: set[str] = set()
        self._reported_runs_lock = threading.Lock()
        self._stdout_threads: list[threading.Thread] = []

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
        """Check all sessions for process exit."""
        sessions = self.registry.get_all_sessions()

        for session_id, entry in sessions.items():
            return_code = entry.process.poll()
            if return_code is not None:
                if entry.persistent:
                    self._handle_persistent_exit(session_id, entry, return_code)
                else:
                    self._handle_oneshot_exit(session_id, entry, return_code)

    def _handle_oneshot_exit(self, session_id: str, entry, return_code: int) -> None:
        """Handle one-shot agent run completion (success or failure).

        Reports completion status to agent-coordinator. Callback processing
        is handled by agent-coordinator when it receives the run_completed event.
        """
        run_id = entry.current_run_id

        # Remove from registry first
        self.registry.remove_session(session_id)

        # Get any output from the process
        # Read directly from pipes instead of using communicate() to avoid
        # "I/O operation on closed file" errors when process exits quickly
        stdout, stderr = "", ""
        try:
            # Check pipe status for diagnostics
            stdout_status = "closed" if (not entry.process.stdout or entry.process.stdout.closed) else "open"
            stderr_status = "closed" if (not entry.process.stderr or entry.process.stderr.closed) else "open"

            # Try reading directly from pipes
            if entry.process.stdout and not entry.process.stdout.closed:
                stdout = entry.process.stdout.read() or ""
            if entry.process.stderr and not entry.process.stderr.closed:
                stderr = entry.process.stderr.read() or ""

            # Log if pipes were already closed (helps diagnose fast-exit issues)
            if stdout_status == "closed" or stderr_status == "closed":
                logger.debug(
                    f"Process for session {session_id} pipes status: stdout={stdout_status}, stderr={stderr_status}"
                )
        except Exception as e:
            # Fall back to communicate() if direct read fails
            try:
                stdout, stderr = entry.process.communicate(timeout=5.0)
            except Exception as e2:
                logger.warning(
                    f"Failed to get output from process for session {session_id}: "
                    f"direct read: {e}, communicate: {e2}"
                )

        if return_code == 0:
            logger.info(f"Agent run {run_id} completed successfully (session={session_id})")
            try:
                self.api_client.report_completed(self.runner_id, run_id, session_status="finished")
            except Exception as e:
                logger.error(f"Failed to report completion for {run_id}: {e}")
        else:
            # Build error message: prefer stderr, fall back to stdout, then generic message
            if stderr and stderr.strip():
                error_msg = stderr.strip()
            elif stdout and stdout.strip():
                error_msg = f"(stdout) {stdout.strip()}"
            else:
                error_msg = f"Process exited with code {return_code}"

            # Log detailed failure info for debugging
            logger.error(f"Agent run {run_id} failed (exit_code={return_code}, session={session_id})")
            logger.error(f"  Error: {error_msg}")
            if stdout and stdout.strip():
                # Truncate long output for logging
                stdout_preview = stdout.strip()[:1000]
                if len(stdout.strip()) > 1000:
                    stdout_preview += "... (truncated)"
                logger.debug(f"  stdout: {stdout_preview}")
            if stderr and stderr.strip():
                stderr_preview = stderr.strip()[:1000]
                if len(stderr.strip()) > 1000:
                    stderr_preview += "... (truncated)"
                logger.debug(f"  stderr: {stderr_preview}")

            try:
                self.api_client.report_failed(self.runner_id, run_id, error_msg)
            except Exception as e:
                logger.error(f"Failed to report failure for {run_id}: {e}")

    def _handle_persistent_exit(self, session_id: str, entry, return_code: int) -> None:
        """Handle unexpected exit of a persistent process."""
        run_id = entry.current_run_id
        self.registry.remove_session(session_id)

        if run_id:
            # Process died with an active run — this is a crash
            with self._reported_runs_lock:
                if run_id in self._reported_runs:
                    return
                self._reported_runs.add(run_id)

            stderr = self._read_stderr(entry)
            error_msg = stderr or f"Persistent process exited with code {return_code}"
            logger.error(f"Persistent process crashed for session {session_id} (run={run_id}, exit_code={return_code})")
            try:
                self.api_client.report_failed(self.runner_id, run_id, error_msg)
            except Exception as e:
                logger.error(f"Failed to report crash for {run_id}: {e}")
        else:
            # Process was idle (between turns) and exited
            status = "finished" if return_code == 0 else "failed"
            logger.info(f"Idle persistent process exited for session {session_id} (exit_code={return_code}, status={status})")
            try:
                self.api_client.report_session_status(self.runner_id, session_id, status)
            except Exception as e:
                logger.error(f"Failed to report session status for {session_id}: {e}")

    def _read_stderr(self, entry) -> str:
        """Read stderr from a process for error reporting."""
        try:
            if entry.process.stderr and not entry.process.stderr.closed:
                return entry.process.stderr.read() or ""
        except Exception:
            pass
        return ""

    def start_stdout_reader(self, session_id: str, process: subprocess.Popen) -> None:
        """Start a stdout reader thread for a persistent process."""
        thread = threading.Thread(
            target=self._stdout_reader_loop,
            args=(session_id, process),
            daemon=True,
        )
        thread.start()
        self._stdout_threads.append(thread)
        logger.debug(f"Started stdout reader for session {session_id}")

    def _stdout_reader_loop(self, session_id: str, process: subprocess.Popen) -> None:
        """Read NDJSON from persistent process stdout."""
        try:
            for line in iter(process.stdout.readline, ''):
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue  # skip non-JSON output
                if msg.get("type") == "turn_complete":
                    self._report_turn_complete(session_id)
        except Exception as e:
            logger.error(f"Stdout reader error for session {session_id}: {e}")
        finally:
            logger.debug(f"Stdout reader exiting for session {session_id}")

    def _report_turn_complete(self, session_id: str) -> None:
        """Handle turn_complete from stdout reader."""
        entry = self.registry.get_session(session_id)
        if not entry or not entry.current_run_id:
            return
        run_id = entry.current_run_id

        with self._reported_runs_lock:
            if run_id in self._reported_runs:
                return  # already reported
            self._reported_runs.add(run_id)

        self.registry.clear_run(session_id)

        try:
            self.api_client.report_completed(self.runner_id, run_id, session_status="idle")
            logger.info(f"Turn complete for run {run_id} (session={session_id})")
        except Exception as e:
            logger.error(f"Failed to report turn complete for {run_id}: {e}")
