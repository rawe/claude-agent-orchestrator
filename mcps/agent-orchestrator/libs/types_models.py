"""
Type definitions for Agent Orchestrator MCP Server
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
    """Information about an agent session"""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(description="Session ID")
    session_name: str = Field(description="Session name")
    status: str = Field(description="Session status")
    project_dir: Optional[str] = Field(default=None, description="Project directory path")
    agent_name: Optional[str] = Field(default=None, description="Agent blueprint name")
    parent_session_name: Optional[str] = Field(
        default=None, description="Parent session name for callbacks"
    )


class ServerConfig(BaseModel):
    """Server configuration"""

    api_url: str = Field(description="Agent Runtime API URL")
