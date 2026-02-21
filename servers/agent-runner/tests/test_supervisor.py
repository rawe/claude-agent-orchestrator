"""
Unit tests for RunSupervisor - background thread monitoring executor subprocesses.

Tests cover:
- One-shot process exit (success/failure)
- Persistent process exit (crash with active run, idle exit, stopping dedup)
- Stdout reader (turn_complete NDJSON, non-JSON tolerance, dedup)
"""

import os
import subprocess
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from registry import ProcessRegistry, SessionProcess
from supervisor import RunSupervisor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_process(poll_return=None, stdout_text="", stderr_text=""):
    """Create a MagicMock that behaves like subprocess.Popen."""
    proc = MagicMock(spec=subprocess.Popen)
    proc.pid = 1234
    proc.poll.return_value = poll_return

    proc.stdout = MagicMock()
    proc.stdout.closed = False
    proc.stdout.read.return_value = stdout_text

    proc.stderr = MagicMock()
    proc.stderr.closed = False
    proc.stderr.read.return_value = stderr_text

    return proc


def _make_api_client():
    """Create a mock CoordinatorAPIClient."""
    mock_api = MagicMock()
    mock_api.report_completed = MagicMock()
    mock_api.report_failed = MagicMock()
    mock_api.report_session_status = MagicMock()
    return mock_api


RUNNER_ID = "test-runner-001"


# ===========================================================================
# TestOneshotExit
# ===========================================================================

class TestOneshotExit:
    """Tests for one-shot process exit handling."""

    def test_oneshot_success_reports_completed(self):
        """Process exits with code 0 -> report_completed(session_status='finished')."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=0)
        registry.register_session("sess-1", proc, "run-1", persistent=False)

        supervisor._check_runs()

        api.report_completed.assert_called_once_with(
            RUNNER_ID, "run-1", session_status="finished"
        )

    def test_oneshot_failure_reports_failed(self):
        """Process exits with non-zero code -> report_failed with stderr."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=1, stderr_text="segfault in module X")
        registry.register_session("sess-2", proc, "run-2", persistent=False)

        supervisor._check_runs()

        api.report_failed.assert_called_once_with(
            RUNNER_ID, "run-2", "segfault in module X"
        )

    def test_oneshot_failure_uses_stdout_when_no_stderr(self):
        """When stderr is empty, error message falls back to stdout."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=1, stdout_text="stdout error info", stderr_text="")
        registry.register_session("sess-3", proc, "run-3", persistent=False)

        supervisor._check_runs()

        api.report_failed.assert_called_once_with(
            RUNNER_ID, "run-3", "(stdout) stdout error info"
        )

    def test_oneshot_failure_generic_when_no_output(self):
        """When both stderr and stdout are empty, uses generic exit code message."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=137, stdout_text="", stderr_text="")
        registry.register_session("sess-4", proc, "run-4", persistent=False)

        supervisor._check_runs()

        api.report_failed.assert_called_once_with(
            RUNNER_ID, "run-4", "Process exited with code 137"
        )

    def test_oneshot_removes_from_registry(self):
        """Session is removed from registry after one-shot exit."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=0)
        registry.register_session("sess-5", proc, "run-5", persistent=False)

        assert registry.count() == 1
        supervisor._check_runs()
        assert registry.count() == 0
        assert registry.get_session("sess-5") is None


# ===========================================================================
# TestPersistentExit
# ===========================================================================

class TestPersistentExit:
    """Tests for persistent process exit handling."""

    def test_persistent_crash_reports_failed(self):
        """Persistent process exits with active run_id -> report_failed."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=1, stderr_text="crash: out of memory")
        registry.register_session("sess-p1", proc, "run-p1", persistent=True)

        supervisor._check_runs()

        api.report_failed.assert_called_once_with(
            RUNNER_ID, "run-p1", "crash: out of memory"
        )
        # Session should be removed
        assert registry.get_session("sess-p1") is None

    def test_persistent_crash_generic_error_when_no_stderr(self):
        """Persistent crash with no stderr uses generic message with exit code."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=9, stderr_text="")
        registry.register_session("sess-p1b", proc, "run-p1b", persistent=True)

        supervisor._check_runs()

        api.report_failed.assert_called_once_with(
            RUNNER_ID, "run-p1b", "Persistent process exited with code 9"
        )

    def test_persistent_idle_exit_success(self):
        """Persistent process exits idle (no run_id) with code 0 -> report_session_status('finished')."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=0)
        registry.register_session("sess-p2", proc, "run-p2", persistent=True)
        # Clear the run to simulate idle state
        registry.clear_run("sess-p2")

        supervisor._check_runs()

        api.report_session_status.assert_called_once_with(
            RUNNER_ID, "sess-p2", "finished"
        )

    def test_persistent_idle_exit_failure(self):
        """Persistent process exits idle with code 1 -> report_session_status('failed')."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=1)
        registry.register_session("sess-p3", proc, "run-p3", persistent=True)
        # Clear the run to simulate idle state
        registry.clear_run("sess-p3")

        supervisor._check_runs()

        api.report_session_status.assert_called_once_with(
            RUNNER_ID, "sess-p3", "failed"
        )

    def test_persistent_stopping_skips_reporting(self):
        """When registry.mark_stopping() is set, no report is made on exit."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=0)
        registry.register_session("sess-p4", proc, "run-p4", persistent=True)
        registry.mark_stopping("sess-p4")

        supervisor._check_runs()

        api.report_completed.assert_not_called()
        api.report_failed.assert_not_called()
        api.report_session_status.assert_not_called()


