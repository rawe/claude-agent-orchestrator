from datetime import datetime, timezone

import database


class TestSessionCRUD:
    def test_create_session(self, db_path):
        """Create a session and verify all fields."""
        ts = datetime.now(timezone.utc).isoformat()
        session = database.create_session(
            session_id="ses_001",
            timestamp=ts,
            status="pending",
            project_dir="/tmp/project",
            agent_name="test-agent",
            parent_session_id=None,
        )
        assert session is not None
        assert session["session_id"] == "ses_001"
        assert session["status"] == "pending"
        assert session["created_at"] == ts
        assert session["project_dir"] == "/tmp/project"
        assert session["agent_name"] == "test-agent"
        assert session["parent_session_id"] is None
        assert session["executor_session_id"] is None
        assert session["executor_profile"] is None
        assert session["hostname"] is None

    def test_create_session_defaults(self, db_path):
        """Create a session with minimal args — defaults to pending, None optionals."""
        ts = datetime.now(timezone.utc).isoformat()
        session = database.create_session(session_id="ses_defaults", timestamp=ts)
        assert session["status"] == "pending"
        assert session["project_dir"] is None
        assert session["agent_name"] is None

    def test_create_session_duplicate_raises(self, db_path):
        """Creating a session with a duplicate ID raises SessionAlreadyExistsError."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_dup", timestamp=ts)
        try:
            database.create_session(session_id="ses_dup", timestamp=ts)
            assert False, "Expected SessionAlreadyExistsError"
        except database.SessionAlreadyExistsError as e:
            assert e.session_id == "ses_dup"

    def test_get_session_by_id(self, db_path):
        """Create then get, verify all fields returned."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(
            session_id="ses_get",
            timestamp=ts,
            agent_name="lookup-agent",
        )
        retrieved = database.get_session_by_id("ses_get")
        assert retrieved is not None
        assert retrieved["session_id"] == "ses_get"
        assert retrieved["agent_name"] == "lookup-agent"
        assert retrieved["created_at"] == ts

    def test_get_session_not_found(self, db_path):
        """Returns None for non-existent session."""
        assert database.get_session_by_id("nonexistent") is None


class TestSessionStateTransitions:
    def test_bind_session_executor(self, db_path):
        """Binding executor transitions pending -> running and sets executor fields."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_bind", timestamp=ts)

        result = database.bind_session_executor(
            session_id="ses_bind",
            executor_session_id="exec-uuid-123",
            hostname="worker-01",
            executor_profile="coding",
            project_dir="/tmp/proj",
        )
        assert result is not None
        assert result["status"] == "running"
        assert result["executor_session_id"] == "exec-uuid-123"
        assert result["hostname"] == "worker-01"
        assert result["executor_profile"] == "coding"
        assert result["project_dir"] == "/tmp/proj"

    def test_bind_session_not_found(self, db_path):
        """Binding a non-existent session returns None."""
        result = database.bind_session_executor(
            session_id="nonexistent",
            executor_session_id="exec-1",
            hostname="h1",
            executor_profile="coding",
        )
        assert result is None

    def test_update_session_status(self, db_path):
        """Verify status can be changed via update_session_status."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_status", timestamp=ts)
        database.update_session_status("ses_status", "running")
        session = database.get_session_by_id("ses_status")
        assert session["status"] == "running"

    def test_session_full_lifecycle(self, db_path):
        """Full path: pending -> running -> finished."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_lifecycle", timestamp=ts)

        session = database.get_session_by_id("ses_lifecycle")
        assert session["status"] == "pending"

        database.bind_session_executor(
            session_id="ses_lifecycle",
            executor_session_id="exec-lc",
            hostname="host-1",
            executor_profile="coding",
        )
        session = database.get_session_by_id("ses_lifecycle")
        assert session["status"] == "running"

        database.update_session_status("ses_lifecycle", "finished")
        session = database.get_session_by_id("ses_lifecycle")
        assert session["status"] == "finished"
