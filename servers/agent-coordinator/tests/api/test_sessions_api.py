"""API tests for GET/DELETE /sessions endpoints."""


class TestGetSessions:
    """Tests for GET /sessions — listing sessions."""

    def test_get_sessions_empty(self, coordinator_client):
        """GET /sessions returns empty list when no sessions exist."""
        resp = coordinator_client.get("/sessions")
        assert resp.status_code == 200
        assert resp.json() == {"sessions": []}

    def test_get_sessions_after_run_created(self, coordinator_client):
        """GET /sessions returns session created by POST /runs."""
        # Create a run (which auto-creates a session)
        run_resp = coordinator_client.post("/runs", json={
            "type": "start_session",
            "parameters": {"prompt": "Hello"},
        })
        session_id = run_resp.json()["session_id"]

        resp = coordinator_client.get("/sessions")
        assert resp.status_code == 200
        sessions = resp.json()["sessions"]
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session_id
        assert sessions[0]["status"] == "pending"


class TestGetSessionById:
    """Tests for GET /sessions/{session_id}."""

    def test_get_session_by_id(self, coordinator_client):
        """GET /sessions/{id} returns the session details."""
        run_resp = coordinator_client.post("/runs", json={
            "type": "start_session",
            "parameters": {"prompt": "Hello"},
        })
        session_id = run_resp.json()["session_id"]

        resp = coordinator_client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200
        session = resp.json()["session"]
        assert session["session_id"] == session_id
        assert session["status"] == "pending"

    def test_get_session_not_found(self, coordinator_client):
        """GET /sessions/nonexistent returns 404."""
        resp = coordinator_client.get("/sessions/ses_nonexistent")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Session not found"


class TestDeleteSession:
    """Tests for DELETE /sessions/{session_id}."""

    def test_delete_session(self, coordinator_client):
        """DELETE /sessions/{id} removes a finished session."""
        # Create a session via run
        run_resp = coordinator_client.post("/runs", json={
            "type": "start_session",
            "parameters": {"prompt": "Hello"},
        })
        session_id = run_resp.json()["session_id"]

        # Session is 'pending' — need to move it to a terminal state for deletion
        # Directly update DB status to 'finished' (pending is neither running nor idle,
        # so DELETE should work on pending sessions since the check is for running/idle)
        resp = coordinator_client.delete(f"/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["session_id"] == session_id

        # Verify session is gone
        get_resp = coordinator_client.get(f"/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_session_not_found(self, coordinator_client):
        """DELETE /sessions/nonexistent returns 404."""
        resp = coordinator_client.delete("/sessions/ses_nonexistent")
        assert resp.status_code == 404

    def test_delete_running_session_rejected(self, coordinator_client):
        """DELETE /sessions/{id} on a running session returns 409."""
        import database as db_module

        # Create a session via run
        run_resp = coordinator_client.post("/runs", json={
            "type": "start_session",
            "parameters": {"prompt": "Hello"},
        })
        session_id = run_resp.json()["session_id"]

        # Move to running status
        db_module.update_session_status(session_id, "running")

        resp = coordinator_client.delete(f"/sessions/{session_id}")
        assert resp.status_code == 409
        assert "Stop session first" in resp.json()["detail"]


class TestGetSessionResult:
    """Tests for GET /sessions/{session_id}/result."""

    def test_get_session_result_not_finished(self, coordinator_client):
        """GET /sessions/{id}/result on pending session returns 400."""
        run_resp = coordinator_client.post("/runs", json={
            "type": "start_session",
            "parameters": {"prompt": "Hello"},
        })
        session_id = run_resp.json()["session_id"]

        resp = coordinator_client.get(f"/sessions/{session_id}/result")
        assert resp.status_code == 400
        assert "not finished" in resp.json()["detail"]

    def test_get_session_result_not_found(self, coordinator_client):
        """GET /sessions/{id}/result on nonexistent session returns 404."""
        resp = coordinator_client.get("/sessions/ses_nonexistent/result")
        assert resp.status_code == 404
