"""
Run Executor - spawns ao-*-exec subprocess with JSON payload via stdin.

Maps agent run types to execution modes and handles subprocess spawning.
Uses unified ao-*-exec entrypoint with structured JSON payloads.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional
import logging

from api_client import Run
from invocation import SCHEMA_VERSION

logger = logging.getLogger(__name__)


# Environment variable for executor path (relative to agent-runner dir)
ENV_EXECUTOR_PATH = "AGENT_EXECUTOR_PATH"
DEFAULT_EXECUTOR_PATH = "executors/claude-code/ao-claude-code-exec"


def get_runner_dir() -> Path:
    """Get the agent-runner directory."""
    return Path(__file__).parent.parent.resolve()


def get_executors_dir() -> Path:
    """Get the executors directory."""
    return get_runner_dir() / "executors"


def list_executors() -> list[str]:
    """List available executor names (folder names in executors/).

    Returns:
        List of executor folder names sorted alphabetically
    """
    executors_dir = get_executors_dir()
    if not executors_dir.exists():
        return []

    return sorted([
        d.name for d in executors_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])


def resolve_executor_name(name: str) -> str:
    """Resolve executor name to full relative path.

    Looks for ao-*-exec file inside executors/<name>/ directory.

    Args:
        name: Executor folder name (e.g., 'claude-code', 'test-executor')

    Returns:
        Relative path string (e.g., 'executors/claude-code/ao-claude-code-exec')

    Raises:
        RuntimeError: If executor folder or script not found
    """
    executor_dir = get_executors_dir() / name

    if not executor_dir.exists():
        available = ", ".join(list_executors()) or "none"
        raise RuntimeError(
            f"Executor '{name}' not found. Available: {available}"
        )

    # Find ao-*-exec file in the directory
    exec_files = list(executor_dir.glob("ao-*-exec"))
    if not exec_files:
        raise RuntimeError(
            f"No ao-*-exec script found in executors/{name}/"
        )
    if len(exec_files) > 1:
        raise RuntimeError(
            f"Multiple ao-*-exec scripts found in executors/{name}/: "
            f"{[f.name for f in exec_files]}"
        )

    # Return relative path string
    return f"executors/{name}/{exec_files[0].name}"


def get_executor_path() -> Path:
    """Get path to executor script.

    Uses AGENT_EXECUTOR_PATH env var (relative to agent-runner dir).
    Default: executors/claude-code/ao-claude-code-exec
    """
    executor_rel_path = os.environ.get(ENV_EXECUTOR_PATH, DEFAULT_EXECUTOR_PATH)

    # Resolve relative to agent-runner dir
    runner_dir = get_runner_dir()
    executor_path = runner_dir / executor_rel_path

    if not executor_path.exists():
        raise RuntimeError(f"Executor not found: {executor_path}")

    return executor_path


def get_executor_type() -> str:
    """Get executor type (folder name) from current executor path.

    Extracts folder name from paths like:
    - executors/claude-code/ao-claude-code-exec -> claude-code
    - executors/test-executor/ao-test-exec -> test-executor

    Returns:
        Executor folder name, or 'unknown' if cannot be determined
    """
    try:
        executor_path = get_executor_path()
        # Path is: .../executors/<name>/ao-*-exec
        # Parent is the executor folder
        return executor_path.parent.name
    except RuntimeError:
        return "unknown"


class RunExecutor:
    """Executes agent runs by spawning executor subprocess with JSON payload."""

    def __init__(self, default_project_dir: str):
        """Initialize executor.

        Args:
            default_project_dir: Default project directory if agent run doesn't specify one
        """
        self.default_project_dir = default_project_dir
        self.executor_path = get_executor_path()

        logger.debug(f"Executor path: {self.executor_path}")

    def execute_run(self, run: Run, parent_session_name: Optional[str] = None) -> subprocess.Popen:
        """Execute an agent run by spawning ao-*-exec with JSON payload via stdin.

        Args:
            run: The agent run to execute
            parent_session_name: Optional parent session name for callback context

        Returns:
            The spawned subprocess.Popen object
        """
        # Map run type to execution mode
        if run.type == "start_session":
            mode = "start"
        elif run.type == "resume_session":
            mode = "resume"
        else:
            raise ValueError(f"Unknown agent run type: {run.type}")

        return self._execute_with_payload(run, mode)

    def _build_payload(self, run: Run, mode: str) -> dict:
        """Build JSON payload for ao-*-exec.

        Args:
            run: The agent run to execute
            mode: Execution mode ('start' or 'resume')

        Returns:
            Dictionary payload for JSON serialization
        """
        payload = {
            "schema_version": SCHEMA_VERSION,
            "mode": mode,
            "session_name": run.session_name,
            "prompt": run.prompt,
        }

        # Add optional fields for start mode
        if mode == "start":
            if run.agent_name:
                payload["agent_name"] = run.agent_name
            project_dir = run.project_dir or self.default_project_dir
            payload["project_dir"] = project_dir

        return payload

    def _execute_with_payload(self, run: Run, mode: str) -> subprocess.Popen:
        """Execute executor with JSON payload via stdin.

        Args:
            run: The agent run to execute
            mode: Execution mode ('start' or 'resume')

        Returns:
            The spawned subprocess.Popen object
        """
        # Build JSON payload
        payload = self._build_payload(run, mode)
        payload_json = json.dumps(payload)

        # Build command - use 'uv run --script' for cross-platform compatibility
        # (Windows doesn't support shebangs, so we need explicit uv invocation)
        cmd = ["uv", "run", "--script", str(self.executor_path)]

        # Build environment
        env = os.environ.copy()

        # Set AGENT_SESSION_NAME so the session knows its own identity.
        # This allows MCP servers to include the session name in HTTP headers
        # for callback support (X-Agent-Session-Name header).
        # Flow: Runner sets env -> ao-*-exec replaces ${AGENT_SESSION_NAME} in MCP config
        #       -> Claude sends X-Agent-Session-Name header -> MCP server reads it
        env["AGENT_SESSION_NAME"] = run.session_name

        # Log action (don't log full payload - prompt may be large/sensitive)
        if mode == "start":
            logger.info(
                f"Starting session: {run.session_name}"
                + (f" (agent={run.agent_name})" if run.agent_name else "")
            )
        else:
            logger.info(f"Resuming session: {run.session_name}")

        logger.debug(
            f"Executing ao-*-exec: mode={mode} session={run.session_name} "
            f"prompt_len={len(run.prompt)}"
        )

        # Spawn subprocess with stdin pipe
        # encoding='utf-8' required for Windows (defaults to CP1252 which can't handle emojis)
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding='utf-8',
            errors='replace',
        )

        # Write payload to stdin and close
        process.stdin.write(payload_json)
        process.stdin.close()

        return process
