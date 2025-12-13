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


def discover_commands_dir() -> Path:
    """Auto-discover the ao-* commands directory.

    Commands are in servers/agent-launcher/claude-code/
    """
    # Start from this file's location (lib/executor.py)
    # Go up to agent-launcher dir, then into claude-code/
    launcher_dir = Path(__file__).parent.parent.resolve()
    commands_dir = launcher_dir / "claude-code"

    if not commands_dir.exists():
        raise RuntimeError(f"Commands directory not found: {commands_dir}")

    return commands_dir


class JobExecutor:
    """Executes jobs by spawning ao-exec subprocess with JSON payload."""

    def __init__(self, default_project_dir: str):
        """Initialize executor.

        Args:
            default_project_dir: Default project directory if job doesn't specify one
        """
        self.default_project_dir = default_project_dir
        self.commands_dir = discover_commands_dir()

        logger.debug(f"Commands directory: {self.commands_dir}")

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
        """Execute ao-exec with JSON payload via stdin.

        Args:
            job: The job to execute
            mode: Execution mode ('start' or 'resume')

        Returns:
            The spawned subprocess.Popen object
        """
        ao_exec = self.commands_dir / "ao-exec"

        # Build JSON payload
        payload = self._build_payload(job, mode)
        payload_json = json.dumps(payload)

        # Build command (just the executor, no args)
        cmd = [str(ao_exec)]

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
