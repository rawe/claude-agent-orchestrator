"""
Tests for RunExecutor with JSON payload.

Tests cover:
- Payload building for start/resume modes
- JSON structure correctness
- Schema version inclusion
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add runner lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from executor import RunExecutor
from invocation import SCHEMA_VERSION
from api_client import Run


class TestBuildPayload:
    """Tests for RunExecutor._build_payload()"""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with mocked executor path."""
        fake_exec = tmp_path / "test-exec"
        fake_exec.write_text("#!/bin/bash\necho test")
        fake_exec.chmod(0o755)
        with patch("executor.get_runner_dir", return_value=tmp_path):
            return RunExecutor(default_project_dir="/default/path")

    def test_start_payload_minimal(self, executor):
        """Start payload includes required fields."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name=None,
            parameters={"prompt": "Hello world"},
            project_dir=None,
        )

        payload = executor._build_payload(run, "start")

        assert payload["schema_version"] == SCHEMA_VERSION
        assert payload["mode"] == "start"
        assert payload["session_id"] == "ses_test123"
        assert payload["parameters"]["prompt"] == "Hello world"
        # Uses default project_dir
        assert payload["project_dir"] == "/default/path"
        # No agent_name when not specified
        assert "agent_name" not in payload

    def test_start_payload_with_agent(self, executor):
        """Start payload includes agent_name when specified."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name="security-auditor",
            parameters={"prompt": "Hello world"},
            project_dir="/custom/path",
        )

        payload = executor._build_payload(run, "start")

        assert payload["agent_name"] == "security-auditor"
        assert payload["project_dir"] == "/custom/path"

    def test_resume_payload_minimal(self, executor):
        """Resume payload includes only required fields."""
        run = Run(
            run_id="run-1",
            type="resume_session",
            session_id="ses_test123",
            agent_name="should-be-ignored",
            parameters={"prompt": "Continue please"},
            project_dir="/should/be/ignored",
        )

        payload = executor._build_payload(run, "resume")

        assert payload["schema_version"] == SCHEMA_VERSION
        assert payload["mode"] == "resume"
        assert payload["session_id"] == "ses_test123"
        assert payload["parameters"]["prompt"] == "Continue please"
        # Resume DOES include agent_name now (for procedural agents)
        # but NOT project_dir
        assert "project_dir" not in payload

    def test_payload_is_valid_json(self, executor):
        """Payload can be serialized to valid JSON."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name="agent",
            parameters={"prompt": "Hello 世界! 😀"},
            project_dir="/path",
        )

        payload = executor._build_payload(run, "start")
        json_str = json.dumps(payload)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["parameters"]["prompt"] == "Hello 世界! 😀"


class TestExecuteWithPayload:
    """Tests for RunExecutor._execute_with_payload()"""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with mocked executor path."""
        # Create fake executor at the default path
        exec_dir = tmp_path / "executors" / "claude-code"
        exec_dir.mkdir(parents=True)
        fake_exec = exec_dir / "ao-claude-code-exec"
        fake_exec.write_text("#!/bin/bash\necho test")
        fake_exec.chmod(0o755)

        with patch("executor.get_runner_dir", return_value=tmp_path):
            return RunExecutor(default_project_dir="/default/path")

    def test_execute_calls_executor(self, executor):
        """Execute calls executor subprocess."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name=None,
            parameters={"prompt": "Hello"},
            project_dir=None,
        )

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_popen.return_value = mock_process

            executor._execute_with_payload(run, "start")

            # Should call Popen with executor (via 'uv run --script <executor>')
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args
            cmd = call_args[0][0]
            # The command is now ["uv", "run", "--script", <executor_path>]
            assert cmd[0] == "uv"
            assert cmd[1] == "run"
            assert cmd[2] == "--script"
            assert "ao-claude-code-exec" in cmd[3]

    def test_execute_writes_json_to_stdin(self, executor):
        """Execute writes JSON payload to subprocess stdin."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name=None,
            parameters={"prompt": "Hello"},
            project_dir=None,
        )

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_popen.return_value = mock_process

            executor._execute_with_payload(run, "start")

            # Should write to stdin
            mock_process.stdin.write.assert_called_once()
            written = mock_process.stdin.write.call_args[0][0]

            # Should be valid JSON
            payload = json.loads(written)
            assert payload["schema_version"] == SCHEMA_VERSION
            assert payload["session_id"] == "ses_test123"

            # Should close stdin
            mock_process.stdin.close.assert_called_once()

    def test_execute_sets_agent_session_id_env(self, executor):
        """Execute sets AGENT_SESSION_ID environment variable."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_my123456",
            agent_name=None,
            parameters={"prompt": "Hello"},
            project_dir=None,
        )

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_popen.return_value = mock_process

            executor._execute_with_payload(run, "start")

            # Check env passed to Popen
            call_kwargs = mock_popen.call_args[1]
            env = call_kwargs["env"]
            assert env["AGENT_SESSION_ID"] == "ses_my123456"


class TestExecute:
    """Tests for RunExecutor.execute_run()"""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with mocked executor path."""
        fake_exec = tmp_path / "test-exec"
        fake_exec.write_text("#!/bin/bash\necho test")
        fake_exec.chmod(0o755)

        with patch("executor.get_runner_dir", return_value=tmp_path):
            return RunExecutor(default_project_dir="/default/path")

    def test_execute_start_session(self, executor):
        """execute_run routes start_session to mode='start'."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_testid1",
            agent_name=None,
            parameters={"prompt": "Hello"},
            project_dir=None,
        )

        with patch.object(executor, "_execute_with_payload") as mock_exec:
            mock_exec.return_value = MagicMock()
            executor.execute_run(run)
            mock_exec.assert_called_once_with(run, "start")

    def test_execute_resume_session(self, executor):
        """execute_run routes resume_session to mode='resume'."""
        run = Run(
            run_id="run-1",
            type="resume_session",
            session_id="ses_testid1",
            agent_name=None,
            parameters={"prompt": "Hello"},
            project_dir=None,
        )

        with patch.object(executor, "_execute_with_payload") as mock_exec:
            mock_exec.return_value = MagicMock()
            executor.execute_run(run)
            mock_exec.assert_called_once_with(run, "resume")

    def test_execute_unknown_type_raises(self, executor):
        """execute_run raises ValueError for unknown agent run type."""
        run = Run(
            run_id="run-1",
            type="unknown_type",
            session_id="ses_testid1",
            agent_name=None,
            parameters={"prompt": "Hello"},
            project_dir=None,
        )

        with pytest.raises(ValueError, match="Unknown agent run type: unknown_type"):
            executor.execute_run(run)


class TestResolvedAgentBlueprint:
    """Tests for resolved_agent_blueprint from run payload (mcp-resolution-at-coordinator.md)."""

    @pytest.fixture
    def executor_with_mcp_url(self, tmp_path):
        """Create executor with mocked executor path and MCP server URL."""
        fake_exec = tmp_path / "test-exec"
        fake_exec.write_text("#!/bin/bash\necho test")
        fake_exec.chmod(0o755)
        with patch("executor.get_runner_dir", return_value=tmp_path):
            return RunExecutor(
                default_project_dir="/default/path",
                mcp_server_url="http://localhost:9999/mcp",
            )

    def test_uses_resolved_blueprint_from_run(self, executor_with_mcp_url):
        """Uses resolved_agent_blueprint from run payload when available."""
        resolved_blueprint = {
            "name": "test-agent",
            "system_prompt": "You are a test agent.",
            "mcp_servers": {
                "api": {
                    "type": "http",
                    "url": "http://resolved-api.example.com",
                }
            }
        }

        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name="test-agent",
            parameters={"prompt": "Hello"},
            project_dir=None,
            resolved_agent_blueprint=resolved_blueprint,
        )

        payload = executor_with_mcp_url._build_payload(run, "start")

        assert "agent_blueprint" in payload
        assert payload["agent_blueprint"]["name"] == "test-agent"
        assert payload["agent_blueprint"]["mcp_servers"]["api"]["url"] == "http://resolved-api.example.com"

    def test_resolves_runner_placeholders(self, executor_with_mcp_url):
        """Resolves ${runner.orchestrator_mcp_url} in resolved_agent_blueprint."""
        resolved_blueprint = {
            "name": "test-agent",
            "mcp_servers": {
                "orchestrator": {
                    "type": "http",
                    "url": "${runner.orchestrator_mcp_url}",
                    "config": {
                        "run_id": "run-123"
                    }
                }
            }
        }

        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name="test-agent",
            parameters={"prompt": "Hello"},
            project_dir=None,
            resolved_agent_blueprint=resolved_blueprint,
        )

        payload = executor_with_mcp_url._build_payload(run, "start")

        # ${runner.orchestrator_mcp_url} should be resolved
        assert payload["agent_blueprint"]["mcp_servers"]["orchestrator"]["url"] == "http://localhost:9999/mcp"
        # Other values should be unchanged
        assert payload["agent_blueprint"]["mcp_servers"]["orchestrator"]["config"]["run_id"] == "run-123"

    def test_preserves_other_placeholders_in_runner_resolution(self, executor_with_mcp_url):
        """Unknown ${runner.X} placeholders are preserved."""
        resolved_blueprint = {
            "value": "${runner.unknown_key}"
        }

        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name="test-agent",
            parameters={"prompt": "Hello"},
            project_dir=None,
            resolved_agent_blueprint=resolved_blueprint,
        )

        payload = executor_with_mcp_url._build_payload(run, "start")

        # Unknown runner placeholders should be preserved
        assert payload["agent_blueprint"]["value"] == "${runner.unknown_key}"

    def test_does_not_mutate_original_blueprint(self, executor_with_mcp_url):
        """Original resolved_agent_blueprint is not modified."""
        original_blueprint = {
            "mcp_servers": {
                "orchestrator": {
                    "url": "${runner.orchestrator_mcp_url}"
                }
            }
        }

        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name="test-agent",
            parameters={"prompt": "Hello"},
            project_dir=None,
            resolved_agent_blueprint=original_blueprint,
        )

        executor_with_mcp_url._build_payload(run, "start")

        # Original should be unchanged
        assert original_blueprint["mcp_servers"]["orchestrator"]["url"] == "${runner.orchestrator_mcp_url}"


class TestRunnerPlaceholderResolution:
    """Tests for _resolve_runner_placeholders method."""

    @pytest.fixture
    def executor_with_mcp_url(self, tmp_path):
        """Create executor with MCP server URL."""
        fake_exec = tmp_path / "test-exec"
        fake_exec.write_text("#!/bin/bash\necho test")
        fake_exec.chmod(0o755)
        with patch("executor.get_runner_dir", return_value=tmp_path):
            return RunExecutor(
                default_project_dir="/default/path",
                mcp_server_url="http://localhost:8888/mcp",
            )

    def test_resolves_orchestrator_mcp_url(self, executor_with_mcp_url):
        """Resolves ${runner.orchestrator_mcp_url}."""
        blueprint = {
            "url": "${runner.orchestrator_mcp_url}"
        }

        resolved = executor_with_mcp_url._resolve_runner_placeholders(blueprint)

        assert resolved["url"] == "http://localhost:8888/mcp"

    def test_resolves_in_nested_structures(self, executor_with_mcp_url):
        """Resolves runner placeholders in nested dicts and lists."""
        blueprint = {
            "level1": {
                "level2": {
                    "url": "${runner.orchestrator_mcp_url}"
                }
            },
            "urls": ["${runner.orchestrator_mcp_url}", "http://other.com"]
        }

        resolved = executor_with_mcp_url._resolve_runner_placeholders(blueprint)

        assert resolved["level1"]["level2"]["url"] == "http://localhost:8888/mcp"
        assert resolved["urls"][0] == "http://localhost:8888/mcp"
        assert resolved["urls"][1] == "http://other.com"

    def test_handles_no_mcp_url(self, tmp_path):
        """Handles case where mcp_server_url is None."""
        fake_exec = tmp_path / "test-exec"
        fake_exec.write_text("#!/bin/bash\necho test")
        fake_exec.chmod(0o755)
        with patch("executor.get_runner_dir", return_value=tmp_path):
            executor = RunExecutor(
                default_project_dir="/default/path",
                mcp_server_url=None,  # No MCP URL
            )

        blueprint = {
            "url": "${runner.orchestrator_mcp_url}"
        }

        resolved = executor._resolve_runner_placeholders(blueprint)

        # Should preserve placeholder when no URL available
        assert resolved["url"] == "${runner.orchestrator_mcp_url}"
