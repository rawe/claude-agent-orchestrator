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


# Note: MCPServerRef is added after its definition at the end of this file
# This union allows both legacy inline format and new ref-based format
MCPServerConfig = Union[MCPServerStdio, MCPServerHttp]


class AgentBase(BaseModel):
    """Base agent fields."""

    name: str
    description: str


class AgentCreate(AgentBase):
    """Request body for creating an agent."""

    type: AgentType = "autonomous"
    script: Optional[str] = None  # Script reference for procedural agents
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
    script: Optional[str] = None  # Script reference for procedural agents
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
    """Full agent representation.

    Procedural Agent Ownership (mutually exclusive):
    - Coordinator-owned: `script` is set, `command` and `runner_id` are null
    - Runner-owned: `command` and `runner_id` are set, `script` is null

    The `script` and `command` fields MUST NOT both be set. This is the
    differentiation criteria used by the Procedural Executor to determine
    execution mode. See design doc: phase-1-scripts-and-procedural-agents.md
    """

    type: AgentType = "autonomous"
    # Coordinator-owned procedural agent: references a centrally managed script
    script: Optional[str] = None
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
    # Runner-owned procedural agent: command executed relative to executor directory
    command: Optional[str] = None
    runner_id: Optional[str] = None  # Non-null indicates runner ownership


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

class CapabilityType(str, Enum):
    """
    Type of capability - determines which fields are allowed.

    - script: Local script execution (script field allowed, mcp_servers forbidden)
    - mcp: MCP server integration (mcp_servers field allowed, script forbidden)
    - text: Instructions only (both script and mcp_servers forbidden)

    The text field is always allowed for additional instructions.
    """
    SCRIPT = "script"
    MCP = "mcp"
    TEXT = "text"


class CapabilityBase(BaseModel):
    """Base capability fields."""

    name: str
    description: str


class CapabilityCreate(CapabilityBase):
    """Request body for creating a capability."""

    type: CapabilityType = CapabilityType.TEXT
    script: Optional[str] = None  # Allowed when type=script
    text: Optional[str] = None  # Always allowed
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None  # Allowed when type=mcp


class CapabilityUpdate(BaseModel):
    """Request body for updating a capability (partial)."""

    description: Optional[str] = None
    type: Optional[CapabilityType] = None
    script: Optional[str] = None  # Allowed when type=script
    text: Optional[str] = None  # Always allowed
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None  # Allowed when type=mcp


class Capability(CapabilityBase):
    """Full capability representation."""

    type: CapabilityType = CapabilityType.TEXT
    script: Optional[str] = None  # Allowed when type=script
    text: Optional[str] = None  # Always allowed
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None  # Allowed when type=mcp
    created_at: str
    modified_at: str


class CapabilitySummary(CapabilityBase):
    """Summary capability for list endpoint (without full text content)."""

    type: CapabilityType
    has_script: bool
    script_name: Optional[str]
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


# ==============================================================================
# Script Models (Centralized Script Management)
# ==============================================================================

class ScriptBase(BaseModel):
    """Base script fields."""

    name: str
    description: str


class ScriptCreate(ScriptBase):
    """Request body for creating a script."""

    script_file: str  # Filename of the script (e.g., "send-notification.py")
    script_content: str  # Content of the script file
    parameters_schema: Optional[dict] = None  # JSON Schema for parameters validation
    demands: Optional[RunnerDemands] = None  # Execution requirements (e.g., tags: ["uv"])


class ScriptUpdate(BaseModel):
    """Request body for updating a script (partial)."""

    description: Optional[str] = None
    script_file: Optional[str] = None  # New filename if changed
    script_content: Optional[str] = None  # New content if changed
    parameters_schema: Optional[dict] = None  # JSON Schema for parameters validation
    demands: Optional[RunnerDemands] = None  # Execution requirements


class Script(ScriptBase):
    """Full script representation."""

    script_file: str  # Filename of the script
    script_content: str  # Content of the script file
    parameters_schema: Optional[dict] = None  # JSON Schema for parameters validation
    demands: Optional[RunnerDemands] = None  # Execution requirements
    created_at: str
    modified_at: str


class ScriptSummary(ScriptBase):
    """Summary script for list endpoint (without script content)."""

    script_file: str
    has_parameters_schema: bool
    has_demands: bool
    demand_tags: list[str]  # Quick access to demand tags
    created_at: str
    modified_at: str


# ==============================================================================
# MCP Server Registry Models (Phase 2: mcp-server-registry.md)
# ==============================================================================

class ConfigSchemaField(BaseModel):
    """Schema definition for a single config field."""

    model_config = ConfigDict(extra="forbid")

    type: str = "string"  # string, integer, boolean
    description: Optional[str] = None
    required: bool = False
    sensitive: bool = False  # If true, value should be masked in logs/UI
    default: Optional[Any] = None


class MCPServerConfigSchema(BaseModel):
    """Schema for MCP server configuration values."""

    model_config = ConfigDict(extra="forbid")

    fields: dict[str, ConfigSchemaField] = {}


class MCPServerRegistryEntry(BaseModel):
    """Full MCP server registry entry."""

    id: str
    name: str
    description: Optional[str] = None
    url: str
    config_schema: Optional[MCPServerConfigSchema] = None
    default_config: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class MCPServerRegistryCreate(BaseModel):
    """Request body for creating an MCP server registry entry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: Optional[str] = None
    url: str
    config_schema: Optional[MCPServerConfigSchema] = None
    default_config: Optional[dict[str, Any]] = None


class MCPServerRegistryUpdate(BaseModel):
    """Request body for updating an MCP server registry entry (partial)."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    config_schema: Optional[MCPServerConfigSchema] = None
    default_config: Optional[dict[str, Any]] = None


class MCPServerRef(BaseModel):
    """Reference to an MCP server in the registry.

    Used in agent/capability mcp_servers config instead of inline type/url.
    """

    model_config = ConfigDict(extra="forbid")

    ref: str  # Registry entry ID
    config: Optional[dict[str, Any]] = None  # Config values to merge with defaults
