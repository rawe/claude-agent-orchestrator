"""
Start Mode Tests

Tests for starting new executor sessions with real Claude SDK.
These tests make actual API calls and cost money.

Run with: uv run --with pytest pytest tests/integration/tests/test_start_mode.py -v

Markers:
- @pytest.mark.claude: All tests in this file make Claude API calls
"""

import pytest

# Mark all tests as claude tests (make real Claude SDK calls)
pytestmark = pytest.mark.claude


class TestBasicStart:
    """Basic start mode tests."""

    def test_basic_start_returns_response(self, harness, session_id, project_dir):
        """S01: Basic start with simple prompt returns response."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Respond with exactly the word 'hello' and nothing else."},
            "project_dir": project_dir,
        })

        assert result.success, f"Executor failed: {result.stderr}"
        assert result.exit_code == 0
        # Response should contain 'hello' (case-insensitive)
        assert "hello" in result.stdout.lower(), f"Expected 'hello' in output: {result.stdout}"

    def test_basic_start_binds_session(self, harness, session_id, project_dir):
        """S01: Start mode binds session to gateway."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Say 'test' and nothing else."},
            "project_dir": project_dir,
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Verify bind was called
        bind_calls = harness.get_bind_calls()
        assert len(bind_calls) >= 1, "Expected at least one bind call"

        bind_call = bind_calls[0]
        assert bind_call.body["session_id"] == session_id
        assert bind_call.body.get("executor_session_id"), "executor_session_id should be set"

    def test_basic_start_sends_events(self, harness, session_id, project_dir):
        """S01: Start mode sends message and result events."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Say 'events test' and nothing else."},
            "project_dir": project_dir,
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Check events
        events = harness.get_events_for_session(session_id)
        assert len(events) >= 2, f"Expected at least 2 events, got {len(events)}"

        # Should have user message event
        message_events = harness.get_message_events(session_id)
        user_messages = [e for e in message_events if e.get("role") == "user"]
        assert len(user_messages) >= 1, "Expected user message event"

        # Should have result event
        result_events = harness.get_result_events(session_id)
        assert len(result_events) >= 1, "Expected result event"


class TestStartWithBlueprint:
    """Tests for start with agent blueprint."""

    def test_start_with_system_prompt(self, harness, session_id, project_dir):
        """S02: Start with system prompt affects response."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "What is your name?"},
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "named-agent",
                "system_prompt": "You are an assistant named 'TestBot'. Always introduce yourself by name when asked.",
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"
        # Response should reference the name from system prompt
        assert "testbot" in result.stdout.lower(), f"Expected 'TestBot' in response: {result.stdout}"

    def test_start_with_agent_name_recorded(self, harness, session_id, project_dir):
        """Start with agent_blueprint records agent name."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Say 'ok'."},
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "my-test-agent",
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Session should be created
        session = harness.get_session(session_id)
        assert session is not None


class TestStartWithExecutorConfig:
    """Tests for executor configuration."""

    def test_start_with_permission_mode(self, harness, session_id, project_dir):
        """Start with custom permission mode."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Say 'configured' and nothing else."},
            "project_dir": project_dir,
            "executor_config": {
                "permission_mode": "bypassPermissions",
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"
        assert "configured" in result.stdout.lower()


class TestStartDeterministic:
    """Tests with deterministic prompts for reliable assertions."""

    def test_number_response(self, harness, session_id, project_dir):
        """Request a specific number response."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Respond with exactly the number '42' and nothing else. No words, just the number."},
            "project_dir": project_dir,
        })

        assert result.success, f"Executor failed: {result.stderr}"
        assert "42" in result.stdout, f"Expected '42' in output: {result.stdout}"

    def test_json_response(self, harness, session_id, project_dir):
        """Request a JSON response (without schema validation)."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": 'Return exactly this JSON and nothing else: {"status": "ok"}'
            },
            "project_dir": project_dir,
        })

        assert result.success, f"Executor failed: {result.stderr}"
        assert "status" in result.stdout.lower()
        assert "ok" in result.stdout.lower()


class TestStartTiming:
    """Tests for execution timing."""

    def test_simple_prompt_completes_in_reasonable_time(self, harness, session_id, project_dir):
        """Simple prompt should complete within timeout."""
        result = harness.run_executor(
            {
                "schema_version": "2.2",
                "mode": "start",
                "session_id": session_id,
                "parameters": {"prompt": "Say 'fast'."},
                "project_dir": project_dir,
            },
            timeout=60.0,  # 60 second timeout
        )

        assert result.success, f"Executor failed: {result.stderr}"
        # Should complete in reasonable time (less than 30 seconds for simple prompt)
        assert result.duration_seconds < 30, f"Took too long: {result.duration_seconds}s"