# ===========================================================================
# TestStdoutReader
# ===========================================================================

class TestStdoutReader:
    """Tests for stdout NDJSON reader on persistent processes."""

    def test_turn_complete_reports_idle(self):
        """Write {"type":"turn_complete"} NDJSON -> report_completed(session_status='idle') and clear_run()."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        # Use os.pipe to create a real readable pipe
        read_fd, write_fd = os.pipe()
        read_file = os.fdopen(read_fd, "r")
        write_file = os.fdopen(write_fd, "w")

        proc = MagicMock(spec=subprocess.Popen)
        proc.pid = 5678
        proc.stdout = read_file

        registry.register_session("sess-s1", proc, "run-s1", persistent=True)

        # Write turn_complete NDJSON and close to end iteration
        write_file.write('{"type": "turn_complete"}\n')
        write_file.flush()
        write_file.close()

        # Run the stdout reader loop directly (blocks until EOF)
        supervisor._stdout_reader_loop("sess-s1", proc)

        read_file.close()

        api.report_completed.assert_called_once_with(
            RUNNER_ID, "run-s1", session_status="idle"
        )
        # run_id should be cleared in registry
        entry = registry.get_session("sess-s1")
        assert entry is not None
        assert entry.current_run_id is None

    def test_stdout_reader_ignores_non_json(self):
        """Non-JSON lines are skipped without error."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        read_fd, write_fd = os.pipe()
        read_file = os.fdopen(read_fd, "r")
        write_file = os.fdopen(write_fd, "w")

        proc = MagicMock(spec=subprocess.Popen)
        proc.pid = 5679
        proc.stdout = read_file

        registry.register_session("sess-s2", proc, "run-s2", persistent=True)

        # Write non-JSON lines, then a turn_complete, then close
        write_file.write("this is not json\n")
        write_file.write("also not json {{{}\n")
        write_file.write('{"type": "turn_complete"}\n')
        write_file.flush()
        write_file.close()

        supervisor._stdout_reader_loop("sess-s2", proc)

        read_file.close()

        # Should still process the turn_complete despite preceding garbage
        api.report_completed.assert_called_once_with(
            RUNNER_ID, "run-s2", session_status="idle"
        )

    def test_stdout_reader_ignores_non_turn_complete_json(self):
        """Valid JSON that isn't turn_complete is ignored."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        read_fd, write_fd = os.pipe()
        read_file = os.fdopen(read_fd, "r")
        write_file = os.fdopen(write_fd, "w")

        proc = MagicMock(spec=subprocess.Popen)
        proc.pid = 5680
        proc.stdout = read_file

        registry.register_session("sess-s3", proc, "run-s3", persistent=True)

        write_file.write('{"type": "heartbeat"}\n')
        write_file.write('{"status": "ok"}\n')
        write_file.flush()
        write_file.close()

        supervisor._stdout_reader_loop("sess-s3", proc)

        read_file.close()

        api.report_completed.assert_not_called()
        api.report_failed.assert_not_called()

    def test_dedup_prevents_double_report(self):
        """Pre-populate _reported_runs -> no duplicate report from stdout reader."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        read_fd, write_fd = os.pipe()
        read_file = os.fdopen(read_fd, "r")
        write_file = os.fdopen(write_fd, "w")

        proc = MagicMock(spec=subprocess.Popen)
        proc.pid = 5681
        proc.stdout = read_file

        registry.register_session("sess-s4", proc, "run-s4", persistent=True)

        # Pre-populate dedup set (simulates the exit handler having already reported)
        supervisor._reported_runs.add("run-s4")

        write_file.write('{"type": "turn_complete"}\n')
        write_file.flush()
        write_file.close()

        supervisor._stdout_reader_loop("sess-s4", proc)

        read_file.close()

        # Should NOT report because run-s4 was already in _reported_runs
        api.report_completed.assert_not_called()

    def test_dedup_prevents_double_report_from_exit_handler(self):
        """Pre-populate _reported_runs -> persistent crash handler skips duplicate."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=1, stderr_text="crash")
        registry.register_session("sess-s5", proc, "run-s5", persistent=True)

        # Pre-populate dedup set (simulates stdout reader having already reported)
        supervisor._reported_runs.add("run-s5")

        supervisor._check_runs()

        # Should NOT report because run-s5 was already in _reported_runs
        api.report_failed.assert_not_called()

    def test_empty_lines_are_skipped(self):
        """Empty and whitespace-only lines in stdout are silently skipped."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        read_fd, write_fd = os.pipe()
        read_file = os.fdopen(read_fd, "r")
        write_file = os.fdopen(write_fd, "w")

        proc = MagicMock(spec=subprocess.Popen)
        proc.pid = 5682
        proc.stdout = read_file

        registry.register_session("sess-s6", proc, "run-s6", persistent=True)

        write_file.write("\n")
        write_file.write("   \n")
        write_file.write('{"type": "turn_complete"}\n')
        write_file.flush()
        write_file.close()

        supervisor._stdout_reader_loop("sess-s6", proc)

        read_file.close()

        api.report_completed.assert_called_once_with(
            RUNNER_ID, "run-s6", session_status="idle"
        )


