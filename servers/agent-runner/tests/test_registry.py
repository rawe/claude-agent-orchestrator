"""
Tests for ProcessRegistry - thread-safe session→process mapping.

Tests cover:
- Register/get/remove sessions
- Dual index (session_id and run_id)
- Swap and clear run operations
- Stopping dedup guard
- Concurrent access safety
"""

import subprocess
import threading
from unittest.mock import MagicMock

from registry import ProcessRegistry


def _mock_process(pid=1234, poll_return=None):
    """Create a mock subprocess.Popen."""
    proc = MagicMock(spec=subprocess.Popen)
    proc.pid = pid
    proc.poll.return_value = poll_return
    return proc


class TestRegisterAndGet:
    """Test basic register and lookup operations."""

    def test_register_and_get_session(self):
        reg = ProcessRegistry()
        proc = _mock_process()
        reg.register_session("ses_001", proc, "run_001")

        entry = reg.get_session("ses_001")
        assert entry is not None
        assert entry.session_id == "ses_001"
        assert entry.process is proc
        assert entry.current_run_id == "run_001"
        assert entry.persistent is False

    def test_register_persistent_session(self):
        reg = ProcessRegistry()
        proc = _mock_process()
        reg.register_session("ses_001", proc, "run_001", persistent=True)

        entry = reg.get_session("ses_001")
        assert entry.persistent is True

    def test_get_nonexistent_session(self):
        reg = ProcessRegistry()
        assert reg.get_session("ses_nonexistent") is None

    def test_count(self):
        reg = ProcessRegistry()
        assert reg.count() == 0

        reg.register_session("ses_001", _mock_process(), "run_001")
        assert reg.count() == 1

        reg.register_session("ses_002", _mock_process(), "run_002")
        assert reg.count() == 2

    def test_get_all_sessions_returns_copy(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001")

        all_sessions = reg.get_all_sessions()
        assert "ses_001" in all_sessions
        assert len(all_sessions) == 1

        # Modifying the copy should not affect registry
        all_sessions.pop("ses_001")
        assert reg.count() == 1


class TestDualIndex:
    """Test session_id and run_id dual indexing."""

    def test_get_session_by_run(self):
        reg = ProcessRegistry()
        proc = _mock_process()
        reg.register_session("ses_001", proc, "run_001")

        entry = reg.get_session_by_run("run_001")
        assert entry is not None
        assert entry.session_id == "ses_001"

    def test_get_session_by_nonexistent_run(self):
        reg = ProcessRegistry()
        assert reg.get_session_by_run("run_nonexistent") is None

    def test_multiple_sessions_indexed_by_run(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001")
        reg.register_session("ses_002", _mock_process(), "run_002")

        assert reg.get_session_by_run("run_001").session_id == "ses_001"
        assert reg.get_session_by_run("run_002").session_id == "ses_002"


class TestSwapRun:
    """Test atomic run_id swap for persistent sessions."""

    def test_swap_run_updates_indexes(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001")

        old = reg.swap_run("ses_001", "run_002")
        assert old == "run_001"

        # New run_id works
        entry = reg.get_session_by_run("run_002")
        assert entry is not None
        assert entry.session_id == "ses_001"
        assert entry.current_run_id == "run_002"

        # Old run_id no longer indexed
        assert reg.get_session_by_run("run_001") is None

    def test_swap_run_nonexistent_session(self):
        reg = ProcessRegistry()
        assert reg.swap_run("ses_nonexistent", "run_001") is None

    def test_swap_run_when_no_previous_run(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001")
        reg.clear_run("ses_001")

        old = reg.swap_run("ses_001", "run_002")
        assert old is None
        assert reg.get_session_by_run("run_002").session_id == "ses_001"


class TestClearRun:
    """Test clearing run_id (turn complete, process stays alive)."""

    def test_clear_run(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001")

        cleared = reg.clear_run("ses_001")
        assert cleared == "run_001"

        entry = reg.get_session("ses_001")
        assert entry is not None
        assert entry.current_run_id is None

        # Run index cleared
        assert reg.get_session_by_run("run_001") is None

    def test_clear_run_nonexistent_session(self):
        reg = ProcessRegistry()
        assert reg.clear_run("ses_nonexistent") is None

    def test_clear_run_already_cleared(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001")
        reg.clear_run("ses_001")

        # Second clear returns None (no run to clear)
        assert reg.clear_run("ses_001") is None


class TestRemoveSession:
    """Test session removal from both indexes."""

    def test_remove_session(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001")

        entry = reg.remove_session("ses_001")
        assert entry is not None
        assert entry.session_id == "ses_001"

        # Both indexes cleared
        assert reg.get_session("ses_001") is None
        assert reg.get_session_by_run("run_001") is None
        assert reg.count() == 0

    def test_remove_nonexistent_session(self):
        reg = ProcessRegistry()
        assert reg.remove_session("ses_nonexistent") is None

    def test_remove_clears_stopping_flag(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001")
        reg.mark_stopping("ses_001")
        assert reg.is_stopping("ses_001") is True

        reg.remove_session("ses_001")
        assert reg.is_stopping("ses_001") is False


class TestStoppingGuard:
    """Test stopping dedup guard."""

    def test_mark_and_check_stopping(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001")

        assert reg.is_stopping("ses_001") is False
        reg.mark_stopping("ses_001")
        assert reg.is_stopping("ses_001") is True

    def test_is_stopping_unknown_session(self):
        reg = ProcessRegistry()
        assert reg.is_stopping("ses_nonexistent") is False


class TestConcurrency:
    """Test thread safety of registry operations."""

    def test_concurrent_register_and_get(self):
        reg = ProcessRegistry()
        errors = []

        def register_sessions(start_idx, count):
            try:
                for i in range(count):
                    sid = f"ses_{start_idx + i:04d}"
                    rid = f"run_{start_idx + i:04d}"
                    reg.register_session(sid, _mock_process(pid=start_idx + i), rid)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_sessions, args=(0, 50)),
            threading.Thread(target=register_sessions, args=(50, 50)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert reg.count() == 100

    def test_concurrent_swap_and_clear(self):
        reg = ProcessRegistry()
        reg.register_session("ses_001", _mock_process(), "run_001", persistent=True)
        errors = []

        def swap_runs():
            try:
                for i in range(50):
                    reg.swap_run("ses_001", f"run_swap_{i}")
            except Exception as e:
                errors.append(e)

        def clear_runs():
            try:
                for _ in range(50):
                    reg.clear_run("ses_001")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=swap_runs)
        t2 = threading.Thread(target=clear_runs)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0
        # Session should still exist
        assert reg.get_session("ses_001") is not None
