from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, List, Literal, Union


# ==============================================================================
# Agent Models (from agent-registry)
# ==============================================================================

class MCPServerStdio(BaseModel):
    """MCP server configuration for stdio transport (command-based)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["stdio"] = "stdio"
    command: str
    args: list[str]
    env: Optional[dict[str, str]] = None


class MCPServerHttp(BaseModel):
    """MCP server configuration for HTTP transport."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["http"]
    url: str
    headers: Optional[dict[str, str]] = None


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
    tags: Optional[list[str]] = None
    demands: Optional["RunnerDemands"] = None


class AgentUpdate(BaseModel):
    """Request body for updating an agent (partial)."""

    description: Optional[str] = None
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    demands: Optional["RunnerDemands"] = None


class Agent(AgentBase):
    """Full agent representation."""

    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    tags: list[str] = []
    demands: Optional["RunnerDemands"] = None
    status: Literal["active", "inactive"] = "active"
    created_at: str
    modified_at: str


class AgentStatusUpdate(BaseModel):
    """Request body for status update."""

    status: Literal["active", "inactive"]


# ==============================================================================
# Runner Demands Models (ADR-011)
# ==============================================================================

class RunnerDemands(BaseModel):
    """
    Demands that a run requires from a runner.

    Property demands require exact match if specified.
    Tag demands require runner to have ALL specified tags.

    See ADR-011 for details.
    """
    # Property demands (exact match required if specified)
    hostname: Optional[str] = None
    project_dir: Optional[str] = None
    executor_type: Optional[str] = None
    # Capability demands (must have ALL)
    tags: List[str] = []

    def is_empty(self) -> bool:
        """Check if no demands are specified."""
        return (
            self.hostname is None
            and self.project_dir is None
            and self.executor_type is None
            and len(self.tags) == 0
        )

    @staticmethod
    def merge(
        blueprint: "RunnerDemands",
        additional: "RunnerDemands"
    ) -> "RunnerDemands":
        """
        Merge demands additively.

        Blueprint demands take precedence (cannot be overridden).
        Additional demands can only ADD constraints, never relax or override.
        Tags are always merged (union).
        """
        return RunnerDemands(
            # Blueprint wins if set, otherwise use additional
            hostname=blueprint.hostname or additional.hostname,
            project_dir=blueprint.project_dir or additional.project_dir,
            executor_type=blueprint.executor_type or additional.executor_type,
            # Tags are always additive (union)
            tags=list(set(blueprint.tags) | set(additional.tags)),
        )


# ==============================================================================
# Session Models (ADR-010)
# ==============================================================================

class SessionCreate(BaseModel):
    """Model for creating a new session.

    session_id is coordinator-generated at run creation.
    No session_name - that concept is removed per ADR-010.
    """
    session_id: str
    project_dir: Optional[str] = None
    agent_name: Optional[str] = None
    parent_session_id: Optional[str] = None


class SessionBind(BaseModel):
    """Model for binding executor information to a session.

    Called by executor after framework session starts.
    See ADR-010 for details.
    """
    executor_session_id: str
    hostname: str
    executor_type: str
    project_dir: Optional[str] = None


class SessionMetadataUpdate(BaseModel):
    """Model for updating session metadata"""
    project_dir: Optional[str] = None
    agent_name: Optional[str] = None
    last_resumed_at: Optional[str] = None
    executor_session_id: Optional[str] = None
    executor_type: Optional[str] = None
    hostname: Optional[str] = None


class MessageContent(BaseModel):
    """Content block within a message"""
    type: str  # 'text' (only text supported for now)
    text: str


class Event(BaseModel):
    """Event model for hook data.

    session_id is the coordinator-generated ID.
    executor_session_id is the framework's ID (optional, for correlation).
    """
    event_type: str  # 'session_start' | 'pre_tool' | 'post_tool' | 'session_stop' | 'message'
    session_id: str
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
