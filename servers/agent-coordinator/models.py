import re
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Any, List, Literal, Union


# ==============================================================================
# Validators
# ==============================================================================

SESSION_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
SESSION_NAME_MAX_LENGTH = 60


def validate_session_name(name: str) -> str:
    """
    Validate session name format.

    Rules:
    - Not empty
    - Max 60 characters
    - Only alphanumeric, dash, underscore: ^[a-zA-Z0-9_-]+$

    Returns the validated name or raises ValueError.
    """
    if not name:
        raise ValueError("Session name cannot be empty")

    if len(name) > SESSION_NAME_MAX_LENGTH:
        raise ValueError(
            f"Session name too long (max {SESSION_NAME_MAX_LENGTH} characters, got {len(name)})"
        )

    if not SESSION_NAME_PATTERN.match(name):
        raise ValueError(
            "Session name can only contain alphanumeric characters, dashes, and underscores"
        )

    return name


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
    parent_session_name: Optional[str] = None

    @field_validator("session_name")
    @classmethod
    def check_session_name(cls, v: str) -> str:
        return validate_session_name(v)

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

    @field_validator("session_name")
    @classmethod
    def check_session_name(cls, v: str) -> str:
        return validate_session_name(v)
