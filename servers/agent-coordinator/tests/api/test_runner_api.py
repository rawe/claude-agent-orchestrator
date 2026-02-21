"""API tests for runner endpoints (IB-05).

Tests runner registration, polling, and run lifecycle reporting
via POST /runner/register, GET /runner/runs, and POST /runner/runs/{id}/*.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def fresh_runner_services(monkeypatch):
    """Reset runner-related singletons for test isolation.

    The coordinator_client fixture resets run_queue and DB, but runner_registry,
    stop_command_queue, and script_sync_queue are module-level singletons that
    persist across tests. This fixture provides fresh instances for each test.
    """
    import main as coordinator_main
    from services.runner_registry import RunnerRegistry
    from services.stop_command_queue import StopCommandQueue
    from services.script_sync_queue import ScriptSyncQueue

    monkeypatch.setattr(coordinator_main, "runner_registry", RunnerRegistry())
    monkeypatch.setattr(coordinator_main, "stop_command_queue", StopCommandQueue())
    monkeypatch.setattr(coordinator_main, "script_sync_queue", ScriptSyncQueue())

    # Short poll timeout so tests don't hang if no run is available
    monkeypatch.setattr(coordinator_main, "RUNNER_POLL_TIMEOUT", 2)


def _register_runner(client, hostname="test-host", project_dir="/test",
                     executor_profile="default",
                     executor_type="autonomous"):
    """Helper to register a runner and return the response."""
    return client.post("/runner/register", json={
        "hostname": hostname,
        "project_dir": project_dir,
        "executor_profile": executor_profile,
        "executor": {"type": executor_type, "command": "claude"},
    })


def _create_run(client, prompt="Hello"):
    """Helper to create a run. Returns (session_id, run_id)."""
    resp = client.post("/runs", json={
        "type": "start_session",
        "parameters": {"prompt": prompt},
    })
    data = resp.json()
    return data["session_id"], data["run_id"]


class TestRunnerAPI:
    """Tests for runner registration, polling, and status reporting."""

    def test_register_runner(self, coordinator_client):
        """POST /runner/register → 200 with runner_id and poll configuration."""
        resp = _register_runner(coordinator_client)
        assert resp.status_code == 200
        data = resp.json()
        assert data["runner_id"].startswith("lnch_")
        assert data["poll_endpoint"] == "/runner/runs"
        assert "poll_timeout_seconds" in data
        assert "heartbeat_interval_seconds" in data

    def test_register_duplicate_runner_conflict(self, coordinator_client):
        """Second registration with same identity → 409 with duplicate_runner error."""
        resp1 = _register_runner(coordinator_client)
        assert resp1.status_code == 200

        resp2 = _register_runner(coordinator_client)
        assert resp2.status_code == 409
        detail = resp2.json()["detail"]
        assert detail["error"] == "duplicate_runner"
        assert detail["runner_id"] == resp1.json()["runner_id"]

    def test_runner_poll_claims_run(self, coordinator_client):
        """Create run, register runner, poll → returns claimed run."""
        session_id, run_id = _create_run(coordinator_client)

        reg_resp = _register_runner(coordinator_client)
        runner_id = reg_resp.json()["runner_id"]

        poll_resp = coordinator_client.get(
            "/runner/runs", params={"runner_id": runner_id}
        )
        assert poll_resp.status_code == 200
        run_data = poll_resp.json()["run"]
        assert run_data["run_id"] == run_id
        assert run_data["session_id"] == session_id
        assert run_data["status"] == "claimed"

    def test_runner_report_started(self, coordinator_client):
        """POST /runner/runs/{id}/started → 200 ok."""
        _create_run(coordinator_client)
        reg_resp = _register_runner(coordinator_client)
        runner_id = reg_resp.json()["runner_id"]

        poll_resp = coordinator_client.get(
            "/runner/runs", params={"runner_id": runner_id}
        )
        run_id = poll_resp.json()["run"]["run_id"]

        started_resp = coordinator_client.post(
            f"/runner/runs/{run_id}/started",
            json={"runner_id": runner_id},
        )
        assert started_resp.status_code == 200
        assert started_resp.json() == {"ok": True}

    def test_runner_report_completed_finishes_session(self, coordinator_client):
        """Full lifecycle: create → poll → start → complete → session finished."""
        session_id, _ = _create_run(coordinator_client)
        reg_resp = _register_runner(coordinator_client)
        runner_id = reg_resp.json()["runner_id"]

        # Claim
        poll_resp = coordinator_client.get(
            "/runner/runs", params={"runner_id": runner_id}
        )
        run_id = poll_resp.json()["run"]["run_id"]

        # Start
        coordinator_client.post(
            f"/runner/runs/{run_id}/started",
            json={"runner_id": runner_id},
        )

        # Complete
        completed_resp = coordinator_client.post(
            f"/runner/runs/{run_id}/completed",
            json={"runner_id": runner_id},
        )
        assert completed_resp.status_code == 200
        assert completed_resp.json() == {"ok": True}

        # Verify session reached terminal state
        session_resp = coordinator_client.get(f"/sessions/{session_id}")
        assert session_resp.status_code == 200
        assert session_resp.json()["session"]["status"] == "finished"