# ===========================================================================
# TestStartStdoutReader
# ===========================================================================

class TestStartStdoutReader:
    """Tests for the start_stdout_reader method that spawns a reader thread."""

    def test_start_stdout_reader_spawns_thread(self):
        """start_stdout_reader creates a daemon thread that reads from process stdout."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        read_fd, write_fd = os.pipe()
        read_file = os.fdopen(read_fd, "r")
        write_file = os.fdopen(write_fd, "w")

        proc = MagicMock(spec=subprocess.Popen)
        proc.pid = 6000
        proc.stdout = read_file

        registry.register_session("sess-t1", proc, "run-t1", persistent=True)

        supervisor.start_stdout_reader("sess-t1", proc)

        # Give the thread a moment to start
        time.sleep(0.1)

        assert len(supervisor._stdout_threads) == 1
        assert supervisor._stdout_threads[0].is_alive()

        # Write turn_complete and close to end the reader
        write_file.write('{"type": "turn_complete"}\n')
        write_file.flush()
        write_file.close()

        # Wait for thread to finish
        supervisor._stdout_threads[0].join(timeout=2.0)

        read_file.close()

        api.report_completed.assert_called_once_with(
            RUNNER_ID, "run-t1", session_status="idle"
        )


# ===========================================================================
# TestProcessWithClosedPipes
# ===========================================================================

class TestProcessWithClosedPipes:
    """Tests for edge cases with closed/missing process pipes."""

    def test_oneshot_with_closed_stdout(self):
        """One-shot exit works when stdout pipe is already closed."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=0)
        proc.stdout.closed = True
        registry.register_session("sess-c1", proc, "run-c1", persistent=False)

        supervisor._check_runs()

        api.report_completed.assert_called_once_with(
            RUNNER_ID, "run-c1", session_status="finished"
        )

    def test_oneshot_with_none_stdout(self):
        """One-shot exit works when stdout is None."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=1, stderr_text="error detail")
        proc.stdout = None
        registry.register_session("sess-c2", proc, "run-c2", persistent=False)

        supervisor._check_runs()

        api.report_failed.assert_called_once_with(
            RUNNER_ID, "run-c2", "error detail"
        )

    def test_persistent_crash_with_closed_stderr(self):
        """Persistent crash reads empty stderr when pipe is closed."""
        registry = ProcessRegistry()
        api = _make_api_client()
        supervisor = RunSupervisor(api, registry, RUNNER_ID, check_interval=0.1)

        proc = _make_mock_process(poll_return=1)
        proc.stderr.closed = True
        registry.register_session("sess-c3", proc, "run-c3", persistent=True)

        supervisor._check_runs()

        # Should use generic message since stderr is closed
        api.report_failed.assert_called_once_with(
            RUNNER_ID, "run-c3", "Persistent process exited with code 1"
        )
