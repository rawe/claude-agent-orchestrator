from datetime import datetime, timezone
from types import SimpleNamespace

import database


def _make_event(session_id, event_type="tool_use", timestamp=None, **kwargs):
    """Helper to create event objects matching insert_event's expected interface."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    defaults = dict(
        session_id=session_id,
        event_type=event_type,
        timestamp=ts,
        tool_name=None,
        tool_input=None,
        tool_output=None,
        error=None,
        exit_code=None,
        reason=None,
        role=None,
        content=None,
        result_text=None,
        result_data=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestEventCRUD:
    def test_create_event(self, db_path):
        """Insert and retrieve an event with all fields."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_evt_01", timestamp=ts)

        event = _make_event(
            session_id="ses_evt_01",
            event_type="tool_use",
            timestamp=ts,
            tool_name="Read",
            tool_input={"path": "/tmp/file.txt"},
            tool_output={"content": "hello"},
        )
        database.insert_event(event)

        events = database.get_events("ses_evt_01")
        assert len(events) == 1
        assert events[0]["session_id"] == "ses_evt_01"
        assert events[0]["event_type"] == "tool_use"
        assert events[0]["tool_name"] == "Read"
        assert events[0]["tool_input"] == {"path": "/tmp/file.txt"}
        assert events[0]["tool_output"] == {"content": "hello"}

    def test_create_result_event(self, db_path):
        """Insert a result event with result_text and result_data."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_evt_result", timestamp=ts)

        event = _make_event(
            session_id="ses_evt_result",
            event_type="result",
            timestamp=ts,
            result_text="Task completed successfully",
            result_data={"status": "ok", "output": 42},
        )
        database.insert_event(event)

        events = database.get_events("ses_evt_result")
        assert len(events) == 1
        assert events[0]["result_text"] == "Task completed successfully"
        assert events[0]["result_data"] == {"status": "ok", "output": 42}

    def test_get_events_for_session(self, db_path):
        """Returns events for correct session only, ordered by timestamp."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_A", timestamp=ts)
        database.create_session(session_id="ses_B", timestamp=ts)

        database.insert_event(_make_event("ses_A", timestamp="2026-01-01T00:00:01Z"))
        database.insert_event(_make_event("ses_A", timestamp="2026-01-01T00:00:02Z"))
        database.insert_event(_make_event("ses_B", timestamp="2026-01-01T00:00:03Z"))

        events_a = database.get_events("ses_A")
        events_b = database.get_events("ses_B")

        assert len(events_a) == 2
        assert len(events_b) == 1
        # Verify ordering (ASC by timestamp)
        assert events_a[0]["timestamp"] <= events_a[1]["timestamp"]

    def test_get_events_empty(self, db_path):
        """Session with no events returns empty list."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_no_events", timestamp=ts)
        events = database.get_events("ses_no_events")
        assert events == []


class TestCascadeDelete:
    def test_cascade_delete_session(self, db_path):
        """Deleting a session removes its runs and events via CASCADE."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_del", timestamp=ts)
        database.create_run(
            run_id="run_del_01",
            session_id="ses_del",
            run_type="start_session",
            parameters="{}",
            created_at=ts,
        )
        database.insert_event(_make_event("ses_del", timestamp=ts))
        database.insert_event(_make_event("ses_del", timestamp=ts))

        result = database.delete_session("ses_del")
        assert result is not None
        assert result["session"] is True
        assert result["runs_count"] == 1
        assert result["events_count"] == 2

        # Verify everything is gone
        assert database.get_session_by_id("ses_del") is None
        assert database.get_run_by_id("run_del_01") is None
        assert database.get_events("ses_del") == []

    def test_cascade_preserves_other_sessions(self, db_path):
        """Deleting session A doesn't affect session B's data."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_keep", timestamp=ts)
        database.create_session(session_id="ses_remove", timestamp=ts)

        database.create_run(
            run_id="run_keep",
            session_id="ses_keep",
            run_type="start_session",
            parameters="{}",
            created_at=ts,
        )
        database.create_run(
            run_id="run_remove",
            session_id="ses_remove",
            run_type="start_session",
            parameters="{}",
            created_at=ts,
        )
        database.insert_event(_make_event("ses_keep", timestamp=ts))
        database.insert_event(_make_event("ses_remove", timestamp=ts))

        database.delete_session("ses_remove")

        # Session B's data is intact
        assert database.get_session_by_id("ses_keep") is not None
        assert database.get_run_by_id("run_keep") is not None
        assert len(database.get_events("ses_keep")) == 1

        # Session A's data is gone
        assert database.get_session_by_id("ses_remove") is None
        assert database.get_run_by_id("run_remove") is None

    def test_delete_nonexistent_session(self, db_path):
        """Deleting a non-existent session returns None."""
        assert database.delete_session("nonexistent") is None
