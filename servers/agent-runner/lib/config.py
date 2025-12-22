"""
Runner Configuration

Configuration for the Agent Runner process that polls Agent Coordinator for runs.
Supports both API key and Auth0 M2M authentication.
"""

import os
from dataclasses import dataclass


# Environment variable names
ENV_COORDINATOR_URL = "AGENT_ORCHESTRATOR_API_URL"
ENV_API_KEY = "AGENT_ORCHESTRATOR_API_KEY"
ENV_POLL_TIMEOUT = "POLL_TIMEOUT"
ENV_HEARTBEAT_INTERVAL = "HEARTBEAT_INTERVAL"
ENV_PROJECT_DIR = "PROJECT_DIR"
ENV_RUNNER_TAGS = "RUNNER_TAGS"  # Comma-separated capability tags (ADR-011)

# Auth0 M2M environment variables
ENV_AUTH0_DOMAIN = "AUTH0_DOMAIN"
ENV_AUTH0_CLIENT_ID = "AUTH0_CLIENT_ID"
ENV_AUTH0_CLIENT_SECRET = "AUTH0_CLIENT_SECRET"
ENV_AUTH0_AUDIENCE = "AUTH0_AUDIENCE"

# Defaults
DEFAULT_COORDINATOR_URL = "http://localhost:8765"
DEFAULT_POLL_TIMEOUT = 30
DEFAULT_HEARTBEAT_INTERVAL = 60


def _parse_tags(tags_str: str) -> list[str]:
    """Parse comma-separated tags string into a list."""
    if not tags_str:
        return []
    return [tag.strip() for tag in tags_str.split(",") if tag.strip()]


@dataclass
class RunnerConfig:
    """Configuration for the Agent Runner."""

    agent_coordinator_url: str
    api_key: str
    poll_timeout: int
    heartbeat_interval: int
    project_dir: str
    tags: list[str]  # Capability tags (ADR-011)

    # Auth0 M2M configuration
    auth0_domain: str
    auth0_client_id: str
    auth0_client_secret: str
    auth0_audience: str

    @property
    def use_oidc(self) -> bool:
        """Check if Auth0 OIDC is configured."""
        return bool(
            self.auth0_domain
            and self.auth0_client_id
            and self.auth0_client_secret
            and self.auth0_audience
        )

    @classmethod
    def from_env(cls) -> "RunnerConfig":
        """Load configuration from environment variables."""
        return cls(
            agent_coordinator_url=os.environ.get(ENV_COORDINATOR_URL, DEFAULT_COORDINATOR_URL),
            api_key=os.environ.get(ENV_API_KEY, ""),
            poll_timeout=int(os.environ.get(ENV_POLL_TIMEOUT, DEFAULT_POLL_TIMEOUT)),
            heartbeat_interval=int(
                os.environ.get(ENV_HEARTBEAT_INTERVAL, DEFAULT_HEARTBEAT_INTERVAL)
            ),
            project_dir=os.environ.get(ENV_PROJECT_DIR, os.getcwd()),
            tags=_parse_tags(os.environ.get(ENV_RUNNER_TAGS, "")),
            # Auth0 M2M
            auth0_domain=os.environ.get(ENV_AUTH0_DOMAIN, ""),
            auth0_client_id=os.environ.get(ENV_AUTH0_CLIENT_ID, ""),
            auth0_client_secret=os.environ.get(ENV_AUTH0_CLIENT_SECRET, ""),
            auth0_audience=os.environ.get(ENV_AUTH0_AUDIENCE, ""),
        )
