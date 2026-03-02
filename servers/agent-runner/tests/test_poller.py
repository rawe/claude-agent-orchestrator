"""
Tests for RunPoller - background thread that polls coordinator for runs and commands.

Tests cover:
- _handle_run: start session, resume routing, busy guard, broken pipe, one-shot resume
- _handle_stop: graceful shutdown, SIGTERM, SIGKILL escalation, idle sessions
- _poll_loop: deregistration signal, connection failure retries
"""

import subprocess
import time
from unittest.mock import MagicMock, patch, call

from api_client import Run, PollResult
from registry import ProcessRegistry
from poller import RunPoller


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run(
    run_id="run_001",
    run_type="start_session",
    session_id="ses_001",
    prompt="Hello",
    agent_name=None,
    project_dir=None,
):
    """Create a Run dataclass for tests."""
    return Run(
        run_id=run_id,
        type=run_type,
        session_id=session_id,
        agent_name=agent_name,
        parameters={"prompt": prompt},
        project_dir=project_dir,
    )


def _mock_process(pid=1234, poll_return=None):
    """Create a mock subprocess.Popen that appears running."""
    proc = MagicMock(spec=subprocess.Popen)
    proc.pid = pid
    proc.poll.return_value = poll_return
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = MagicMock()
    return proc


def _make_poller(
    api_client=None,
    executor=None,
    registry=None,
    runner_id="lnch_test",
    on_deregistered=None,
    persistent=False,
):
    """Create a RunPoller with mocks, NOT started."""
    api = api_client or MagicMock()
    exe = executor or MagicMock()
    exe.is_persistent = persistent
    reg = registry or ProcessRegistry()

    poller = RunPoller(
        api_client=api,
        executor=exe,
        registry=reg,
        runner_id=runner_id,
        on_deregistered=on_deregistered,
    )
    return poller


# ===========================================================================
# TestHandleRun
# ===========================================================================

