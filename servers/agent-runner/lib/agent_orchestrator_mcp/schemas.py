"""
Schemas and enums for the Agent Orchestrator MCP Server.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class ExecutionMode(str, Enum):
    """Execution modes for start_agent_session tool."""

    SYNC = "sync"
    """Synchronous - wait for session to complete and return result."""

    ASYNC_POLL = "async_poll"
    """Async with polling - return session_id, caller polls for status."""

    ASYNC_CALLBACK = "async_callback"
    """Async with callback - return immediately, parent receives callback on completion."""


@dataclass
class RequestContext:
    """Context extracted from HTTP request headers.

    Contains information about the calling agent session, used for:
    - Callback routing (parent_session_id)
    - Blueprint visibility filtering (tags)
    - Additional demands for runner selection
    """

    parent_session_id: Optional[str] = None
    """Session ID of the calling agent (for callbacks)."""

    tags: Optional[str] = None
    """Comma-separated tags for filtering visible blueprints."""

    additional_demands: dict = field(default_factory=dict)
    """Additional demands from X-Additional-Demands header (JSON).

    May contain: hostname, project_dir, executor_profile, tags
    """

    def get_hostname(self) -> Optional[str]:
        """Get hostname from additional demands."""
        return self.additional_demands.get("hostname")

    def get_project_dir(self) -> Optional[str]:
        """Get project_dir from additional demands."""
        return self.additional_demands.get("project_dir")

    def get_executor_profile(self) -> Optional[str]:
        """Get executor_profile from additional demands."""
        return self.additional_demands.get("executor_profile")

    def get_runner_tags(self) -> Optional[list[str]]:
        """Get runner tags from additional demands."""
        return self.additional_demands.get("tags")
