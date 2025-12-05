from pydantic import BaseModel
from typing import Optional, Any, List, Literal, Union


# ==============================================================================
# Agent Models (from agent-registry)
# ==============================================================================

class MCPServerStdio(BaseModel):
    """MCP server configuration for stdio transport (command-based)."""

    type: Literal["stdio"] = "stdio"
    command: str
    args: list[str]
    env: Optional[dict[str, str]] = None


class MCPServerHttp(BaseModel):
    """MCP server configuration for HTTP transport."""

    type: Literal["http"]
    url: str


MCPServerConfig = Union[MCPServerStdio, MCPServerHttp]


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


# ==============================================================================
# Session Models
# ==============================================================================

class SessionMetadataUpdate(BaseModel):
    """Model for updating session metadata"""
    session_name: Optional[str] = None
    project_dir: Optional[str] = None
    agent_name: Optional[str] = None
    last_resumed_at: Optional[str] = None


class SessionCreate(BaseModel):
    """Model for creating a new session"""
    session_id: str
    session_name: str
    project_dir: Optional[str] = None
    agent_name: Optional[str] = None

class MessageContent(BaseModel):
    """Content block within a message"""
    type: str  # 'text' (only text supported for now)
    text: str

class Event(BaseModel):
    """Event model for hook data"""
    event_type: str  # 'session_start' | 'pre_tool' | 'post_tool' | 'session_stop' | 'message'
    session_id: str
    session_name: str
    timestamp: str
    # Tool-related fields (pre_tool and post_tool)
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[Any] = None
    error: Optional[str] = None
    # Session stop fields
    exit_code: Optional[int] = None
    reason: Optional[str] = None
    # Message fields
    role: Optional[str] = None  # 'assistant' | 'user'
    content: Optional[List[dict]] = None  # Array of content blocks
