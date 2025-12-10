"""
Job Executor - spawns ao-start and ao-resume subprocesses.

Maps job types to commands and handles subprocess spawning.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional
import logging

from api_client import Job

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
    """Executes jobs by spawning ao-* subprocess commands."""

    def __init__(self, default_project_dir: str):
        """Initialize executor.

        Args:
            default_project_dir: Default project directory if job doesn't specify one
        """
        self.default_project_dir = default_project_dir
        self.commands_dir = discover_commands_dir()

        logger.debug(f"Commands directory: {self.commands_dir}")

    def execute(self, job: Job, parent_session_name: Optional[str] = None) -> subprocess.Popen:
        """Execute a job by spawning the appropriate subprocess.

        Args:
            job: The job to execute
            parent_session_name: Optional parent session name for callback context

        Returns:
            The spawned subprocess.Popen object
        """
        if job.type == "start_session":
            return self._execute_start_session(job, parent_session_name)
        elif job.type == "resume_session":
            return self._execute_resume_session(job, parent_session_name)
        else:
            raise ValueError(f"Unknown job type: {job.type}")

    def _execute_start_session(self, job: Job, parent_session_name: Optional[str] = None) -> subprocess.Popen:
        """Execute a start_session job via ao-start."""
        ao_start = self.commands_dir / "ao-start"

        # Build command
        cmd = [
            str(ao_start),
            job.session_name,
            "--prompt", job.prompt,
        ]

        if job.agent_name:
            cmd.extend(["--agent", job.agent_name])

        project_dir = job.project_dir or self.default_project_dir
        cmd.extend(["--project-dir", project_dir])

        # Build environment
        env = os.environ.copy()

        # Set AGENT_SESSION_NAME so the session knows its own identity.
        # This allows MCP servers to include the session name in HTTP headers
        # for callback support (X-Agent-Session-Name header).
        # Flow: Launcher sets env → ao-start replaces ${AGENT_SESSION_NAME} in MCP config
        #       → Claude sends X-Agent-Session-Name header → MCP server reads it
        env["AGENT_SESSION_NAME"] = job.session_name

        logger.info(f"Starting session: {job.session_name}" + (f" (agent={job.agent_name})" if job.agent_name else ""))

        # Spawn subprocess
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        return process

    def _execute_resume_session(self, job: Job, parent_session_name: Optional[str] = None) -> subprocess.Popen:
        """Execute a resume_session job via ao-resume."""
        ao_resume = self.commands_dir / "ao-resume"

        # Build command
        cmd = [
            str(ao_resume),
            job.session_name,
            "--prompt", job.prompt,
        ]

        # Build environment
        env = os.environ.copy()

        # Set AGENT_SESSION_NAME so the session knows its own identity (same as start)
        env["AGENT_SESSION_NAME"] = job.session_name

        logger.info(f"Resuming session: {job.session_name}")

        # Spawn subprocess
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        return process
