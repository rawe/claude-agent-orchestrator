"""
OpenAPI configuration for Agent Coordinator API.

This module defines:
- API metadata (title, description, version, etc.)
- Tags for endpoint grouping
- Security scheme documentation
- Custom response models for consistent API responses

FastAPI automatically generates OpenAPI spec from:
- Pydantic models (request/response bodies)
- Route decorators (paths, methods, status codes)
- Docstrings (operation descriptions)
- Type hints (parameter types)

Access the API documentation at:
- /docs - Swagger UI (interactive)
- /redoc - ReDoc (readable documentation)
- /openapi.json - Raw OpenAPI specification
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from enum import Enum


# ==============================================================================
# API Metadata
# ==============================================================================

API_TITLE = "Agent Coordinator API"
API_DESCRIPTION = """
## Agent Coordinator

Unified service for agent session management, agent blueprint registry, and capability management.

### Key Features

- **Session Management**: Create, monitor, and control agent sessions
- **Run Queue**: Queue agent runs and match them to runners based on demands
- **Agent Registry**: Manage agent blueprints with system prompts and MCP servers
- **Capability System**: Reusable components that can be attached to agents
- **Runner Management**: Register and coordinate agent runners
- **Real-time Updates**: Server-Sent Events (SSE) for live session monitoring

### Authentication

All endpoints require API key authentication via the `X-API-Key` header (when AUTH_ENABLED=true).

### Architecture

