"""
Configuration for Agent Launcher.

Loads settings from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass


@dataclass
class LauncherConfig:
    """Configuration for the Agent Launcher."""

    # Agent Runtime connection
    agent_runtime_url: str

    # Polling configuration
    poll_timeout: int  # seconds

    # Heartbeat configuration
    heartbeat_interval: int  # seconds

    # Default project directory for ao-* commands
    project_dir: str

    @classmethod
    def from_env(cls) -> "LauncherConfig":
        """Load configuration from environment variables."""
        return cls(
            agent_runtime_url=os.getenv("AGENT_ORCHESTRATOR_API_URL", "http://localhost:8765"),
            poll_timeout=int(os.getenv("POLL_TIMEOUT", "30")),
            heartbeat_interval=int(os.getenv("HEARTBEAT_INTERVAL", "60")),
            project_dir=os.getenv("PROJECT_DIR", os.getcwd()),
        )
