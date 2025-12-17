"""
Tests for ExecutorInvocation payload parsing.

Tests cover:
- Valid start/resume payload parsing
- Missing required fields
- Invalid schema version
- Invalid mode
- Empty stdin
- Invalid JSON
- Resume mode ignoring start-only fields
- Unknown fields (forward compatibility)
"""

import json
import pytest
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# Add runner lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from invocation import ExecutorInvocation, SUPPORTED_VERSIONS, INVOCATION_SCHEMA, SCHEMA_VERSION


class TestFromJson:
    """Tests for ExecutorInvocation.from_json()"""

    def test_parse_start_minimal(self):
        """Valid minimal start payload parses correctly."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "start",
            "session_name": "test-session",
            "prompt": "Hello world",
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.schema_version == "1.0"
        assert inv.mode == "start"
        assert inv.session_name == "test-session"
        assert inv.prompt == "Hello world"
        assert inv.agent_name is None
        assert inv.project_dir is None
        assert inv.metadata == {}

    def test_parse_start_full(self):
        """Valid full start payload parses correctly."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "start",
            "session_name": "test-session",
            "prompt": "Hello world",
            "agent_name": "security-auditor",
            "project_dir": "/path/to/project",
            "metadata": {"key": "value"},
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.schema_version == "1.0"
        assert inv.mode == "start"
        assert inv.session_name == "test-session"
        assert inv.prompt == "Hello world"
        assert inv.agent_name == "security-auditor"
        assert inv.project_dir == "/path/to/project"
        assert inv.metadata == {"key": "value"}

    def test_parse_resume_minimal(self):
        """Valid minimal resume payload parses correctly."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "resume",
            "session_name": "test-session",
            "prompt": "Continue please",
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.schema_version == "1.0"
        assert inv.mode == "resume"
        assert inv.session_name == "test-session"
        assert inv.prompt == "Continue please"
        assert inv.agent_name is None
        assert inv.project_dir is None

    def test_parse_resume_ignores_agent_name(self):
        """Resume mode logs warning but parses agent_name (ignored by executor)."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "resume",
            "session_name": "test-session",
            "prompt": "Continue",
            "agent_name": "should-be-ignored",
        })

        with patch("invocation.logger") as mock_logger:
            inv = ExecutorInvocation.from_json(payload)

            # Should warn about ignored field
            mock_logger.warning.assert_called()
            assert "agent_name" in str(mock_logger.warning.call_args)

        # Field is still parsed (executor will ignore it)
        assert inv.agent_name == "should-be-ignored"

    def test_parse_resume_ignores_project_dir(self):
        """Resume mode logs warning but parses project_dir (ignored by executor)."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "resume",
            "session_name": "test-session",
            "prompt": "Continue",
            "project_dir": "/should/be/ignored",
        })

        with patch("invocation.logger") as mock_logger:
            inv = ExecutorInvocation.from_json(payload)

            # Should warn about ignored field
            mock_logger.warning.assert_called()
            assert "project_dir" in str(mock_logger.warning.call_args)

        # Field is still parsed (executor will ignore it)
        assert inv.project_dir == "/should/be/ignored"

    def test_parse_unicode_prompt(self):
        """Unicode characters in prompt are handled correctly."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "start",
            "session_name": "test-session",
            "prompt": "Hello \u4e16\u754c! \U0001F600 \u2764\ufe0f",  # "Hello 世界! 😀 ❤️"
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.prompt == "Hello 世界! 😀 ❤️"

    def test_parse_long_prompt(self):
        """Long prompts are handled correctly."""
        long_prompt = "x" * 100000  # 100KB prompt

        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "start",
            "session_name": "test-session",
            "prompt": long_prompt,
        })

        inv = ExecutorInvocation.from_json(payload)

        assert len(inv.prompt) == 100000

    def test_parse_missing_schema_version(self):
        """Missing schema_version raises ValueError."""
        payload = json.dumps({
            "mode": "start",
            "session_name": "test-session",
            "prompt": "Hello",
        })

        with pytest.raises(ValueError, match="Missing required field: schema_version"):
            ExecutorInvocation.from_json(payload)

    def test_parse_missing_mode(self):
        """Missing mode raises ValueError."""
        payload = json.dumps({
            "schema_version": "1.0",
            "session_name": "test-session",
            "prompt": "Hello",
        })

        with pytest.raises(ValueError, match="Missing required field: mode"):
            ExecutorInvocation.from_json(payload)

    def test_parse_missing_session_name(self):
        """Missing session_name raises ValueError."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "start",
            "prompt": "Hello",
        })

        with pytest.raises(ValueError, match="Missing required field: session_name"):
            ExecutorInvocation.from_json(payload)

    def test_parse_missing_prompt(self):
        """Missing prompt raises ValueError."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "start",
            "session_name": "test-session",
        })

        with pytest.raises(ValueError, match="Missing required field: prompt"):
            ExecutorInvocation.from_json(payload)

    def test_parse_unsupported_version(self):
        """Unsupported schema version raises ValueError."""
        payload = json.dumps({
            "schema_version": "99.0",
            "mode": "start",
            "session_name": "test-session",
            "prompt": "Hello",
        })

        with pytest.raises(ValueError, match="Unsupported schema version: 99.0"):
            ExecutorInvocation.from_json(payload)

    def test_parse_invalid_mode(self):
        """Invalid mode raises ValueError."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "invalid",
            "session_name": "test-session",
            "prompt": "Hello",
        })

        with pytest.raises(ValueError, match="Invalid mode: invalid"):
            ExecutorInvocation.from_json(payload)

    def test_parse_empty_input(self):
        """Empty input raises ValueError."""
        with pytest.raises(ValueError, match="No input received on stdin"):
            ExecutorInvocation.from_json("")

    def test_parse_whitespace_only(self):
        """Whitespace-only input raises ValueError."""
        with pytest.raises(ValueError, match="No input received on stdin"):
            ExecutorInvocation.from_json("   \n\t  ")

    def test_parse_invalid_json(self):
        """Invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            ExecutorInvocation.from_json("not json {")

    def test_parse_unknown_fields_ignored(self):
        """Unknown fields are logged as warning but parsing succeeds."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "start",
            "session_name": "test-session",
            "prompt": "Hello",
            "unknown_field": "should be ignored",
            "another_unknown": 123,
        })

        with patch("invocation.logger") as mock_logger:
            inv = ExecutorInvocation.from_json(payload)

            # Should log warnings for unknown fields
            assert mock_logger.warning.call_count >= 2

        # Parsing should succeed
        assert inv.session_name == "test-session"


class TestFromStdin:
    """Tests for ExecutorInvocation.from_stdin()"""

    def test_from_stdin_reads_input(self):
        """from_stdin reads from sys.stdin."""
        payload = json.dumps({
            "schema_version": "1.0",
            "mode": "start",
            "session_name": "stdin-test",
            "prompt": "From stdin",
        })

        with patch("sys.stdin", StringIO(payload)):
            inv = ExecutorInvocation.from_stdin()

        assert inv.session_name == "stdin-test"
        assert inv.prompt == "From stdin"


class TestSerialization:
    """Tests for serialization methods."""

    def test_to_dict_minimal(self):
        """to_dict returns correct dict for minimal invocation."""
        inv = ExecutorInvocation(
            schema_version="1.0",
            mode="start",
            session_name="test",
            prompt="hello",
        )

        d = inv.to_dict()

        assert d == {
            "schema_version": "1.0",
            "mode": "start",
            "session_name": "test",
            "prompt": "hello",
        }

    def test_to_dict_full(self):
        """to_dict returns correct dict for full invocation."""
        inv = ExecutorInvocation(
            schema_version="1.0",
            mode="start",
            session_name="test",
            prompt="hello",
            agent_name="agent",
            project_dir="/path",
            metadata={"key": "value"},
        )

        d = inv.to_dict()

        assert d == {
            "schema_version": "1.0",
            "mode": "start",
            "session_name": "test",
            "prompt": "hello",
            "agent_name": "agent",
            "project_dir": "/path",
            "metadata": {"key": "value"},
        }

    def test_to_json(self):
        """to_json returns valid JSON string."""
        inv = ExecutorInvocation(
            schema_version="1.0",
            mode="start",
            session_name="test",
            prompt="hello",
        )

        json_str = inv.to_json()
        parsed = json.loads(json_str)

        assert parsed["session_name"] == "test"

    def test_roundtrip(self):
        """JSON roundtrip preserves all fields."""
        original = ExecutorInvocation(
            schema_version="1.0",
            mode="start",
            session_name="roundtrip-test",
            prompt="test prompt",
            agent_name="test-agent",
            project_dir="/test/path",
            metadata={"nested": {"key": "value"}},
        )

        json_str = original.to_json()
        restored = ExecutorInvocation.from_json(json_str)

        assert restored.schema_version == original.schema_version
        assert restored.mode == original.mode
        assert restored.session_name == original.session_name
        assert restored.prompt == original.prompt
        assert restored.agent_name == original.agent_name
        assert restored.project_dir == original.project_dir
        assert restored.metadata == original.metadata


class TestLogSummary:
    """Tests for log_summary method."""

    def test_log_summary_does_not_include_prompt(self):
        """log_summary logs metadata but not actual prompt content."""
        inv = ExecutorInvocation(
            schema_version="1.0",
            mode="start",
            session_name="secret-session",
            prompt="This is sensitive prompt content that should not be logged",
        )

        with patch("invocation.logger") as mock_logger:
            inv.log_summary()

            # Should log
            mock_logger.info.assert_called_once()
            log_message = str(mock_logger.info.call_args)

            # Should include metadata
            assert "1.0" in log_message
            assert "start" in log_message
            assert "secret-session" in log_message

            # Should NOT include actual prompt content
            assert "sensitive" not in log_message
            assert "should not be logged" not in log_message

            # Should include prompt length
            assert "prompt_len=" in log_message


class TestSchema:
    """Tests for schema constants."""

    def test_supported_versions_contains_1_0(self):
        """SUPPORTED_VERSIONS contains '1.0'."""
        assert "1.0" in SUPPORTED_VERSIONS

    def test_schema_is_valid_json_schema(self):
        """INVOCATION_SCHEMA is a valid JSON Schema structure."""
        assert INVOCATION_SCHEMA["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert INVOCATION_SCHEMA["type"] == "object"
        assert "properties" in INVOCATION_SCHEMA
        assert "required" in INVOCATION_SCHEMA
