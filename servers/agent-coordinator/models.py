from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, List, Literal, Union


# ==============================================================================
# Stream Event Types (SSE broadcasts)
# ==============================================================================

class StreamEventType(str, Enum):
    """
    Event types for real-time streaming via Server-Sent Events (SSE).

    These are the event types sent to connected clients for real-time updates
    via the /sse/sessions endpoint.

    See ADR-013 for SSE migration details.
    """
    INIT = "init"                       # Initial state on connect
    SESSION_CREATED = "session_created" # New session created
    SESSION_UPDATED = "session_updated" # Session state changed
    SESSION_DELETED = "session_deleted" # Session removed
    EVENT = "event"                     # Session event (tool call, message, etc.)
    RUN_FAILED = "run_failed"           # Run timeout or failure

    @property
    def abbrev(self) -> str:
        """Get 3-letter abbreviation for SSE event IDs."""
        return _STREAM_EVENT_ABBREV[self]


# Abbreviations for SSE event IDs (used in Last-Event-ID for resume)
_STREAM_EVENT_ABBREV = {
    StreamEventType.INIT: "ini",
    StreamEventType.SESSION_CREATED: "scr",
    StreamEventType.SESSION_UPDATED: "sup",
    StreamEventType.SESSION_DELETED: "sdl",
    StreamEventType.EVENT: "evt",
    StreamEventType.RUN_FAILED: "rfl",
}


# ==============================================================================
# Session Event Types (events within a session)
# ==============================================================================

class SessionEventType(str, Enum):
    """
    Event types that occur within an agent session.

    These are logged in the events table and represent the lifecycle
    and activities of an agent session (specifically, of runs within a session).
    """
    RUN_START = "run_start"          # Run execution started
    RUN_COMPLETED = "run_completed"  # Run execution completed

    PRE_TOOL = "pre_tool"            # Before tool execution
    POST_TOOL = "post_tool"          # After tool execution
    MESSAGE = "message"              # Assistant or user message
    RESULT = "result"                # Session result (structured output)


# ==============================================================================
# Agent Models (from agent-registry)
# ==============================================================================

# Agent type: autonomous agents interpret intent, procedural agents follow defined procedures
AgentType = Literal["autonomous", "procedural"]


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

    type: AgentType = "autonomous"
    parameters_schema: Optional[dict] = None  # JSON Schema for parameters validation
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    capabilities: Optional[list[str]] = None
    demands: Optional["RunnerDemands"] = None


class AgentUpdate(BaseModel):
    """Request body for updating an agent (partial)."""

    type: Optional[AgentType] = None
    parameters_schema: Optional[dict] = None  # JSON Schema for parameters validation
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    capabilities: Optional[list[str]] = None
    demands: Optional["RunnerDemands"] = None


class Agent(AgentBase):
    """Full agent representation."""

    type: AgentType = "autonomous"
    parameters_schema: Optional[dict] = None  # JSON Schema for parameters validation
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    tags: list[str] = []
    capabilities: list[str] = []
    demands: Optional["RunnerDemands"] = None
    status: Literal["active", "inactive"] = "active"
    created_at: str
    modified_at: str


class AgentStatusUpdate(BaseModel):
    """Request body for status update."""

    status: Literal["active", "inactive"]


# ==============================================================================
# Capability Models (Capabilities System)
# ==============================================================================

class CapabilityBase(BaseModel):
    """Base capability fields."""

    name: str
    description: str


class CapabilityCreate(CapabilityBase):
    """Request body for creating a capability."""

    text: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None


class CapabilityUpdate(BaseModel):
    """Request body for updating a capability (partial)."""

    description: Optional[str] = None
    text: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None


class Capability(CapabilityBase):
    """Full capability representation."""

    text: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    created_at: str
    modified_at: str


class CapabilitySummary(CapabilityBase):
    """Summary capability for list endpoint (without full text content)."""

    has_text: bool
    has_mcp: bool
    mcp_server_names: list[str]
    created_at: str
    modified_at: str


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
    executor_profile: Optional[str] = None
    # Capability demands (must have ALL)
    tags: List[str] = []

    def is_empty(self) -> bool:
        """Check if no demands are specified."""
        return (
            self.hostname is None
            and self.project_dir is None
            and self.executor_profile is None
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
            executor_profile=blueprint.executor_profile or additional.executor_profile,
            # Tags are always additive (union)
            tags=list(set(blueprint.tags) | set(additional.tags)),
        )


# ==============================================================================
# Execution Mode (ADR-003)
# ==============================================================================

class ExecutionMode(str, Enum):
    """
    Execution mode for agent sessions.

    Controls how the parent session interacts with child sessions:
    - SYNC: Parent waits for child to complete, receives result directly
    - ASYNC_POLL: Parent continues immediately, polls for child status/result
    - ASYNC_CALLBACK: Parent continues immediately, coordinator auto-resumes parent

    See ADR-003 for details.
    """
    SYNC = "sync"
    ASYNC_POLL = "async_poll"
    ASYNC_CALLBACK = "async_callback"


# ==============================================================================
# Session Models (ADR-010)
# ==============================================================================

class SessionCreate(BaseModel):
    """Model for creating a new session.

    session_id is coordinator-generated at run creation.
    No session_name - that concept is removed per ADR-010.

    Note: execution_mode is stored on runs, not sessions.
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
    executor_profile: str
    project_dir: Optional[str] = None


class SessionMetadataUpdate(BaseModel):
    """Model for updating session metadata"""
    project_dir: Optional[str] = None
    agent_name: Optional[str] = None
    last_resumed_at: Optional[str] = None
    executor_session_id: Optional[str] = None
    executor_profile: Optional[str] = None
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
    event_type: str  # 'run_start' | 'pre_tool' | 'post_tool' | 'run_completed' | 'message' | 'result'
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
    # Result fields (for event_type='result')
    result_text: Optional[str] = None  # Human-readable result text
    result_data: Optional[dict] = None  # Structured JSON output (for deterministic agents)


class SessionResult(BaseModel):
    """Structured result from a session.

    Returned by GET /sessions/{session_id}/result endpoint.
    - result_text: Human-readable output (always present for completed sessions)
    - result_data: Structured JSON output (present for deterministic agents, null for AI agents)
    """
    result_text: Optional[str] = None
    result_data: Optional[dict] = None