See the Architecture Decision Records (ADRs) in the repository for detailed design documentation:
- ADR-003: Execution Modes (sync/async)
- ADR-010: Session Identity and Executor Abstraction
- ADR-011: Runner Capabilities and Run Demands
- ADR-012: Runner Lifecycle Management
- ADR-013: WebSocket to SSE Migration
"""

API_VERSION = "0.5.0"

API_CONTACT = {
    "name": "Agent Orchestrator",
    "url": "https://github.com/your-org/agent-orchestrator",
}

API_LICENSE = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}


# ==============================================================================
# OpenAPI Tags (for endpoint grouping)
# ==============================================================================

OPENAPI_TAGS = [
    {
        "name": "Sessions",
        "description": "Session lifecycle management - create, query, stop, and delete agent sessions.",
    },
    {
        "name": "SSE",
        "description": "Server-Sent Events for real-time session updates.",
    },
    {
        "name": "Runs",
        "description": "Run queue management - create runs, query status, and stop runs.",
    },
    {
        "name": "Runners",
        "description": "Runner registration and management - runners poll for work and report status.",
    },
    {
        "name": "Agents",
        "description": "Agent blueprint registry - manage agent configurations with system prompts and MCP servers.",
    },
    {
        "name": "Capabilities",
        "description": "Capability management - reusable components (text, MCP servers) that can be attached to agents.",
    },
    {
        "name": "Scripts",
        "description": "Script management - executable scripts that procedural agents reference for execution.",
    },
    {
        "name": "MCP Registry",
        "description": "MCP Server Registry - centralized management of MCP server definitions referenced by agents and capabilities.",
    },
    {
        "name": "Health",
        "description": "Service health checks.",
    },
    {
        "name": "Config",
        "description": "Configuration management - export and import agent blueprints and capabilities.",
    },
    {
        "name": "Events (Legacy)",
        "description": "Legacy event reception endpoint. Prefer using `/sessions/{session_id}/events` for new integrations.",
    },
]


# ==============================================================================
# Security Scheme
# ==============================================================================

# Security scheme for OpenAPI documentation
# Note: Actual authentication is handled by auth.py
SECURITY_SCHEMES = {
    "ApiKeyAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key for authentication. Required when AUTH_ENABLED=true.",
    }
}


# ==============================================================================
# Common Response Models
# ==============================================================================

class OkResponse(BaseModel):
    """Standard success response."""
    ok: bool = Field(default=True, description="Indicates success")


class ErrorDetail(BaseModel):
    """Error detail model."""
    detail: str = Field(..., description="Error message")


class SessionResponse(BaseModel):
    """Response containing a single session."""
    session_id: str = Field(..., description="Coordinator-generated session ID")
    status: str = Field(..., description="Session status (pending, running, stopping, stopped, finished)")
    created_at: str = Field(..., description="ISO timestamp of session creation")
    project_dir: Optional[str] = Field(None, description="Project directory path")
    agent_name: Optional[str] = Field(None, description="Agent blueprint name")
    parent_session_id: Optional[str] = Field(None, description="Parent session ID for hierarchical orchestration")
    executor_session_id: Optional[str] = Field(None, description="Framework's session ID after binding")
    executor_profile: Optional[str] = Field(None, description="Executor profile name")
    hostname: Optional[str] = Field(None, description="Host where session is running")
    last_resumed_at: Optional[str] = Field(None, description="ISO timestamp of last resume")


class SessionListResponse(BaseModel):
    """Response containing a list of sessions."""
    sessions: List[SessionResponse] = Field(..., description="List of sessions")


class SessionCreateResponse(BaseModel):
    """Response after creating a session."""
    session_id: str = Field(..., description="Coordinator-generated session ID")
    status: str = Field(default="pending", description="Initial session status")


class SessionAffinityInfo(BaseModel):
    """Session affinity information for resume routing."""
    session_id: str
    hostname: Optional[str] = None
    project_dir: Optional[str] = None
    executor_profile: Optional[str] = None


class SessionAffinityResponse(BaseModel):
    """Response containing session affinity information."""
    affinity: SessionAffinityInfo


class SessionResultResponse(BaseModel):
    """Response containing session result data."""
    session_id: str
    result: Optional[Any] = Field(None, description="Session result (from callback or completion)")
    status: str


class SessionStatusResponse(BaseModel):
    """Quick status check response."""
    status: str = Field(..., description="Session status (running, finished, not_existent)")


class SessionDeleteResponse(BaseModel):
    """Response after deleting a session."""
    session_id: str
    runs_deleted: int = Field(..., description="Number of runs deleted with the session")


class EventListResponse(BaseModel):
    """Response containing a list of events."""
    events: List[dict] = Field(..., description="List of session events")


# ==============================================================================
# Run Response Models
# ==============================================================================

class RunStatus(str, Enum):
    """Run status enum."""
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class RunResponse(BaseModel):
    """Response containing run details."""
    run_id: str = Field(..., description="Unique run identifier")
    type: str = Field(..., description="Run type (start_session, resume_session)")
    session_id: str = Field(..., description="Associated session ID")
    agent_name: Optional[str] = Field(None, description="Agent blueprint name")
    parameters: dict = Field(..., description="Input parameters for the run")
    status: str = Field(..., description="Run status")
    project_dir: Optional[str] = None
    parent_session_id: Optional[str] = None
    execution_mode: str = Field(default="sync")
    demands: Optional[dict] = Field(None, description="Runner demands (merged from blueprint + additional)")
    runner_id: Optional[str] = Field(None, description="ID of runner that claimed this run")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: str
    claimed_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    timeout_at: Optional[str] = Field(None, description="When demand matching times out")


class RunCreateResponse(BaseModel):
    """Response after creating a run."""
    run_id: str
    session_id: str
    status: str = Field(default="pending")


class RunListResponse(BaseModel):
    """Response containing a list of runs."""
    runs: List[RunResponse]


# ==============================================================================
# Runner Response Models
# ==============================================================================

class RunnerRegisterResponse(BaseModel):
    """Response after runner registration."""
    runner_id: str = Field(..., description="Assigned runner ID")
    poll_endpoint: str = Field(..., description="Endpoint for polling runs")
    poll_timeout_seconds: int = Field(..., description="Long-poll timeout")
    heartbeat_interval_seconds: int = Field(..., description="Heartbeat interval")


class RunnerStatus(str, Enum):
    """Runner status enum."""
    ACTIVE = "active"
    STALE = "stale"


class RunnerInfoResponse(BaseModel):
    """Runner information with status."""
    runner_id: str
    hostname: str
    project_dir: str
    executor_profile: str
    executor: Optional[dict] = None
    tags: List[str] = []
    require_matching_tags: bool = False
    status: str
    registered_at: str
    last_heartbeat_at: str


class RunnerListResponse(BaseModel):
    """Response containing a list of runners."""
    runners: List[RunnerInfoResponse]


class RunnerPollResponse(BaseModel):
    """Response from runner poll endpoint."""
    run: Optional[RunResponse] = Field(None, description="Run to execute (null if none available)")
    stop_session_ids: List[str] = Field(default=[], description="Sessions to stop")


# ==============================================================================
# Health Response Model
# ==============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy", description="Service health status")


# ==============================================================================
# Config Response Models
# ==============================================================================

class ConfigImportResponse(BaseModel):
    """Response after importing configuration."""
    message: str = Field(..., description="Success message")
    agents_imported: int = Field(..., description="Number of agents imported")
    capabilities_imported: int = Field(..., description="Number of capabilities imported")
    agents_replaced: int = Field(..., description="Number of agents that were replaced")
    capabilities_replaced: int = Field(..., description="Number of capabilities that were replaced")
