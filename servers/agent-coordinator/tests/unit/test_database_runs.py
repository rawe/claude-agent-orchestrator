import json
from datetime import datetime, timezone

import database


class TestRunCRUD:
    def test_create_run(self, db_path):
        """Creates run in pending state with all fields stored correctly."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_run_01", timestamp=ts)

        params = json.dumps({"prompt": "hello"})
        database.create_run(
            run_id="run_001",
            session_id="ses_run_01",
            run_type="start_session",
            parameters=params,
            created_at=ts,
            agent_name="test-agent",
            project_dir="/tmp/proj",
            execution_mode="sync",
        )

        run = database.get_run_by_id("run_001")
        assert run is not None
        assert run["run_id"] == "run_001"
        assert run["session_id"] == "ses_run_01"
        assert run["type"] == "start_session"
        assert run["parameters"] == params
        assert run["status"] == "pending"
        assert run["runner_id"] is None
        assert run["agent_name"] == "test-agent"
        assert run["execution_mode"] == "sync"

    def test_get_run_by_id(self, db_path):
        """Create then get returns correct run."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_run_02", timestamp=ts)
        database.create_run(
            run_id="run_002",
            session_id="ses_run_02",
            run_type="start_session",
            parameters="{}",
            created_at=ts,
        )

        run = database.get_run_by_id("run_002")
        assert run is not None
        assert run["run_id"] == "run_002"

    def test_get_run_not_found(self, db_path):
        """Returns None for non-existent run."""
        assert database.get_run_by_id("nonexistent") is None


class TestRunClaiming:
    def test_claim_run(self, db_path):
        """Atomic claim changes status to claimed + sets runner_id and claimed_at."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_claim", timestamp=ts)
        database.create_run(
            run_id="run_claim_01",
            session_id="ses_claim",
            run_type="start_session",
            parameters="{}",
            created_at=ts,
        )

        claimed = database.claim_run(
            run_id="run_claim_01",
            runner_id="runner-A",
            claimed_at=ts,
        )
        assert claimed is True

        run = database.get_run_by_id("run_claim_01")
        assert run["status"] == "claimed"
        assert run["runner_id"] == "runner-A"
        assert run["claimed_at"] == ts

    def test_claim_already_claimed_run(self, db_path):
        """Claiming an already-claimed run returns False."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_double_claim", timestamp=ts)
        database.create_run(
            run_id="run_double",
            session_id="ses_double_claim",
            run_type="start_session",
            parameters="{}",
            created_at=ts,
        )

        assert database.claim_run("run_double", "runner-A", ts) is True
        assert database.claim_run("run_double", "runner-B", ts) is False

        # Verify original claim is preserved
        run = database.get_run_by_id("run_double")
        assert run["runner_id"] == "runner-A"

    def test_update_run_status(self, db_path):
        """Verify status transitions work with optional timestamps."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_run_status", timestamp=ts)
        database.create_run(
            run_id="run_status_01",
            session_id="ses_run_status",
            run_type="start_session",
            parameters="{}",
            created_at=ts,
        )

        # Transition to running with started_at
        updated = database.update_run_status(
            run_id="run_status_01",
            status="running",
            started_at=ts,
        )
        assert updated is True
        run = database.get_run_by_id("run_status_01")
        assert run["status"] == "running"
        assert run["started_at"] == ts

        # Transition to completed with completed_at
        completed_ts = datetime.now(timezone.utc).isoformat()
        updated = database.update_run_status(
            run_id="run_status_01",
            status="completed",
            completed_at=completed_ts,
        )
        assert updated is True
        run = database.get_run_by_id("run_status_01")
        assert run["status"] == "completed"
        assert run["completed_at"] == completed_ts

    def test_update_run_status_with_error(self, db_path):
        """Failed runs store error message."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_run_err", timestamp=ts)
        database.create_run(
            run_id="run_err_01",
            session_id="ses_run_err",
            run_type="start_session",
            parameters="{}",
            created_at=ts,
        )

        database.update_run_status(
            run_id="run_err_01",
            status="failed",
            error="Something went wrong",
            completed_at=ts,
        )
        run = database.get_run_by_id("run_err_01")
        assert run["status"] == "failed"
        assert run["error"] == "Something went wrong"
