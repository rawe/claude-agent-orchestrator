"""API tests for POST /runs endpoint."""


class TestPostRuns:
    """Tests for POST /runs — creating new runs."""

    def test_post_runs_creates_pending_session(self, coordinator_client):
        """POST /runs with start_session creates a session with ses_ prefix."""
        resp = coordinator_client.post("/runs", json={
            "type": "start_session",
            "parameters": {"prompt": "Hello"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"].startswith("ses_")
        assert data["status"] == "pending"

    def test_post_runs_returns_run_id(self, coordinator_client):
        """POST /runs response includes a run_id with run_ prefix."""
        resp = coordinator_client.post("/runs", json={
            "type": "start_session",
            "parameters": {"prompt": "Hello"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "run_id" in data
        assert data["run_id"].startswith("run_")

    def test_post_runs_with_agent_name(self, coordinator_client):
        """POST /runs with agent_name stores it on the session."""
        # First create an agent so the agent lookup succeeds
        coordinator_client.post("/agents", json={
            "name": "test-agent",
            "description": "A test agent",
            "type": "autonomous",
        })

        resp = coordinator_client.post("/runs", json={
            "type": "start_session",
            "agent_name": "test-agent",
            "parameters": {"prompt": "Do something"},
        })
        assert resp.status_code == 201
        data = resp.json()
        session_id = data["session_id"]

        # Verify the session has the agent_name
        session_resp = coordinator_client.get(f"/sessions/{session_id}")
        assert session_resp.status_code == 200
        assert session_resp.json()["session"]["agent_name"] == "test-agent"

    def test_post_runs_missing_parameters(self, coordinator_client):
        """POST /runs without required 'parameters' field returns 422."""
        resp = coordinator_client.post("/runs", json={
            "type": "start_session",
        })
        assert resp.status_code == 422

    def test_post_runs_invalid_type(self, coordinator_client):
        """POST /runs with invalid type returns 422."""
        resp = coordinator_client.post("/runs", json={
            "type": "invalid_type",
            "parameters": {"prompt": "Hello"},
        })
        assert resp.status_code == 422

    def test_post_runs_resume_requires_session_id(self, coordinator_client):
        """POST /runs with resume_session but no session_id returns 400."""
        resp = coordinator_client.post("/runs", json={
            "type": "resume_session",
            "parameters": {"prompt": "Continue"},
        })
        assert resp.status_code == 400
        assert "session_id is required" in resp.json()["detail"]

    def test_post_runs_resume_nonexistent_session(self, coordinator_client):
        """POST /runs with resume_session for nonexistent session returns 404."""
        resp = coordinator_client.post("/runs", json={
            "type": "resume_session",
            "session_id": "ses_nonexistent",
            "parameters": {"prompt": "Continue"},
        })
        assert resp.status_code == 404
