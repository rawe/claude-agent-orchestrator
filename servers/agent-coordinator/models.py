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
    output_schema: Optional[dict] = None  # JSON Schema for output validation
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    capabilities: Optional[list[str]] = None
    demands: Optional["RunnerDemands"] = None
    hooks: Optional["AgentHooks"] = None  # Lifecycle hooks


class AgentUpdate(BaseModel):
    """Request body for updating an agent (partial)."""

    type: Optional[AgentType] = None
    parameters_schema: Optional[dict] = None  # JSON Schema for parameters validation
    output_schema: Optional[dict] = None  # JSON Schema for output validation
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    capabilities: Optional[list[str]] = None
    demands: Optional["RunnerDemands"] = None
    hooks: Optional["AgentHooks"] = None  # Lifecycle hooks


class Agent(AgentBase):
    """Full agent representation."""

    type: AgentType = "autonomous"
    parameters_schema: Optional[dict] = None  # JSON Schema for parameters validation
    output_schema: Optional[dict] = None  # JSON Schema for output validation
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    tags: list[str] = []
    capabilities: list[str] = []
    demands: Optional["RunnerDemands"] = None
    hooks: Optional["AgentHooks"] = None  # Lifecycle hooks
    status: Literal["active", "inactive"] = "active"
    created_at: str
    modified_at: str
    # Runner-owned agent fields (Phase 4 - Procedural Executor)
    command: Optional[str] = None  # CLI command for procedural agents
    runner_id: Optional[str] = None  # Runner that owns this agent (None = file-based)


class AgentStatusUpdate(BaseModel):
    """Request body for status update."""

    status: Literal["active", "inactive"]


# ==============================================================================
# Agent Hook Models (Agent Run Hooks)
# ==============================================================================

class HookOnError(str, Enum):
    """Behavior when a hook fails or times out."""
    BLOCK = "block"      # Block the run from executing
    CONTINUE = "continue"  # Continue with the run despite hook failure


class HookAgentConfig(BaseModel):
    """Configuration for an agent-type hook."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["agent"] = "agent"
    agent_name: str  # Name of the agent to execute as hook
    on_error: HookOnError = HookOnError.CONTINUE  # Default: continue on error
    timeout_seconds: int = 300  # Default: 5 minutes


# Union type for future extensibility (e.g., webhook hooks, script hooks)
HookConfig = HookAgentConfig


class AgentHooks(BaseModel):
    """Lifecycle hooks for an agent."""

    model_config = ConfigDict(extra="forbid")

    on_run_start: Optional[HookConfig] = None  # Execute synchronously when run is claimed
    on_run_finish: Optional[HookConfig] = None  # Execute fire-and-forget when run completes


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
    executor_type: Optional[str] = None  # Must match: "autonomous" | "procedural"
    # Capability demands (must have ALL)
    tags: List[str] = []

    def is_empty(self) -> bool:
        """Check if no demands are specified."""
        return (
            self.hostname is None
            and self.project_dir is None
            and self.executor_profile is None
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
            executor_profile=blueprint.executor_profile or additional.executor_profile,
            executor_type=blueprint.executor_type or additional.executor_type,
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
    # Result fields (for event_type='result') - mutually exclusive
    result_text: Optional[str] = None  # Free-form text (autonomous agents without output_schema)
    result_data: Optional[dict] = None  # Validated JSON (procedural agents or autonomous with output_schema)


class SessionResult(BaseModel):
    """Structured result from a session.

    Returned by GET /sessions/{session_id}/result endpoint.

    Fields are mutually exclusive based on agent configuration:
    - result_text: Free-form text output (autonomous agents without output_schema)
    - result_data: Validated JSON output (procedural agents, or autonomous agents with output_schema)

    Consumers should check which field is non-null to determine the result type.
    """
    result_text: Optional[str] = None
    result_data: Optional[dict] = None


# ==============================================================================
# Runner Agent Models (Phase 4 - Procedural Executor)
# ==============================================================================

class RunnerAgent(BaseModel):
    """Agent registered by a runner.

    Runner-owned agents are procedural agents bundled with the runner.
    They are deleted when the runner deregisters.
    """
    name: str
    description: Optional[str] = None
    command: str  # CLI command to execute (e.g., "scripts/echo/echo")
    parameters_schema: Optional[dict] = None  # JSON Schema for parameters validation
    output_schema: Optional[dict] = None  # JSON Schema for output validation
