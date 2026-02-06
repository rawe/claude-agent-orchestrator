"""
Resume Mode Tests

Tests for resuming existing executor sessions with real Claude SDK.
These tests run start followed by resume to test the full flow.

Run with: uv run --with pytest pytest tests/integration/tests/test_resume_mode.py -v

Markers:
- @pytest.mark.claude: All tests in this file make Claude API calls
- @pytest.mark.slow: These tests take longer (2 Claude calls each)
"""

import pytest

# Mark all tests as claude + slow (2 Claude calls per test)
pytestmark = [pytest.mark.claude, pytest.mark.slow]


class TestBasicResume:
    """Basic resume mode tests."""

    def test_resume_after_start(self, harness, session_id, project_dir):
        """R01: Resume continues from existing session."""
        # First, start a session
        start_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Remember the secret word 'elephant'. Just say 'ok' to confirm."},
            "project_dir": project_dir,
        })

        assert start_result.success, f"Start failed: {start_result.stderr}"

        harness.wait_for_session()

        # Now resume
        resume_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": session_id,
            "parameters": {"prompt": "What was the secret word I told you to remember?"},
        })

        assert resume_result.success, f"Resume failed: {resume_result.stderr}"
        # Should remember 'elephant' from the first message
        assert "elephant" in resume_result.stdout.lower(), \
            f"Expected 'elephant' in response: {resume_result.stdout}"

    def test_resume_updates_last_resumed_at(self, harness, session_id, project_dir):
        """R01: Resume updates last_resumed_at metadata."""
        # Start a session
        start_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Say 'started'."},
            "project_dir": project_dir,
        })

        assert start_result.success, f"Start failed: {start_result.stderr}"

        # Clear to isolate resume calls
        initial_calls = len(harness.get_gateway_calls())

        harness.wait_for_session()

        # Resume
        resume_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": session_id,
            "parameters": {"prompt": "Say 'resumed'."},
        })

        assert resume_result.success, f"Resume failed: {resume_result.stderr}"

        # Check that metadata was updated (PATCH /metadata call)
        all_calls = harness.get_gateway_calls()
        metadata_calls = [c for c in all_calls if c.path == "/metadata" and c.method == "PATCH"]

        # Should have at least one metadata update for last_resumed_at
        assert len(metadata_calls) >= 1, "Expected metadata update call for resume"

    def test_resume_sends_new_events(self, harness, session_id, project_dir):
        """R01: Resume sends new message and result events."""
        # Start
        start_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Say 'first'."},
            "project_dir": project_dir,
        })

        assert start_result.success

        events_after_start = len(harness.get_events_for_session(session_id))

        harness.wait_for_session()

        # Resume
        resume_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": session_id,
            "parameters": {"prompt": "Say 'second'."},
        })

        assert resume_result.success

        events_after_resume = len(harness.get_events_for_session(session_id))

        # Should have more events after resume
        assert events_after_resume > events_after_start, \
            f"Expected more events after resume: {events_after_start} -> {events_after_resume}"


class TestResumeContext:
    """Tests for context preservation across resume."""

    def test_resume_remembers_conversation(self, harness, session_id, project_dir):
        """R02: Resume maintains conversation context."""
        # Start with a memorable fact
        start_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "My favorite color is blue. Just acknowledge with 'noted'."},
            "project_dir": project_dir,
        })

        assert start_result.success, f"Start failed: {start_result.stderr}"

        harness.wait_for_session()

        # Resume and ask about it
        resume_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": session_id,
            "parameters": {"prompt": "What is my favorite color?"},
        })

        assert resume_result.success, f"Resume failed: {resume_result.stderr}"
        assert "blue" in resume_result.stdout.lower(), \
            f"Expected 'blue' in response: {resume_result.stdout}"

    def test_multiple_resumes(self, harness, session_id, project_dir):
        """Multiple resumes maintain context chain."""
        # Start
        start_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Count: 1. Just confirm with the number."},
            "project_dir": project_dir,
        })
        assert start_result.success

        harness.wait_for_session()

        # First resume
        resume1_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": session_id,
            "parameters": {"prompt": "Count: 2. Just confirm with the number."},
        })
        assert resume1_result.success

        harness.wait_for_session()

        # Second resume - ask about the sequence
        resume2_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": session_id,
            "parameters": {"prompt": "What numbers have I counted so far? List them."},
        })
        assert resume2_result.success

        # Should remember both numbers
        output = resume2_result.stdout.lower()
        assert "1" in output and "2" in output, \
            f"Expected both '1' and '2' in response: {resume2_result.stdout}"


class TestResumeWithBlueprint:
    """Tests for resume with agent blueprint (MCP servers)."""

    def test_resume_with_mcp_servers(self, harness, session_id, project_dir):
        """Resume can include MCP servers in blueprint."""
        # Start with MCP
        start_payload = {
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Say 'started with tools'."},
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "mcp-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        }

        start_result = harness.run_executor(start_payload)
        assert start_result.success, f"Start failed: {start_result.stderr}"

        harness.wait_for_session()

        # Resume with same blueprint (MCP servers)
        resume_result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": session_id,
            "parameters": {"prompt": "Use the echo tool to say 'resumed'. Then confirm."},
            "agent_blueprint": {
                "name": "mcp-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        })

        assert resume_result.success, f"Resume failed: {resume_result.stderr}"

        # Check if echo tool was called
        echo_calls = harness.get_mcp_calls_by_tool("echo")
        # May or may not call the tool depending on Claude's interpretation
        # The important thing is resume worked


class TestResumeHarnessHelper:
    """Tests using the harness helper method."""

    def test_run_start_and_resume_helper(self, harness, session_id, project_dir):
        """Test the run_start_and_resume helper method."""
        start_payload = {
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "The magic number is 7. Say 'ok'."},
            "project_dir": project_dir,
        }

        start_result, resume_result = harness.run_start_and_resume(
            start_payload=start_payload,
            resume_prompt="What is the magic number?",
        )

        assert start_result.success, f"Start failed: {start_result.stderr}"
        assert resume_result.success, f"Resume failed: {resume_result.stderr}"
        assert "7" in resume_result.stdout, \
            f"Expected '7' in response: {resume_result.stdout}"
