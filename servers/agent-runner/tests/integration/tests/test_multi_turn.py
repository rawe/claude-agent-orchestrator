"""
Multi-Turn Session Tests

Tests for multi-turn executor sessions where the ClaudeSDKClient stays
alive across multiple turns within a single process.

Run with: uv run --with pytest pytest tests/integration/tests/test_multi_turn.py -v

Markers:
- @pytest.mark.claude: All tests in this file make Claude API calls
"""

import pytest

# Mark all tests as claude tests (make real Claude SDK calls)
pytestmark = pytest.mark.claude


class TestMultiTurnBasic:
    """Basic multi-turn session tests."""

    def test_single_turn_with_shutdown(self, harness, session_id, project_dir):
        """Start a session, get response, shutdown cleanly."""
        executor = harness.create_multi_turn_executor(session_id=session_id)

        try:
            result = executor.start({
                "schema_version": "2.2",
                "mode": "start",
                "session_id": session_id,
                "parameters": {"prompt": "Respond with exactly the word 'hello' and nothing else."},
                "project_dir": project_dir,
                "metadata": {"run_id": "run_single_turn"},
            })

            assert result["type"] == "turn_complete", f"Expected turn_complete, got: {result}"
            assert result["result"], f"Expected non-empty result, got: {result}"
            assert "hello" in result["result"].lower(), f"Expected 'hello' in result: {result['result']}"

            exit_code = executor.shutdown()
            assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {executor.stderr_output[-500:]}"
        except Exception:
            executor.kill()
            raise

    def test_two_turns_context_preserved(self, harness, session_id, project_dir):
        """Second turn can reference first turn content."""
        executor = harness.create_multi_turn_executor(session_id=session_id)

        try:
            # Turn 1: tell it a secret word
            result1 = executor.start({
                "schema_version": "2.2",
                "mode": "start",
                "session_id": session_id,
                "parameters": {"prompt": "Remember: the secret word is 'elephant'. Just say 'acknowledged'."},
                "project_dir": project_dir,
                "metadata": {"run_id": "run_turn1"},
            })

            assert result1["type"] == "turn_complete"
            assert result1["result"], "Turn 1 should return a non-empty result"

            # Turn 2: ask for the secret word
            result2 = executor.send_turn(
                run_id="run_turn2",
                parameters={"prompt": "What was the secret word I told you?"},
            )

            assert result2["type"] == "turn_complete"
            assert "elephant" in result2["result"].lower(), \
                f"Expected 'elephant' in turn 2 result: {result2['result']}"

            exit_code = executor.shutdown()
            assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
        except Exception:
            executor.kill()
            raise

    def test_shutdown_via_eof(self, harness, session_id, project_dir):
        """Process exits cleanly when stdin is closed (EOF instead of shutdown)."""
        executor = harness.create_multi_turn_executor(session_id=session_id)

        try:
            result = executor.start({
                "schema_version": "2.2",
                "mode": "start",
                "session_id": session_id,
                "parameters": {"prompt": "Say 'ready' and nothing else."},
                "project_dir": project_dir,
                "metadata": {"run_id": "run_eof"},
            })

            assert result["type"] == "turn_complete"
            assert result["result"], "Expected non-empty result"

            # Close stdin (EOF) instead of sending shutdown
            exit_code = executor.close_stdin(timeout=15)
            assert exit_code == 0, f"Expected exit code 0 on EOF, got {exit_code}. stderr: {executor.stderr_output[-500:]}"
        except Exception:
            executor.kill()
            raise


class TestMultiTurnEvents:
    """Verify session events are emitted correctly."""

    def test_events_emitted_per_turn(self, harness, session_id, project_dir):
        """Each turn emits user_message, assistant_message, result events."""
        executor = harness.create_multi_turn_executor(session_id=session_id)

        try:
            # Turn 1
            result1 = executor.start({
                "schema_version": "2.2",
                "mode": "start",
                "session_id": session_id,
                "parameters": {"prompt": "Say 'first' and nothing else."},
                "project_dir": project_dir,
                "metadata": {"run_id": "run_events_t1"},
            })
            assert result1["type"] == "turn_complete"

            events_after_turn1 = harness.get_events_for_session(session_id)

            # Should have user message, assistant message, and result events after turn 1
            message_events_t1 = harness.get_message_events(session_id)
            user_messages_t1 = [e for e in message_events_t1 if e.get("role") == "user"]
            assistant_messages_t1 = [e for e in message_events_t1 if e.get("role") == "assistant"]
            result_events_t1 = harness.get_result_events(session_id)

            assert len(user_messages_t1) >= 1, f"Expected at least 1 user message after turn 1, got {len(user_messages_t1)}"
            assert len(assistant_messages_t1) >= 1, f"Expected at least 1 assistant message after turn 1, got {len(assistant_messages_t1)}"
            assert len(result_events_t1) >= 1, f"Expected at least 1 result event after turn 1, got {len(result_events_t1)}"

            # Turn 2
            result2 = executor.send_turn(
                run_id="run_events_t2",
                parameters={"prompt": "Say 'second' and nothing else."},
            )
            assert result2["type"] == "turn_complete"

            # Should have more events after turn 2
            events_after_turn2 = harness.get_events_for_session(session_id)
            assert len(events_after_turn2) > len(events_after_turn1), \
                f"Expected more events after turn 2: {len(events_after_turn1)} -> {len(events_after_turn2)}"

            # Should have additional user and result events for turn 2
            message_events_t2 = harness.get_message_events(session_id)
            user_messages_t2 = [e for e in message_events_t2 if e.get("role") == "user"]
            result_events_t2 = harness.get_result_events(session_id)

            assert len(user_messages_t2) >= 2, f"Expected at least 2 user messages after turn 2, got {len(user_messages_t2)}"
            assert len(result_events_t2) >= 2, f"Expected at least 2 result events after turn 2, got {len(result_events_t2)}"

            exit_code = executor.shutdown()
            assert exit_code == 0
        except Exception:
            executor.kill()
            raise
