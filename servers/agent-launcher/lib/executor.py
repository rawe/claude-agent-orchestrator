"""
Job Executor - spawns ao-exec subprocess with JSON payload via stdin.

Maps job types to execution modes and handles subprocess spawning.
Uses unified ao-exec entrypoint with structured JSON payloads.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional
import logging

from api_client import Job
from invocation import SCHEMA_VERSION

logger = logging.getLogger(__name__)


# Environment variable for executor path (relative to agent-launcher dir)
ENV_EXECUTOR_PATH = "AGENT_EXECUTOR_PATH"
DEFAULT_EXECUTOR_PATH = "claude-code/ao-exec"


def get_executor_path() -> Path:
    """Get path to executor script.

    Uses AGENT_EXECUTOR_PATH env var (relative to agent-launcher dir).
    Default: claude-code/ao-exec

    Examples:
        AGENT_EXECUTOR_PATH=claude-code/ao-exec    (default)
        AGENT_EXECUTOR_PATH=test-executor/test-exec
        AGENT_EXECUTOR_PATH=openai/openai-exec
    """
    executor_rel_path = os.environ.get(ENV_EXECUTOR_PATH, DEFAULT_EXECUTOR_PATH)

    # Resolve relative to agent-launcher dir
    launcher_dir = Path(__file__).parent.parent.resolve()
    executor_path = launcher_dir / executor_rel_path

    if not executor_path.exists():
        raise RuntimeError(f"Executor not found: {executor_path}")

    return executor_path


class JobExecutor:
    """Executes jobs by spawning executor subprocess with JSON payload."""

    def __init__(self, default_project_dir: str):
        """Initialize executor.

        Args:
            default_project_dir: Default project directory if job doesn't specify one
        """
        self.default_project_dir = default_project_dir
        self.executor_path = get_executor_path()

        logger.debug(f"Executor path: {self.executor_path}")

    def execute(self, job: Job, parent_session_name: Optional[str] = None) -> subprocess.Popen:
        """Execute a job by spawning ao-exec with JSON payload via stdin.

        Args:
            job: The job to execute
            parent_session_name: Optional parent session name for callback context

        Returns:
            The spawned subprocess.Popen object
        """
        # Map job type to execution mode
        if job.type == "start_session":
            mode = "start"
        elif job.type == "resume_session":
            mode = "resume"
        else:
            raise ValueError(f"Unknown job type: {job.type}")

        return self._execute_with_payload(job, mode)

    def _build_payload(self, job: Job, mode: str) -> dict:
        """Build JSON payload for ao-exec.

        Args:
            job: The job to execute
            mode: Execution mode ('start' or 'resume')

        Returns:
            Dictionary payload for JSON serialization
        """
        payload = {
            "schema_version": SCHEMA_VERSION,
            "mode": mode,
            "session_name": job.session_name,
            "prompt": job.prompt,
        }

        # Add optional fields for start mode
        if mode == "start":
            if job.agent_name:
                payload["agent_name"] = job.agent_name
            project_dir = job.project_dir or self.default_project_dir
            payload["project_dir"] = project_dir

        return payload

    def _execute_with_payload(self, job: Job, mode: str) -> subprocess.Popen:
        """Execute executor with JSON payload via stdin.

        Args:
            job: The job to execute
            mode: Execution mode ('start' or 'resume')

        Returns:
            The spawned subprocess.Popen object
        """
        # Build JSON payload
        payload = self._build_payload(job, mode)
        payload_json = json.dumps(payload)

        # Build command
        cmd = [str(self.executor_path)]

        # Build environment
        env = os.environ.copy()

        # Set AGENT_SESSION_NAME so the session knows its own identity.
        # This allows MCP servers to include the session name in HTTP headers
        # for callback support (X-Agent-Session-Name header).
        # Flow: Launcher sets env → ao-exec replaces ${AGENT_SESSION_NAME} in MCP config
        #       → Claude sends X-Agent-Session-Name header → MCP server reads it
        env["AGENT_SESSION_NAME"] = job.session_name

        # Log action (don't log full payload - prompt may be large/sensitive)
        if mode == "start":
            logger.info(
                f"Starting session: {job.session_name}"
                + (f" (agent={job.agent_name})" if job.agent_name else "")
            )
        else:
            logger.info(f"Resuming session: {job.session_name}")

        logger.debug(
            f"Executing ao-exec: mode={mode} session={job.session_name} "
            f"prompt_len={len(job.prompt)}"
        )

        # Spawn subprocess with stdin pipe
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )

        # Write payload to stdin and close
        process.stdin.write(payload_json)
        process.stdin.close()

        return process
