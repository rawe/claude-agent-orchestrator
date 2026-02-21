"""
Tests for CoordinatorAPIClient - typed HTTP client to coordinator.

Tests use FakeCoordinator to verify:
- Registration (success, duplicate runner 409, agent collision 409)
- Poll for runs (run response, 204 no content, deregistration, stop commands)
- Status reports (started, completed, failed, stopped)
- Heartbeat
- Deregistration
- Session status reporting
"""

import pytest
from api_client import (
    CoordinatorAPIClient,
    DuplicateRunnerError,
    AgentNameCollisionError,
    AuthenticationError,
    RegistrationResponse,
    PollResult,
    Run,
)
from fakes.fake_coordinator import FakeCoordinator


@pytest.fixture
def coordinator():
    """FakeCoordinator for API client tests."""
    fc = FakeCoordinator(poll_timeout=0.3)
    fc.start()
    yield fc
    fc.stop()


@pytest.fixture
def client(coordinator):
    """CoordinatorAPIClient connected to FakeCoordinator."""
    c = CoordinatorAPIClient(coordinator.url, timeout=5.0)
    yield c
    c.close()


class TestRegistration:
    """Test runner registration."""

    def test_register_success(self, coordinator, client):
        coordinator.configure_registration(
            runner_id="lnch_abc123",
            poll_timeout_seconds=30,
            heartbeat_interval_seconds=60,
        )

        result = client.register(
            hostname="test-host",
            project_dir="/workspace",
            executor_profile="echo",
            executor={"type": "echo", "command": "ao-echo-exec"},
        )

        assert isinstance(result, RegistrationResponse)
        assert result.runner_id == "lnch_abc123"
        assert result.poll_timeout_seconds == 30
        assert result.heartbeat_interval_seconds == 60
        assert "/runner/runs" in result.poll_endpoint

        # Verify registration was recorded
        runners = coordinator.get_registered_runners()
        assert "lnch_abc123" in runners
        assert runners["lnch_abc123"]["hostname"] == "test-host"

    def test_register_with_tags(self, coordinator, client):
        result = client.register(
            hostname="test-host",
            project_dir="/workspace",
            executor_profile="echo",
            executor={"type": "echo"},
            tags=["gpu", "large-context"],
        )

        runners = coordinator.get_registered_runners()
        data = list(runners.values())[0]
        assert data["tags"] == ["gpu", "large-context"]

    def test_register_duplicate_runner_409(self, coordinator, client):
        coordinator.set_register_error(409, {
            "detail": {
                "error": "duplicate_runner",
                "runner_id": "lnch_existing",
                "hostname": "test-host",
                "project_dir": "/workspace",
                "executor_profile": "echo",
                "message": "A runner with this identity is already online",
            }
        })

        with pytest.raises(DuplicateRunnerError) as exc_info:
            client.register(
                hostname="test-host",
                project_dir="/workspace",
                executor_profile="echo",
                executor={"type": "echo"},
            )
        assert exc_info.value.runner_id == "lnch_existing"

    def test_register_agent_name_collision_409(self, coordinator, client):
        coordinator.set_register_error(409, {
            "detail": {
                "error": "agent_name_collision",
                "agent_name": "my-agent",
                "existing_runner_id": "lnch_other",
                "message": "Agent name already registered by another runner",
            }
        })

        with pytest.raises(AgentNameCollisionError) as exc_info:
            client.register(
                hostname="test-host",
                project_dir="/workspace",
                executor_profile="echo",
                executor={"type": "echo"},
            )
        assert exc_info.value.agent_name == "my-agent"
        assert exc_info.value.existing_runner_id == "lnch_other"


class TestPollRun:
    """Test polling for runs."""

    def test_poll_returns_run(self, coordinator, client):
        coordinator.enqueue_run({
            "run": {
                "run_id": "run_001",
                "type": "start_session",
                "session_id": "ses_001",
                "parameters": {"prompt": "hello world"},
                "agent_name": "test-agent",
                "project_dir": "/workspace",
            }
        })

        result = client.poll_run("lnch_test")
        assert isinstance(result, PollResult)
        assert result.run is not None
        assert result.run.run_id == "run_001"
        assert result.run.type == "start_session"
        assert result.run.session_id == "ses_001"
        assert result.run.parameters == {"prompt": "hello world"}
        assert result.run.agent_name == "test-agent"
        assert result.run.project_dir == "/workspace"
        assert result.run.prompt == "hello world"

    def test_poll_returns_resume_run(self, coordinator, client):
        coordinator.enqueue_run({
            "run": {
                "run_id": "run_002",
                "type": "resume_session",
                "session_id": "ses_001",
                "parameters": {"prompt": "continue"},
            }
        })

        result = client.poll_run("lnch_test")
        assert result.run.type == "resume_session"
        assert result.run.run_id == "run_002"

    def test_poll_no_runs_returns_empty(self, coordinator, client):
        result = client.poll_run("lnch_test")
        assert result.run is None
        assert result.deregistered is False
        assert result.stop_sessions == []

    def test_poll_deregistration(self, coordinator, client):
        coordinator.enqueue_deregistered()

        result = client.poll_run("lnch_test")
        assert result.deregistered is True
        assert result.run is None

    def test_poll_stop_sessions(self, coordinator, client):
        coordinator.enqueue_stop_sessions(["ses_001", "ses_002"])

        result = client.poll_run("lnch_test")
        assert result.stop_sessions == ["ses_001", "ses_002"]
        assert result.run is None

    def test_poll_with_resolved_blueprint(self, coordinator, client):
        coordinator.enqueue_run({
            "run": {
                "run_id": "run_003",
                "type": "start_session",
                "session_id": "ses_003",
                "parameters": {"prompt": "test"},
                "resolved_agent_blueprint": {
                    "name": "my-agent",
                    "system_prompt": "You are helpful",
                },
                "scope": {"api_key": "secret123"},
            }
        })

        result = client.poll_run("lnch_test")
        assert result.run.resolved_agent_blueprint["name"] == "my-agent"
        assert result.run.scope["api_key"] == "secret123"

    def test_poll_script_sync(self, coordinator, client):
        coordinator.enqueue_script_sync(
            sync=["script-a", "script-b"],
            remove=["old-script"],
        )

        result = client.poll_run("lnch_test")
        assert result.sync_scripts == ["script-a", "script-b"]
        assert result.remove_scripts == ["old-script"]
        assert result.run is None


