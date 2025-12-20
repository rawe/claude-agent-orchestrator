"""
Type definitions for Agent Orchestrator MCP Server

Note: Uses session_id (coordinator-generated) per ADR-010.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ResponseFormat(str, Enum):
    """Response format options"""

    MARKDOWN = "markdown"
    JSON = "json"


class AgentInfo(BaseModel):
    """Information about an agent blueprint"""

    name: str = Field(description="Agent name/identifier")
    description: str = Field(description="Agent capabilities description")
    status: str = Field(default="active", description="Agent status")


class SessionInfo(BaseModel):
    """Information about an agent session

    Uses session_id (coordinator-generated) per ADR-010.
    executor_session_id is the framework's ID (e.g., Claude SDK UUID).
    """

    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(description="Coordinator-generated session ID (ADR-010)")
    status: str = Field(description="Session status")
    project_dir: Optional[str] = Field(default=None, description="Project directory path")
    agent_name: Optional[str] = Field(default=None, description="Agent blueprint name")
    parent_session_id: Optional[str] = Field(
        default=None, description="Parent session ID for callbacks"
    )
    executor_session_id: Optional[str] = Field(
        default=None, description="Framework's session ID (e.g., Claude SDK UUID)"
    )
    executor_type: Optional[str] = Field(
        default=None, description="Executor type (e.g., 'claude-code')"
    )
    hostname: Optional[str] = Field(
        default=None, description="Machine where session runs"
    )


class ServerConfig(BaseModel):
    """Server configuration"""

    api_url: str = Field(description="Agent Coordinator API URL")
