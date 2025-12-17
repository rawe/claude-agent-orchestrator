"""
Launcher Configuration

Configuration for the Agent Launcher process that polls Agent Coordinator for runs.
"""

import os
from dataclasses import dataclass


# Environment variable names
ENV_COORDINATOR_URL = "AGENT_ORCHESTRATOR_API_URL"
ENV_POLL_TIMEOUT = "POLL_TIMEOUT"
ENV_HEARTBEAT_INTERVAL = "HEARTBEAT_INTERVAL"
ENV_PROJECT_DIR = "PROJECT_DIR"

# Defaults
DEFAULT_COORDINATOR_URL = "http://localhost:8765"
DEFAULT_POLL_TIMEOUT = 30
DEFAULT_HEARTBEAT_INTERVAL = 60


@dataclass
class LauncherConfig:
    """Configuration for the Agent Launcher."""

    agent_coordinator_url: str
    poll_timeout: int
    heartbeat_interval: int
    project_dir: str

    @classmethod
    def from_env(cls) -> "LauncherConfig":
        """Load configuration from environment variables."""
        return cls(
            agent_coordinator_url=os.environ.get(ENV_COORDINATOR_URL, DEFAULT_COORDINATOR_URL),
            poll_timeout=int(os.environ.get(ENV_POLL_TIMEOUT, DEFAULT_POLL_TIMEOUT)),
            heartbeat_interval=int(
                os.environ.get(ENV_HEARTBEAT_INTERVAL, DEFAULT_HEARTBEAT_INTERVAL)
            ),
            project_dir=os.environ.get(ENV_PROJECT_DIR, os.getcwd()),
        )
