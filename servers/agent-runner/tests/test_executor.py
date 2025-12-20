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
        with patch("executor.get_executor_path", return_value=fake_exec):
            return RunExecutor(default_project_dir="/default/path")

    def test_start_payload_minimal(self, executor):
        """Start payload includes required fields."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name=None,
            prompt="Hello world",
            project_dir=None,
        )

        payload = executor._build_payload(run, "start")

        assert payload["schema_version"] == SCHEMA_VERSION
        assert payload["mode"] == "start"
        assert payload["session_id"] == "ses_test123"
        assert payload["prompt"] == "Hello world"
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
            prompt="Hello world",
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
            prompt="Continue please",
            project_dir="/should/be/ignored",
        )

        payload = executor._build_payload(run, "resume")

        assert payload["schema_version"] == SCHEMA_VERSION
        assert payload["mode"] == "resume"
        assert payload["session_id"] == "ses_test123"
        assert payload["prompt"] == "Continue please"
        # Resume should NOT include agent_name or project_dir
        assert "agent_name" not in payload
        assert "project_dir" not in payload

    def test_payload_is_valid_json(self, executor):
        """Payload can be serialized to valid JSON."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name="agent",
            prompt="Hello 世界! 😀",
            project_dir="/path",
        )

        payload = executor._build_payload(run, "start")
        json_str = json.dumps(payload)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["prompt"] == "Hello 世界! 😀"


class TestExecuteWithPayload:
    """Tests for RunExecutor._execute_with_payload()"""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with mocked executor path."""
        fake_exec = tmp_path / "test-exec"
        fake_exec.write_text("#!/bin/bash\necho test")
        fake_exec.chmod(0o755)

        with patch("executor.get_executor_path", return_value=fake_exec):
            return RunExecutor(default_project_dir="/default/path")

    def test_execute_calls_executor(self, executor):
        """Execute calls executor subprocess."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name=None,
            prompt="Hello",
            project_dir=None,
        )

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_popen.return_value = mock_process

            executor._execute_with_payload(run, "start")

            # Should call Popen with executor
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args
            cmd = call_args[0][0]
            assert "test-exec" in cmd[0]

    def test_execute_writes_json_to_stdin(self, executor):
        """Execute writes JSON payload to subprocess stdin."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_test123",
            agent_name=None,
            prompt="Hello",
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
            prompt="Hello",
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

        with patch("executor.get_executor_path", return_value=fake_exec):
            return RunExecutor(default_project_dir="/default/path")

    def test_execute_start_session(self, executor):
        """execute_run routes start_session to mode='start'."""
        run = Run(
            run_id="run-1",
            type="start_session",
            session_id="ses_testid1",
            agent_name=None,
            prompt="Hello",
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
            prompt="Hello",
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
            prompt="Hello",
            project_dir=None,
        )

        with pytest.raises(ValueError, match="Unknown agent run type: unknown_type"):
            executor.execute_run(run)
