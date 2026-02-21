"""
Tests for RunnerGateway — local HTTP proxy between executors and coordinator.

Verifies:
- POST /bind enriches requests with hostname and executor_profile
- POST /events forwards to coordinator at correct path
- PATCH /metadata strips session_id from body and forwards
- Other routes (GET, POST) are forwarded as-is
- Missing required fields return 400
"""

import httpx
import pytest

from runner_gateway import RunnerGateway
from fakes.fake_coordinator import FakeCoordinator


@pytest.fixture
def coordinator():
    """Start a FakeCoordinator for the gateway to forward to."""
    fc = FakeCoordinator(poll_timeout=0.3)
    fc.start()
    yield fc
    fc.stop()


@pytest.fixture
def gateway(coordinator):
    """Start a RunnerGateway pointing at the FakeCoordinator."""
    gw = RunnerGateway(
        coordinator_url=coordinator.url,
        hostname="test-host",
        executor_profile="test-profile",
    )
    gw.start()
    yield gw
    gw.stop()


@pytest.fixture
def client(gateway):
    """httpx client pre-configured with the gateway base URL."""
    with httpx.Client(base_url=gateway.url, timeout=5.0) as c:
        yield c


# =========================================================================
# TestBindRoute
# =========================================================================


class TestBindRoute:
    """POST /bind — executor binds to a session, gateway enriches with runner data."""

    def test_bind_enriches_with_hostname_and_profile(self, client, coordinator):
        """Gateway should add hostname and executor_profile to the forwarded request."""
        response = client.post("/bind", json={
            "session_id": "ses_001",
            "executor_session_id": "exec_001",
        })

        assert response.status_code == 200

        bind_calls = coordinator.get_bind_calls()
        assert len(bind_calls) == 1

        call = bind_calls[0]
        assert call["hostname"] == "test-host"
        assert call["executor_profile"] == "test-profile"

    def test_bind_preserves_executor_session_id(self, client, coordinator):
        """executor_session_id from the executor should pass through unchanged."""
        response = client.post("/bind", json={
            "session_id": "ses_002",
            "executor_session_id": "exec_abc",
        })

        assert response.status_code == 200

        bind_calls = coordinator.get_bind_calls()
        assert len(bind_calls) == 1
        assert bind_calls[0]["executor_session_id"] == "exec_abc"

    def test_bind_includes_project_dir(self, client, coordinator):
        """project_dir should be forwarded when provided by executor."""
        response = client.post("/bind", json={
            "session_id": "ses_003",
            "executor_session_id": "exec_003",
            "project_dir": "/home/user/project",
        })

        assert response.status_code == 200

        bind_calls = coordinator.get_bind_calls()
        assert len(bind_calls) == 1
        assert bind_calls[0]["project_dir"] == "/home/user/project"

    def test_bind_missing_session_id_returns_400(self, client, coordinator):
        """400 when session_id is missing from the request body."""
        response = client.post("/bind", json={
            "executor_session_id": "exec_004",
        })

        assert response.status_code == 400
        assert "session_id" in response.json()["detail"].lower()

        # Nothing should be forwarded to coordinator
        assert len(coordinator.get_bind_calls()) == 0

    def test_bind_missing_executor_session_id_returns_400(self, client, coordinator):
        """400 when executor_session_id is missing from the request body."""
        response = client.post("/bind", json={
            "session_id": "ses_005",
        })

        assert response.status_code == 400
        assert "executor_session_id" in response.json()["detail"].lower()

        # Nothing should be forwarded to coordinator
        assert len(coordinator.get_bind_calls()) == 0


# =========================================================================
# TestEventsRoute
# =========================================================================


class TestEventsRoute:
    """POST /events — executor sends events, gateway forwards to coordinator."""

    def test_events_forwarded_to_coordinator(self, client, coordinator):
        """Event should be forwarded to POST /sessions/{session_id}/events."""
        response = client.post("/events", json={
            "session_id": "ses_010",
            "event_type": "tool_use",
            "tool_name": "bash",
        })

        assert response.status_code == 200

        event_calls = coordinator.get_event_calls()
        assert len(event_calls) == 1

        call = event_calls[0]
        assert call["session_id"] == "ses_010"
        assert call["event_type"] == "tool_use"
        assert call["tool_name"] == "bash"

    def test_events_missing_session_id_returns_400(self, client, coordinator):
        """400 when session_id is missing from the event body."""
        response = client.post("/events", json={
            "event_type": "tool_use",
        })

        assert response.status_code == 400
        assert "session_id" in response.json()["detail"].lower()

        # Nothing should be forwarded
        assert len(coordinator.get_event_calls()) == 0


# =========================================================================
# TestMetadataRoute
# =========================================================================


class TestMetadataRoute:
    """PATCH /metadata — executor updates metadata, gateway forwards."""

    def test_metadata_forwarded_to_coordinator(self, client, coordinator):
        """Metadata should be forwarded to PATCH /sessions/{session_id}/metadata
        with session_id stripped from the body."""
        response = client.patch("/metadata", json={
            "session_id": "ses_020",
            "last_resumed_at": "2026-02-21T10:00:00Z",
            "cost_usd": 0.05,
        })

        assert response.status_code == 200

        metadata_calls = coordinator.get_metadata_calls()
        assert len(metadata_calls) == 1

        call = metadata_calls[0]
        # session_id comes from the path (added by FakeCoordinator recording),
        # but should NOT be in the forwarded body payload
        assert call["session_id"] == "ses_020"
        assert call["last_resumed_at"] == "2026-02-21T10:00:00Z"
        assert call["cost_usd"] == 0.05

        # Verify session_id was stripped from the body forwarded to coordinator
        # by checking the raw call body recorded by FakeCoordinator
        raw_calls = coordinator.get_calls()
        patch_calls = [c for c in raw_calls if c.method == "PATCH"]
        assert len(patch_calls) == 1
        assert "session_id" not in patch_calls[0].body

    def test_metadata_missing_session_id_returns_400(self, client, coordinator):
        """400 when session_id is missing from the metadata body."""
        response = client.patch("/metadata", json={
            "last_resumed_at": "2026-02-21T10:00:00Z",
        })

        assert response.status_code == 400
        assert "session_id" in response.json()["detail"].lower()

        # Nothing should be forwarded
        assert len(coordinator.get_metadata_calls()) == 0


# =========================================================================
# TestForwarding
# =========================================================================


class TestForwarding:
    """Non-routed requests should be forwarded to coordinator as-is."""

    def test_get_forwarded_to_coordinator(self, client, coordinator):
        """GET requests should be forwarded as-is to the coordinator."""
        response = client.get("/sessions/ses_030")

        assert response.status_code == 200

        data = response.json()
        assert data["session"]["session_id"] == "ses_030"

        # Verify the call was recorded at the coordinator
        raw_calls = coordinator.get_calls()
        get_calls = [c for c in raw_calls if c.method == "GET"]
        assert len(get_calls) == 1
        assert get_calls[0].path == "/sessions/ses_030"

    def test_post_forwarded_to_coordinator(self, client, coordinator):
        """Non-routed POST requests (not /bind, /events) should be forwarded."""
        response = client.post("/runner/heartbeat", json={
            "runner_id": "lnch_test12345",
            "active_sessions": [],
        })

        assert response.status_code == 200

        # Verify heartbeat was recorded at the coordinator
        heartbeats = coordinator.get_heartbeats()
        assert len(heartbeats) == 1
        assert heartbeats[0]["runner_id"] == "lnch_test12345"