class TestStatusReports:
    """Test run status reporting."""

    def test_report_started(self, coordinator, client):
        client.report_started("lnch_test", "run_001")

        reports = coordinator.get_run_reports("run_001")
        assert len(reports) == 1
        assert reports[0].type == "started"
        assert reports[0].runner_id == "lnch_test"

    def test_report_completed_oneshot(self, coordinator, client):
        client.report_completed("lnch_test", "run_001", session_status="finished")

        reports = coordinator.get_run_reports("run_001")
        assert len(reports) == 1
        assert reports[0].type == "completed"
        assert reports[0].data["session_status"] == "finished"
        assert coordinator.get_final_status("run_001") == "completed"

    def test_report_completed_persistent(self, coordinator, client):
        client.report_completed("lnch_test", "run_001", session_status="idle")

        reports = coordinator.get_run_reports("run_001")
        assert reports[0].data["session_status"] == "idle"

    def test_report_failed(self, coordinator, client):
        client.report_failed("lnch_test", "run_001", "Process crashed with exit code 1")

        reports = coordinator.get_run_reports("run_001")
        assert len(reports) == 1
        assert reports[0].type == "failed"
        assert reports[0].data["error"] == "Process crashed with exit code 1"
        assert coordinator.get_final_status("run_001") == "failed"

    def test_report_stopped(self, coordinator, client):
        client.report_stopped("lnch_test", "run_001", signal="SIGTERM")

        reports = coordinator.get_run_reports("run_001")
        assert len(reports) == 1
        assert reports[0].type == "stopped"
        assert reports[0].data["signal"] == "SIGTERM"
        assert coordinator.get_final_status("run_001") == "stopped"

    def test_full_lifecycle(self, coordinator, client):
        """Verify start→complete lifecycle is tracked."""
        client.report_started("lnch_test", "run_001")
        client.report_completed("lnch_test", "run_001", session_status="finished")

        reports = coordinator.get_run_reports("run_001")
        assert len(reports) == 2
        assert reports[0].type == "started"
        assert reports[1].type == "completed"


class TestSessionStatus:
    """Test session status reporting (idle process exit)."""

    def test_report_session_status(self, coordinator, client):
        client.report_session_status("lnch_test", "ses_001", "finished")

        statuses = coordinator.get_session_statuses("ses_001")
        assert len(statuses) == 1
        assert statuses[0]["status"] == "finished"
        assert statuses[0]["runner_id"] == "lnch_test"


class TestHeartbeat:
    """Test heartbeat calls."""

    def test_heartbeat(self, coordinator, client):
        client.heartbeat("lnch_test")

        heartbeats = coordinator.get_heartbeats()
        assert len(heartbeats) == 1
        assert heartbeats[0]["runner_id"] == "lnch_test"

    def test_multiple_heartbeats(self, coordinator, client):
        for _ in range(3):
            client.heartbeat("lnch_test")

        assert len(coordinator.get_heartbeats()) == 3


class TestDeregister:
    """Test self-deregistration."""

    def test_deregister(self, coordinator, client):
        # First register
        client.register(
            hostname="test-host",
            project_dir="/workspace",
            executor_profile="echo",
            executor={"type": "echo"},
        )

        runner_id = coordinator._runner_id
        assert runner_id in coordinator.get_registered_runners()

        # Then deregister
        client.deregister(runner_id)

        # Verify runner removed
        assert runner_id not in coordinator.get_registered_runners()

        # Verify DELETE call was made with ?self=true
        delete_calls = coordinator.get_calls_by_path(f"/runners/{runner_id}")
        assert len(delete_calls) == 1
        assert delete_calls[0].method == "DELETE"
        assert delete_calls[0].query["self"] == "true"