class TestHandleRun:
    """Tests for _handle_run method."""

    def test_start_session_spawns_process(self):
        """start_session: executor.execute_run called, session registered, report_started called."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = False
        mock_process = _mock_process()
        mock_executor.execute_run.return_value = mock_process

        registry = ProcessRegistry()
        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
        )

        run = _make_run(run_id="run_001", session_id="ses_001")
        poller._handle_run(run)

        # Verify executor was called
        mock_executor.execute_run.assert_called_once_with(run)

        # Verify session registered
        entry = registry.get_session("ses_001")
        assert entry is not None
        assert entry.process is mock_process
        assert entry.current_run_id == "run_001"
        assert entry.persistent is False

        # Verify report_started
        mock_api.report_started.assert_called_once_with("lnch_test", "run_001")

    def test_start_session_persistent_starts_stdout_reader(self):
        """Persistent executor triggers _start_stdout_reader callback."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = True
        mock_process = _mock_process()
        mock_executor.execute_run.return_value = mock_process

        registry = ProcessRegistry()
        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
            persistent=True,
        )

        # Set the stdout reader callback
        stdout_reader = MagicMock()
        poller._start_stdout_reader = stdout_reader

        run = _make_run(run_id="run_001", session_id="ses_001")
        poller._handle_run(run)

        # Verify stdout reader was called with session_id and process
        stdout_reader.assert_called_once_with("ses_001", mock_process)

        # Verify session registered as persistent
        entry = registry.get_session("ses_001")
        assert entry is not None
        assert entry.persistent is True

    def test_resume_persistent_routes_turn(self):
        """Resume with persistent entry (no current_run_id) sends turn, swaps run, reports started."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = True
        mock_process = _mock_process()

        registry = ProcessRegistry()
        # Pre-register a persistent session with no active run (idle)
        registry.register_session("ses_001", mock_process, "run_000", persistent=True)
        registry.clear_run("ses_001")  # Clear run to simulate idle

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
            persistent=True,
        )

        run = _make_run(
            run_id="run_002",
            run_type="resume_session",
            session_id="ses_001",
        )
        poller._handle_run(run)

        # Verify turn was sent to existing process
        mock_executor.send_turn.assert_called_once_with(mock_process, run)

        # Verify run was swapped in registry
        entry = registry.get_session("ses_001")
        assert entry.current_run_id == "run_002"

        # Verify report_started
        mock_api.report_started.assert_called_once_with("lnch_test", "run_002")

        # Verify execute_run was NOT called (no new process)
        mock_executor.execute_run.assert_not_called()

    def test_resume_busy_session_fails(self):
        """Resume persistent session with active run_id reports failure."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = True
        mock_process = _mock_process()

        registry = ProcessRegistry()
        # Pre-register with an active run
        registry.register_session("ses_001", mock_process, "run_001", persistent=True)

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
            persistent=True,
        )

        run = _make_run(
            run_id="run_002",
            run_type="resume_session",
            session_id="ses_001",
        )
        poller._handle_run(run)

        # Verify report_failed with "busy" message
        mock_api.report_failed.assert_called_once()
        args = mock_api.report_failed.call_args
        assert args[0][0] == "lnch_test"
        assert args[0][1] == "run_002"
        assert "busy" in args[0][2].lower() or "busy" in args[0][2]

        # Verify no turn was sent
        mock_executor.send_turn.assert_not_called()

    def test_resume_no_process_fails(self):
        """Resume with no entry in registry reports failure."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = False

        registry = ProcessRegistry()
        # No session registered

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
        )

        run = _make_run(
            run_id="run_002",
            run_type="resume_session",
            session_id="ses_001",
        )
        poller._handle_run(run)

        # Verify report_failed with "No live executor" message
        mock_api.report_failed.assert_called_once()
        args = mock_api.report_failed.call_args
        assert args[0][0] == "lnch_test"
        assert args[0][1] == "run_002"
        assert "no live executor" in args[0][2].lower()

        # Verify execute_run was NOT called
        mock_executor.execute_run.assert_not_called()

    def test_resume_oneshot_spawns_new_process(self):
        """Resume with non-persistent (one-shot) entry falls through to execute_run."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = False
        new_process = _mock_process(pid=5678)
        mock_executor.execute_run.return_value = new_process

        registry = ProcessRegistry()
        # Pre-register a one-shot session
        old_process = _mock_process(pid=1234)
        registry.register_session("ses_001", old_process, "run_001", persistent=False)
        registry.clear_run("ses_001")

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
        )

        run = _make_run(
            run_id="run_002",
            run_type="resume_session",
            session_id="ses_001",
        )
        poller._handle_run(run)

        # Verify execute_run was called (spawns new process)
        mock_executor.execute_run.assert_called_once_with(run)

        # Verify session was re-registered with new process
        entry = registry.get_session("ses_001")
        assert entry.process is new_process
        assert entry.current_run_id == "run_002"

        # Verify report_started
        mock_api.report_started.assert_called_once_with("lnch_test", "run_002")

    def test_resume_broken_pipe_reports_failed(self):
        """send_turn raising BrokenPipeError removes session and reports failure."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = True
        mock_executor.send_turn.side_effect = BrokenPipeError("pipe broken")
        mock_process = _mock_process()

        registry = ProcessRegistry()
        registry.register_session("ses_001", mock_process, "run_000", persistent=True)
        registry.clear_run("ses_001")  # idle

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
            persistent=True,
        )

        run = _make_run(
            run_id="run_002",
            run_type="resume_session",
            session_id="ses_001",
        )
        poller._handle_run(run)

        # Verify session removed from registry
        assert registry.get_session("ses_001") is None

        # Verify report_failed
        mock_api.report_failed.assert_called_once()
        args = mock_api.report_failed.call_args
        assert args[0][0] == "lnch_test"
        assert args[0][1] == "run_002"
        assert "no longer running" in args[0][2].lower()


# ===========================================================================
# TestHandleStop
# ===========================================================================

class TestHandleStop:
    """Tests for _handle_stop method."""

    def test_stop_terminates_oneshot(self):
        """One-shot process: SIGTERM, report_stopped."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = False

        proc = _mock_process()
        proc.poll.return_value = None  # still running

        registry = ProcessRegistry()
        registry.register_session("ses_001", proc, "run_001", persistent=False)

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
        )

        poller._handle_stop("ses_001")

        # Verify terminate was called
        proc.terminate.assert_called_once()

        # Verify wait was called after terminate
        proc.wait.assert_called()

        # Verify session removed from registry
        assert registry.get_session("ses_001") is None

        # Verify report_stopped with SIGTERM
        mock_api.report_stopped.assert_called_once_with(
            "lnch_test", "run_001", signal="SIGTERM"
        )

    def test_stop_persistent_tries_shutdown_first(self):
        """Persistent process: send_shutdown + wait succeeds, signal='shutdown'."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = True

        proc = _mock_process()
        # After shutdown + wait succeeds, poll returns non-None (process exited)
        proc.poll.return_value = 0  # exited

        registry = ProcessRegistry()
        registry.register_session("ses_001", proc, "run_001", persistent=True)

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
            persistent=True,
        )

        poller._handle_stop("ses_001")

        # Verify send_shutdown was called
        mock_executor.send_shutdown.assert_called_once_with(proc)

        # Verify wait was called (graceful shutdown)
        proc.wait.assert_called()

        # Verify terminate was NOT called (process exited via shutdown)
        proc.terminate.assert_not_called()

        # Verify report_stopped with shutdown signal
        mock_api.report_stopped.assert_called_once_with(
            "lnch_test", "run_001", signal="shutdown"
        )

    def test_stop_escalates_to_sigkill(self):
        """When process.wait always times out: SIGTERM then SIGKILL escalation."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = False

        proc = _mock_process()
        proc.poll.return_value = None  # always running
        proc.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)

        registry = ProcessRegistry()
        registry.register_session("ses_001", proc, "run_001", persistent=False)

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
        )

        poller._handle_stop("ses_001")

        # Verify escalation: terminate then kill
        proc.terminate.assert_called_once()
        proc.kill.assert_called_once()

        # Verify report_stopped with SIGKILL
        mock_api.report_stopped.assert_called_once_with(
            "lnch_test", "run_001", signal="SIGKILL"
        )

    def test_stop_idle_reports_session_status(self):
        """No current_run_id (idle) reports session status instead of report_stopped."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = True

        proc = _mock_process()
        proc.poll.return_value = 0  # exited after shutdown

        registry = ProcessRegistry()
        registry.register_session("ses_001", proc, "run_001", persistent=True)
        registry.clear_run("ses_001")  # make idle

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
            persistent=True,
        )

        poller._handle_stop("ses_001")

        # Verify report_stopped NOT called (no active run)
        mock_api.report_stopped.assert_not_called()

        # Verify report_session_status called
        mock_api.report_session_status.assert_called_once()
        args = mock_api.report_session_status.call_args
        assert args[0][0] == "lnch_test"
        assert args[0][1] == "ses_001"
        # Should be "finished" because shutdown succeeded (signal_used == "shutdown")
        assert args[0][2] == "finished"

    def test_stop_nonexistent_session_ignored(self):
        """No entry in registry: no error, no API calls."""
        mock_api = MagicMock()
        mock_executor = MagicMock()

        registry = ProcessRegistry()

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
        )

        # Should not raise
        poller._handle_stop("ses_nonexistent")

        # No API calls should be made
        mock_api.report_stopped.assert_not_called()
        mock_api.report_session_status.assert_not_called()
        mock_api.report_failed.assert_not_called()

    def test_stop_marks_stopping(self):
        """Verify registry.mark_stopping() is called before termination."""
        mock_api = MagicMock()
        mock_executor = MagicMock()
        mock_executor.is_persistent = False

        proc = _mock_process()
        proc.poll.return_value = None

        registry = ProcessRegistry()
        registry.register_session("ses_001", proc, "run_001", persistent=False)

        poller = _make_poller(
            api_client=mock_api,
            executor=mock_executor,
            registry=registry,
        )

        # We need to verify mark_stopping is called. Since we use a real
        # registry, we spy on it.
        original_mark_stopping = registry.mark_stopping
        mark_stopping_calls = []

        def spy_mark_stopping(session_id):
            mark_stopping_calls.append(session_id)
            return original_mark_stopping(session_id)

        registry.mark_stopping = spy_mark_stopping

        poller._handle_stop("ses_001")

        assert "ses_001" in mark_stopping_calls


# ===========================================================================
# TestPollLoop
# ===========================================================================

class TestPollLoop:
    """Tests for _poll_loop method."""

    @patch("poller.time.sleep")
    def test_deregistration_exits_loop(self, mock_sleep):
        """poll_run returns deregistered=True: on_deregistered called, loop exits."""
        mock_api = MagicMock()
        mock_api.poll_run.return_value = PollResult(deregistered=True)

        on_dereg = MagicMock()
        poller = _make_poller(
            api_client=mock_api,
            on_deregistered=on_dereg,
        )

        # Call _poll_loop directly (not starting a thread)
        poller._poll_loop()

        # Verify poll was called
        mock_api.poll_run.assert_called_once_with("lnch_test")

        # Verify on_deregistered callback was called
        on_dereg.assert_called_once()

    @patch("poller.time.sleep")
    def test_connection_failures_exit_after_retries(self, mock_sleep):
        """poll_run raises exception 3 times: on_deregistered called after MAX_CONNECTION_RETRIES."""
        mock_api = MagicMock()
        mock_api.poll_run.side_effect = ConnectionError("refused")

        on_dereg = MagicMock()
        poller = _make_poller(
            api_client=mock_api,
            on_deregistered=on_dereg,
        )

        poller._poll_loop()

        # Verify poll was called exactly 3 times (MAX_CONNECTION_RETRIES)
        assert mock_api.poll_run.call_count == 3

        # Verify on_deregistered callback was called
        on_dereg.assert_called_once()

        # Verify sleep was called for backoff (between failures, not after last)
        assert mock_sleep.call_count == 2  # sleep after failure 1 and 2, not after 3
