from datetime import datetime, timezone

import database


class TestSmoke:
    def test_db_fixture_creates_session(self, db_path):
        """Verify db_path fixture works: init_db + create_session returns data."""
        ts = datetime.now(timezone.utc).isoformat()
        session = database.create_session(
            session_id="ses_test_001",
            timestamp=ts,
            agent_name="test-agent",
        )
        assert session is not None
        # Verify we can retrieve it
        retrieved = database.get_session_by_id("ses_test_001")
        assert retrieved is not None
        assert retrieved["session_id"] == "ses_test_001"
