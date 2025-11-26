"""
Pydantic models for Agent Manager API.
"""

from typing import Literal, Optional

from pydantic import BaseModel


class MCPServerConfig(BaseModel):
    """MCP server configuration."""

    command: str
    args: list[str]
    env: Optional[dict[str, str]] = None


class AgentBase(BaseModel):
    """Base agent fields."""

    name: str
    description: str


class AgentCreate(AgentBase):
    """Request body for creating an agent."""

    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None


class AgentUpdate(BaseModel):
    """Request body for updating an agent (partial)."""

    description: Optional[str] = None
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None


class Agent(AgentBase):
    """Full agent representation."""

    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    status: Literal["active", "inactive"] = "active"
    created_at: str
    modified_at: str


class AgentStatusUpdate(BaseModel):
    """Request body for status update."""

    status: Literal["active", "inactive"]
