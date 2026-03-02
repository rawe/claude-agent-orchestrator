"""
Executor Test Harness

Orchestrates test execution by managing:
- Fake Runner Gateway
- Minimal MCP Server
- Executor subprocess

Usage:
    harness = ExecutorTestHarness()
    harness.start()

    result = harness.run_executor(payload)
    assert result.success
    assert "hello" in result.stdout

    calls = harness.get_gateway_calls()
    tool_calls = harness.get_mcp_tool_calls()

    harness.stop()
"""

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fake_gateway import FakeRunnerGateway, GatewayCall, SessionState
from .mcp_server import MinimalMCPServer, ToolCall


@dataclass
class ExecutorResult:
    """Result of executor execution."""
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float

    @property
    def success(self) -> bool:
        """True if executor exited with code 0."""
        return self.exit_code == 0

    @property
    def output(self) -> str:
        """Alias for stdout."""
        return self.stdout


class _StderrDrainer:
    """Background thread that drains stderr to prevent pipe deadlocks.

    The executor writes [DIAG] lines to stderr. If the pipe buffer fills
    up, the executor blocks. This drainer reads stderr in a background
    thread, storing lines for later inspection.
    """

    def __init__(self, pipe):
        self._pipe = pipe
        self._lines: list[str] = []
        self._thread = threading.Thread(target=self._drain, daemon=True)
        self._thread.start()

    def _drain(self):
        try:
            for line in self._pipe:
                self._lines.append(line)
        except ValueError:
            # Pipe closed
            pass

    @property
    def output(self) -> str:
        """Return all drained stderr text."""
        return "".join(self._lines)

    def join(self, timeout: float = 5.0):
        self._thread.join(timeout=timeout)


class MultiTurnExecutor:
    """Manages a long-lived executor subprocess for multi-turn tests.

    The executor reads NDJSON lines from stdin:
      - Line 1: initial invocation (start payload)
      - Subsequent lines: {"type": "turn", "run_id": "...", "parameters": {...}}
      - {"type": "shutdown"} to exit gracefully

    After each turn it writes to stdout:
      {"type": "turn_complete", "run_id": "...", "result": "..."}
    """

    def __init__(self, cmd: list[str], env: dict, cwd: str):
        self._cmd = cmd
        self._env = env
        self._cwd = cwd
        self._proc: subprocess.Popen | None = None
        self._drainer: _StderrDrainer | None = None

    def start(self, initial_payload: dict, timeout: float = 120) -> dict:
        """Spawn the executor and send the initial invocation.

        Args:
            initial_payload: JSON payload for the first turn (mode=start).
            timeout: Seconds to wait for the first turn_complete.

        Returns:
            Parsed turn_complete dict from stdout.
        """
        self._proc = subprocess.Popen(
            self._cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self._cwd,
            env=self._env,
        )
        self._drainer = _StderrDrainer(self._proc.stderr)

        # Write initial payload as first NDJSON line
        self._proc.stdin.write(json.dumps(initial_payload) + "\n")
        self._proc.stdin.flush()

        return self._read_turn_result(timeout)

    def send_turn(self, run_id: str, parameters: dict, timeout: float = 120) -> dict:
        """Send a subsequent turn and wait for the result.

        Args:
            run_id: Run ID for the turn.
            parameters: Parameters dict (must contain "prompt").
            timeout: Seconds to wait for turn_complete.

        Returns:
            Parsed turn_complete dict from stdout.
        """
        msg = {"type": "turn", "run_id": run_id, "parameters": parameters}
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()
        return self._read_turn_result(timeout)

    def shutdown(self, timeout: float = 10) -> int:
        """Send shutdown message, close stdin, and wait for exit.

        Returns:
            Process exit code.
        """
        try:
            self._proc.stdin.write(json.dumps({"type": "shutdown"}) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        try:
            self._proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        exit_code = self._proc.wait(timeout=timeout)
        if self._drainer:
            self._drainer.join(timeout=5.0)
        return exit_code

    def close_stdin(self, timeout: float = 10) -> int:
        """Close stdin (EOF) without sending shutdown, and wait for exit.

        Returns:
            Process exit code.
        """
        try:
            self._proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        exit_code = self._proc.wait(timeout=timeout)
        if self._drainer:
            self._drainer.join(timeout=5.0)
        return exit_code

    def kill(self):
        """Force kill the executor process."""
        if self._proc and self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait(timeout=5)
        if self._drainer:
            self._drainer.join(timeout=2.0)

    @property
    def stderr_output(self) -> str:
        """Return all stderr output drained so far."""
        if self._drainer:
            return self._drainer.output
        return ""

    def _read_turn_result(self, timeout: float) -> dict:
        """Read stdout lines until a JSON line with type=turn_complete.

        Non-JSON lines are skipped (the executor may print debug output).

        Args:
            timeout: Seconds to wait before raising TimeoutError.

        Returns:
            Parsed turn_complete dict.
        """
        import select
        import time

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Timed out waiting for turn_complete after {timeout}s. "
                    f"stderr: {self.stderr_output[-500:]}"
                )

            # Use select to wait for data with timeout (Unix only)
            ready, _, _ = select.select([self._proc.stdout], [], [], min(remaining, 1.0))
            if not ready:
                # Check if process died
                if self._proc.poll() is not None:
                    raise RuntimeError(
                        f"Executor exited with code {self._proc.returncode} "
                        f"before sending turn_complete. stderr: {self.stderr_output[-500:]}"
                    )
                continue

            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError(
                    f"Executor stdout closed before turn_complete. "
                    f"stderr: {self.stderr_output[-500:]}"
                )

            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                if isinstance(data, dict) and data.get("type") == "turn_complete":
                    return data
            except json.JSONDecodeError:
                # Skip non-JSON output
                continue


