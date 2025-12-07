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

    Follows the same pattern as the MCP server:
    servers/agent-launcher/ -> plugins/orchestrator/skills/orchestrator/commands/
    """
    # Start from this file's location
    launcher_dir = Path(__file__).parent.parent.resolve()

    # Navigate to project root (servers/agent-launcher -> project root)
    project_root = launcher_dir.parent.parent

    # Commands are in plugins/orchestrator/skills/orchestrator/commands/
    commands_dir = project_root / "plugins" / "orchestrator" / "skills" / "orchestrator" / "commands"

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

        logger.info(f"Commands directory: {self.commands_dir}")

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

        # Build environment - inherit from parent but don't set AGENT_SESSION_NAME
        # The session name env var is only set by the MCP server when spawning
        # children with callback=true. Jobs from the queue are top-level sessions
        # with no parent (unless AGENT_SESSION_NAME is already in the environment
        # from a parent MCP server process).
        env = os.environ.copy()

        logger.info(f"Executing: {' '.join(cmd)}")

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

        # Build environment - inherit from parent but don't set AGENT_SESSION_NAME
        # Same as start_session: the env var is only set by MCP server for callbacks.
        env = os.environ.copy()

        logger.info(f"Executing: {' '.join(cmd)}")

        # Spawn subprocess
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        return process
