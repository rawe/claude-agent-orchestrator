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
- agent_blueprint handling
- Unified parameters field (schema 2.2)
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
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Hello world"},
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.schema_version == "2.2"
        assert inv.mode == "start"
        assert inv.session_id == "ses_abc123"
        assert inv.parameters == {"prompt": "Hello world"}
        assert inv.prompt == "Hello world"  # Helper property
        assert inv.agent_blueprint is None
        assert inv.project_dir is None
        assert inv.metadata == {}

    def test_parse_start_with_blueprint(self):
        """Valid start payload with agent_blueprint parses correctly."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Hello world"},
            "project_dir": "/path/to/project",
            "agent_blueprint": {
                "name": "security-auditor",
                "system_prompt": "You are a security auditor.",
                "mcp_servers": {
                    "orchestrator": {
                        "type": "http",
                        "url": "http://127.0.0.1:54321",
                    }
                }
            },
            "metadata": {"key": "value"},
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.schema_version == "2.2"
        assert inv.mode == "start"
        assert inv.session_id == "ses_abc123"
        assert inv.prompt == "Hello world"  # Helper property
        assert inv.agent_blueprint["name"] == "security-auditor"
        assert inv.agent_blueprint["system_prompt"] == "You are a security auditor."
        assert inv.agent_blueprint["mcp_servers"]["orchestrator"]["url"] == "http://127.0.0.1:54321"
        assert inv.project_dir == "/path/to/project"
        assert inv.metadata == {"key": "value"}

    def test_parse_resume_minimal(self):
        """Valid minimal resume payload parses correctly."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Continue please"},
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.schema_version == "2.2"
        assert inv.mode == "resume"
        assert inv.session_id == "ses_abc123"
        assert inv.prompt == "Continue please"  # Helper property
        assert inv.agent_blueprint is None
        assert inv.project_dir is None

    def test_parse_resume_with_blueprint(self):
        """Resume mode with agent_blueprint parses correctly."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Continue"},
            "agent_blueprint": {
                "name": "worker",
                "mcp_servers": {}
            },
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.agent_blueprint["name"] == "worker"

    def test_parse_resume_ignores_project_dir(self):
        """Resume mode logs warning for project_dir."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Continue"},
            "project_dir": "/should/be/ignored",
        })

        with patch("invocation.logger") as mock_logger:
            inv = ExecutorInvocation.from_json(payload)

            # Should warn about ignored field
            mock_logger.warning.assert_called()
            assert "project_dir" in str(mock_logger.warning.call_args)

        # Field is still parsed
        assert inv.project_dir == "/should/be/ignored"

    def test_parse_unicode_prompt(self):
        """Unicode characters in parameters.prompt are handled correctly."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Hello \u4e16\u754c! \U0001F600 \u2764\ufe0f"},  # "Hello 世界! 😀 ❤️"
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.prompt == "Hello 世界! 😀 ❤️"

    def test_parse_long_prompt(self):
        """Long prompts in parameters are handled correctly."""
        long_prompt = "x" * 100000  # 100KB prompt

        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_abc123",
            "parameters": {"prompt": long_prompt},
        })

        inv = ExecutorInvocation.from_json(payload)

        assert len(inv.prompt) == 100000

    def test_parse_missing_schema_version(self):
        """Missing schema_version raises ValueError."""
        payload = json.dumps({
            "mode": "start",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Hello"},
        })

        with pytest.raises(ValueError, match="Missing required field: schema_version"):
            ExecutorInvocation.from_json(payload)

    def test_parse_missing_mode(self):
        """Missing mode raises ValueError."""
        payload = json.dumps({
            "schema_version": "2.2",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Hello"},
        })

        with pytest.raises(ValueError, match="Missing required field: mode"):
            ExecutorInvocation.from_json(payload)

    def test_parse_missing_session_id(self):
        """Missing session_id raises ValueError."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "start",
            "parameters": {"prompt": "Hello"},
        })

        with pytest.raises(ValueError, match="Missing required field: session_id"):
            ExecutorInvocation.from_json(payload)

    def test_parse_missing_parameters(self):
        """Missing parameters raises ValueError."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_abc123",
        })

        with pytest.raises(ValueError, match="Missing required field: parameters"):
            ExecutorInvocation.from_json(payload)

    def test_parse_unsupported_version(self):
        """Unsupported schema version raises ValueError."""
        payload = json.dumps({
            "schema_version": "99.0",
            "mode": "start",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Hello"},
        })

        with pytest.raises(ValueError, match="Unsupported schema version: 99.0"):
            ExecutorInvocation.from_json(payload)

    def test_parse_invalid_mode(self):
        """Invalid mode raises ValueError."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "invalid",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Hello"},
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
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_abc123",
            "parameters": {"prompt": "Hello"},
            "unknown_field": "should be ignored",
            "another_unknown": 123,
        })

        with patch("invocation.logger") as mock_logger:
            inv = ExecutorInvocation.from_json(payload)

            # Should log warnings for unknown fields
            assert mock_logger.warning.call_count >= 2

        # Parsing should succeed
        assert inv.session_id == "ses_abc123"

    def test_parse_non_prompt_parameters(self):
        """Parameters without prompt are handled correctly (deterministic agents)."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_abc123",
            "parameters": {"input_file": "/path/to/file", "options": ["a", "b"]},
        })

        inv = ExecutorInvocation.from_json(payload)

        assert inv.parameters == {"input_file": "/path/to/file", "options": ["a", "b"]}
        assert inv.prompt is None  # No prompt in parameters


class TestFromStdin:
    """Tests for ExecutorInvocation.from_stdin()"""

    def test_from_stdin_reads_input(self):
        """from_stdin reads from sys.stdin."""
        payload = json.dumps({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_stdin_test",
            "parameters": {"prompt": "From stdin"},
        })

        with patch("sys.stdin", StringIO(payload)):
            inv = ExecutorInvocation.from_stdin()

        assert inv.session_id == "ses_stdin_test"
        assert inv.prompt == "From stdin"


class TestSerialization:
    """Tests for serialization methods."""

    def test_to_dict_minimal(self):
        """to_dict returns correct dict for minimal invocation."""
        inv = ExecutorInvocation(
            schema_version="2.2",
            mode="start",
            session_id="ses_test",
            parameters={"prompt": "hello"},
        )

        d = inv.to_dict()

        assert d == {
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_test",
            "parameters": {"prompt": "hello"},
        }

    def test_to_dict_with_blueprint(self):
        """to_dict returns correct dict with agent_blueprint."""
        inv = ExecutorInvocation(
            schema_version="2.2",
            mode="start",
            session_id="ses_test",
            parameters={"prompt": "hello"},
            project_dir="/path",
            agent_blueprint={
                "name": "agent",
                "system_prompt": "You are an agent.",
            },
            metadata={"key": "value"},
        )

        d = inv.to_dict()

        assert d == {
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_test",
            "parameters": {"prompt": "hello"},
            "project_dir": "/path",
            "agent_blueprint": {
                "name": "agent",
                "system_prompt": "You are an agent.",
            },
            "metadata": {"key": "value"},
        }

    def test_to_json(self):
        """to_json returns valid JSON string."""
        inv = ExecutorInvocation(
            schema_version="2.2",
            mode="start",
            session_id="ses_test",
            parameters={"prompt": "hello"},
        )

        json_str = inv.to_json()
        parsed = json.loads(json_str)

        assert parsed["session_id"] == "ses_test"
        assert parsed["parameters"]["prompt"] == "hello"

    def test_roundtrip(self):
        """JSON roundtrip preserves all fields."""
        original = ExecutorInvocation(
            schema_version="2.2",
            mode="start",
            session_id="ses_roundtrip_test",
            parameters={"prompt": "test prompt"},
            project_dir="/test/path",
            agent_blueprint={
                "name": "test-agent",
                "system_prompt": "Test prompt.",
                "mcp_servers": {"srv": {"url": "http://localhost"}},
            },
            metadata={"nested": {"key": "value"}},
        )

        json_str = original.to_json()
        restored = ExecutorInvocation.from_json(json_str)

        assert restored.schema_version == original.schema_version
        assert restored.mode == original.mode
        assert restored.session_id == original.session_id
        assert restored.parameters == original.parameters
        assert restored.prompt == original.prompt  # Helper property
        assert restored.agent_blueprint == original.agent_blueprint
        assert restored.project_dir == original.project_dir
        assert restored.metadata == original.metadata


class TestLogSummary:
    """Tests for log_summary method."""

    def test_log_summary_does_not_include_prompt(self):
        """log_summary logs metadata but not actual prompt content."""
        inv = ExecutorInvocation(
            schema_version="2.2",
            mode="start",
            session_id="ses_secret",
            parameters={"prompt": "This is sensitive prompt content that should not be logged"},
        )

        with patch("invocation.logger") as mock_logger:
            inv.log_summary()

            # Should log
            mock_logger.info.assert_called_once()
            log_message = str(mock_logger.info.call_args)

            # Should include metadata
            assert "2.2" in log_message
            assert "start" in log_message
            assert "ses_secret" in log_message

            # Should NOT include actual prompt content
            assert "sensitive" not in log_message
            assert "should not be logged" not in log_message

            # Should include prompt length
            assert "prompt_len=" in log_message

    def test_log_summary_with_blueprint(self):
        """log_summary includes blueprint name when present."""
        inv = ExecutorInvocation(
            schema_version="2.2",
            mode="start",
            session_id="ses_test",
            parameters={"prompt": "hello"},
            agent_blueprint={"name": "my-agent"},
        )

        with patch("invocation.logger") as mock_logger:
            inv.log_summary()

            log_message = str(mock_logger.info.call_args)
            assert "blueprint=my-agent" in log_message

    def test_log_summary_no_agent(self):
        """log_summary shows no_agent when no blueprint."""
        inv = ExecutorInvocation(
            schema_version="2.2",
            mode="start",
            session_id="ses_test",
            parameters={"prompt": "hello"},
        )

        with patch("invocation.logger") as mock_logger:
            inv.log_summary()

            log_message = str(mock_logger.info.call_args)
            assert "no_agent" in log_message

    def test_log_summary_non_prompt_parameters(self):
        """log_summary shows params_keys for non-prompt parameters."""
        inv = ExecutorInvocation(
            schema_version="2.2",
            mode="start",
            session_id="ses_test",
            parameters={"input_file": "/path", "options": ["a", "b"]},
        )

        with patch("invocation.logger") as mock_logger:
            inv.log_summary()

            log_message = str(mock_logger.info.call_args)
            assert "params_keys=" in log_message


class TestSchema:
    """Tests for schema constants."""

    def test_supported_versions_contains_2_2(self):
        """SUPPORTED_VERSIONS contains '2.2'."""
        assert "2.2" in SUPPORTED_VERSIONS

    def test_schema_version_is_2_2(self):
        """SCHEMA_VERSION is '2.2'."""
        assert SCHEMA_VERSION == "2.2"

    def test_schema_is_valid_json_schema(self):
        """INVOCATION_SCHEMA is a valid JSON Schema structure."""
        assert INVOCATION_SCHEMA["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert INVOCATION_SCHEMA["type"] == "object"
        assert "properties" in INVOCATION_SCHEMA
        assert "required" in INVOCATION_SCHEMA
        assert "agent_blueprint" in INVOCATION_SCHEMA["properties"]
        assert "parameters" in INVOCATION_SCHEMA["properties"]