class ExecutorTestHarness:
    """
    Test harness for Claude Code executor integration tests.

    Manages lifecycle of:
    - Fake Runner Gateway (simulates coordinator)
    - Minimal MCP Server (provides test tools)
    - Executor subprocess

    Example:
        # Default executor (claude-code)
        harness = ExecutorTestHarness()

        # Test a different executor
        harness = ExecutorTestHarness(executor_path="executors/claude-code-v2/ao-claude-code-exec")

        # Or via environment variable
        EXECUTOR_UNDER_TEST=executors/my-executor/ao-exec pytest tests/integration/ -v

        harness.start()
        try:
            result = harness.run_executor({...})
            assert result.success
        finally:
            harness.stop()
    """

    # Default executor path (relative to agent-runner directory)
    DEFAULT_EXECUTOR_PATH = "executors/claude-code/ao-claude-code-exec"

    # Delay between start and resume to allow CLI session files to flush
    RESUME_DELAY = 2

    def __init__(self, executor_path: str | None = None):
        """
        Initialize test harness.

        Args:
            executor_path: Path to executor script relative to agent-runner directory.
                          Defaults to EXECUTOR_UNDER_TEST env var or claude-code executor.
        """
        self._gateway = FakeRunnerGateway()
        self._mcp_server = MinimalMCPServer()
        self._started = False

        # Determine agent-runner directory
        self._runner_dir = Path(__file__).parent.parent.parent.parent

        # Resolve executor path: parameter > env var > default
        if executor_path:
            self._executor_rel_path = executor_path
        else:
            self._executor_rel_path = os.environ.get(
                "EXECUTOR_UNDER_TEST",
                self.DEFAULT_EXECUTOR_PATH
            )

        self._executor_path = self._runner_dir / self._executor_rel_path

        if not self._executor_path.exists():
            raise FileNotFoundError(
                f"Executor not found at {self._executor_path}. "
                f"Set EXECUTOR_UNDER_TEST env var or pass executor_path parameter."
            )

    @property
    def gateway_url(self) -> str:
        """Get the fake gateway URL."""
        return self._gateway.url

    @property
    def mcp_url(self) -> str:
        """Get the MCP server URL."""
        return self._mcp_server.url

    def start(self):
        """Start all services (gateway and MCP server)."""
        if self._started:
            return

        self._gateway.start()
        self._mcp_server.start()
        self._started = True

    def stop(self):
        """Stop all services."""
        if not self._started:
            return

        self._gateway.stop()
        self._mcp_server.stop()
        self._started = False

    def wait_for_session(self):
        """Wait for CLI session files to flush before resume."""
        time.sleep(self.RESUME_DELAY)

    def clear(self):
        """Clear all recorded calls (between tests)."""
        self._gateway.clear()
        self._mcp_server.clear()

    def run_executor(
        self,
        payload: dict,
        timeout: float = 120.0,
        env_override: dict[str, str] | None = None,
    ) -> ExecutorResult:
        """
        Run the executor with a JSON payload.

        Args:
            payload: JSON payload to send on stdin
            timeout: Maximum execution time in seconds
            env_override: Additional environment variables

        Returns:
            ExecutorResult with stdout, stderr, exit_code, duration
        """
        if not self._started:
            raise RuntimeError("Harness not started. Call start() first.")

        # Build environment
        env = os.environ.copy()
        env["AGENT_ORCHESTRATOR_API_URL"] = self._gateway.url

        # Set session ID for MCP headers
        session_id = payload.get("session_id", "")
        if session_id:
            env["AGENT_SESSION_ID"] = session_id

        # Apply overrides
        if env_override:
            env.update(env_override)

        # Build command
        cmd = ["uv", "run", "--script", str(self._executor_path)]

        # Serialize payload
        payload_json = json.dumps(payload)

        # Run executor
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                input=payload_json,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self._runner_dir),
                env=env,
            )
            duration = time.time() - start_time

            return ExecutorResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_seconds=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return ExecutorResult(
                stdout="",
                stderr=f"Executor timed out after {timeout} seconds",
                exit_code=-1,
                duration_seconds=duration,
            )

    def run_start_and_resume(
        self,
        start_payload: dict,
        resume_prompt: str,
        start_timeout: float = 120.0,
        resume_timeout: float = 120.0,
    ) -> tuple[ExecutorResult, ExecutorResult]:
        """
        Run start followed by resume for the same session.

        Args:
            start_payload: Payload for start mode
            resume_prompt: Prompt for resume mode
            start_timeout: Timeout for start
            resume_timeout: Timeout for resume

        Returns:
            Tuple of (start_result, resume_result)
        """
        # Run start
        start_result = self.run_executor(start_payload, timeout=start_timeout)

        if not start_result.success:
            # Return early if start failed
            return start_result, ExecutorResult(
                stdout="",
                stderr="Skipped: start failed",
                exit_code=-1,
                duration_seconds=0,
            )

        self.wait_for_session()

        # Build resume payload
        session_id = start_payload["session_id"]
        resume_payload = {
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": session_id,
            "parameters": {"prompt": resume_prompt},
        }

        # Copy agent_blueprint if present (for MCP servers)
        if "agent_blueprint" in start_payload:
            resume_payload["agent_blueprint"] = start_payload["agent_blueprint"]

        # Run resume
        resume_result = self.run_executor(resume_payload, timeout=resume_timeout)

        return start_result, resume_result

    # Gateway call accessors

    def get_gateway_calls(self) -> list[GatewayCall]:
        """Get all recorded gateway calls."""
        return self._gateway.get_calls()

    def get_bind_calls(self) -> list[GatewayCall]:
        """Get all /bind calls."""
        return self._gateway.get_bind_calls()

    def get_event_calls(self) -> list[GatewayCall]:
        """Get all /events calls."""
        return self._gateway.get_event_calls()

    def get_events_for_session(self, session_id: str) -> list[dict]:
        """Get all events for a specific session."""
        return self._gateway.get_events_for_session(session_id)

    def get_message_events(self, session_id: str) -> list[dict]:
        """Get message events (user/assistant) for a session."""
        events = self.get_events_for_session(session_id)
        return [e for e in events if e.get("event_type") == "message"]

    def get_result_events(self, session_id: str) -> list[dict]:
        """Get result events for a session."""
        events = self.get_events_for_session(session_id)
        return [e for e in events if e.get("event_type") == "result"]

    def get_post_tool_events(self, session_id: str) -> list[dict]:
        """Get post_tool events for a session."""
        events = self.get_events_for_session(session_id)
        return [e for e in events if e.get("event_type") == "post_tool"]

    def get_session(self, session_id: str) -> SessionState | None:
        """Get session state from gateway."""
        return self._gateway.get_session(session_id)

    def set_session(self, session: SessionState):
        """Pre-configure a session (for resume tests)."""
        self._gateway.set_session(session)

    # MCP call accessors

    def get_mcp_tool_calls(self) -> list[ToolCall]:
        """Get all recorded MCP tool calls."""
        return self._mcp_server.get_tool_calls()

    def get_mcp_calls_by_tool(self, tool_name: str) -> list[ToolCall]:
        """Get MCP calls for a specific tool."""
        return self._mcp_server.get_tool_calls_by_name(tool_name)

    def get_mcp_stored_data(self) -> dict[str, str]:
        """Get data stored via store_data tool."""
        return self._mcp_server.get_stored_data()

    # Payload helpers

    def inject_mcp_url(self, payload: dict, server_name: str = "test-mcp") -> dict:
        """
        Inject MCP server URL into payload's agent_blueprint.

        Args:
            payload: Payload to modify (copied, not mutated)
            server_name: Name for the MCP server

        Returns:
            New payload with MCP server configured
        """
        payload = dict(payload)

        if "agent_blueprint" not in payload:
            payload["agent_blueprint"] = {}

        blueprint = dict(payload["agent_blueprint"])
        payload["agent_blueprint"] = blueprint

        if "mcp_servers" not in blueprint:
            blueprint["mcp_servers"] = {}

        mcp_servers = dict(blueprint["mcp_servers"])
        blueprint["mcp_servers"] = mcp_servers

        mcp_servers[server_name] = {"url": self._mcp_server.url}

        return payload

    # Multi-turn executor factory

    def create_multi_turn_executor(
        self,
        session_id: str | None = None,
        env_override: dict[str, str] | None = None,
    ) -> MultiTurnExecutor:
        """Create a MultiTurnExecutor wired to this harness's services.

        Args:
            session_id: Optional session ID for AGENT_SESSION_ID env var.
            env_override: Additional environment variables.

        Returns:
            A MultiTurnExecutor ready to call .start().
        """
        if not self._started:
            raise RuntimeError("Harness not started. Call start() first.")

        env = os.environ.copy()
        env["AGENT_ORCHESTRATOR_API_URL"] = self._gateway.url

        if session_id:
            env["AGENT_SESSION_ID"] = session_id

        if env_override:
            env.update(env_override)

        cmd = ["uv", "run", "--script", str(self._executor_path)]

        return MultiTurnExecutor(cmd=cmd, env=env, cwd=str(self._runner_dir))


# Context manager support
class ExecutorTestContext:
    """
    Context manager for executor tests.

    Usage:
        with ExecutorTestContext() as harness:
            result = harness.run_executor(payload)
            assert result.success
    """

    def __init__(self):
        self._harness = ExecutorTestHarness()

    def __enter__(self) -> ExecutorTestHarness:
        self._harness.start()
        return self._harness

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._harness.stop()
        return False


# Convenience for testing the harness directly
if __name__ == "__main__":
    import sys

    harness = ExecutorTestHarness()
    print(f"Executor path: {harness._executor_path}")
    print(f"Runner dir: {harness._runner_dir}")

    harness.start()
    print(f"Gateway URL: {harness.gateway_url}")
    print(f"MCP URL: {harness.mcp_url}")

    # Test with a simple payload (will fail without valid Claude API key)
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        payload = {
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_harness_test",
            "parameters": {"prompt": "Say hello"},
            "project_dir": "/tmp/harness-test",
        }
        print(f"\nRunning test payload...")
        result = harness.run_executor(payload, timeout=30.0)
        print(f"Exit code: {result.exit_code}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(f"Stdout: {result.stdout[:200]}...")
        print(f"Stderr: {result.stderr[:200]}...")
        print(f"Gateway calls: {len(harness.get_gateway_calls())}")

    harness.stop()
    print("\nHarness stopped.")
