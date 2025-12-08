# Implementation Guide: MCP Server API Refactor

## Context

This guide describes how to refactor the Agent Orchestrator MCP Server to directly interact with the Agent Runtime API instead of spawning subprocess commands (`ao-start`, `ao-resume`, etc.).

### Current Architecture (Subprocess-based)

```
MCP Server
    ↓ spawns subprocess
ao-start / ao-resume (Python commands)
    ↓ uses
Claude Agent SDK
    ↓ calls
Agent Runtime API (Sessions, Events)
```

The MCP server currently:
1. Spawns `ao-*` commands via `subprocess.Popen`
2. Passes parent session context via `AGENT_SESSION_NAME` environment variable
3. Parses stdout/stderr from commands
4. Handles async mode by spawning detached processes

### Target Architecture (API-based)

```
MCP Server
    ↓ HTTP calls
Agent Runtime API (Jobs API)
    ↓ polled by
Agent Launcher
    ↓ spawns
ao-start / ao-resume
    ↓ uses
Claude Agent SDK
```

The MCP server will:
1. Call `POST /jobs` to create jobs
2. Pass parent session context via `parent_session_name` field in job
3. Poll `GET /jobs/{job_id}` for synchronous operations
4. Return immediately for async operations

### Key Insight: Simplified Parent Session Propagation

**Problem**: Previously, `parent_session_name` had to flow through 5 layers:
```
MCP Server → (env var) → ao-start → claude_client → session_client → Sessions API
```

**Solution**: The Agent Runtime links Jobs to Sessions automatically:
1. MCP Server passes `parent_session_name` to Jobs API
2. Agent Runtime updates session's `parent_session_name` when job starts
3. ao-start/ao-resume don't need to know about parent sessions

This works for both new sessions AND resumes (where a different parent may resume).

---

## Prerequisites

Before implementing this guide, ensure:
- Agent Runtime API is running at `http://localhost:8765`
- Agent Launcher is running and registered with Runtime
- Understanding of the Jobs API flow (see `docs/ao-commands-api-reference.md`)

---

## Implementation Order

The changes must be made in this specific order to maintain a working system:

### Phase 1: Extend Jobs API (Agent Runtime)

**Files to modify:**
- `servers/agent-runtime/services/job_queue.py`
- `servers/agent-runtime/main.py`

**Changes:**

1. Add `parent_session_name` to `JobCreate` model:
```python
class JobCreate(BaseModel):
    """Request body for creating a new job."""
    type: JobType
    session_name: str
    agent_name: Optional[str] = None
    prompt: str
    project_dir: Optional[str] = None
    parent_session_name: Optional[str] = None  # NEW
```

2. Add `parent_session_name` to `Job` model:
```python
class Job(BaseModel):
    """A job in the queue."""
    job_id: str
    type: JobType
    session_name: str
    agent_name: Optional[str] = None
    prompt: str
    project_dir: Optional[str] = None
    parent_session_name: Optional[str] = None  # NEW
    status: JobStatus
    # ... rest of fields
```

3. Update `add_job()` to copy `parent_session_name`:
```python
def add_job(self, job_create: JobCreate) -> Job:
    job = Job(
        # ... existing fields
        parent_session_name=job_create.parent_session_name,  # NEW
        # ...
    )
```

**Verification:**
- `POST /jobs` accepts `parent_session_name`
- `GET /jobs/{job_id}` returns `parent_session_name`

---

### Phase 2: Link Jobs to Sessions (Agent Runtime + Launcher)

**Files to modify:**
- `servers/agent-runtime/main.py`
- `servers/agent-runtime/services/job_queue.py`
- `servers/agent-runtime/database.py`
- `servers/agent-launcher/lib/executor.py`

**Changes:**

1. Update the `POST /launcher/jobs/{job_id}/started` endpoint to set `parent_session_name` on the session:

```python
@app.post("/launcher/jobs/{job_id}/started")
async def report_job_started(job_id: str, request: JobStartedRequest):
    """Report that a job has started executing."""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update job status
    job_queue.update_job_status(job_id, JobStatus.RUNNING, started_at=now)

    # NEW: Update session's parent_session_name if job has one
    if job.parent_session_name:
        session = get_session_by_name(job.session_name)
        if session:
            # Session exists (resume case) - update parent
            update_session_parent(session["session_id"], job.parent_session_name)
        else:
            # Session doesn't exist yet (start case) - store for later
            # The POST /sessions endpoint will look this up
            pass

    return {"ok": True}
```

2. Update `POST /sessions` to look up pending job and copy `parent_session_name`:

```python
@app.post("/sessions")
async def create_session_endpoint(session: SessionCreate):
    """Create a new session with full metadata"""

    # NEW: Look up job by session_name to get parent_session_name
    parent_session_name = session.parent_session_name  # from request (if any)

    # Check if there's a running job for this session_name
    job = job_queue.get_job_by_session_name(session.session_name)
    if job and job.parent_session_name:
        parent_session_name = job.parent_session_name

    new_session = create_session(
        session_id=session.session_id,
        session_name=session.session_name,
        timestamp=timestamp,
        project_dir=session.project_dir,
        agent_name=session.agent_name,
        parent_session_name=parent_session_name,  # Use job's parent if available
    )
    # ...
```

3. Add helper function to job_queue.py:

```python
def get_job_by_session_name(self, session_name: str) -> Optional[Job]:
    """Find a running or claimed job by session_name."""
    with self._lock:
        for job in self._jobs.values():
            if job.session_name == session_name and job.status in (JobStatus.CLAIMED, JobStatus.RUNNING):
                return job
    return None
```

4. Add helper to update session parent (database.py):

```python
def update_session_parent(session_id: str, parent_session_name: str) -> None:
    """Update the parent_session_name of a session."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE sessions SET parent_session_name = ? WHERE session_id = ?",
        (parent_session_name, session_id)
    )
    conn.commit()
    conn.close()
```

5. **Agent Launcher: Set `AGENT_SESSION_NAME` for session self-identification**

The Agent Launcher must set `AGENT_SESSION_NAME={session_name}` in the environment when spawning ao-start/ao-resume. This is critical for the HTTP callback flow:

```
Agent Launcher spawns ao-start with AGENT_SESSION_NAME=A
    ↓
ao-start runs Claude with MCP config containing ${AGENT_SESSION_NAME}
    ↓
_process_mcp_servers() replaces placeholder: X-Agent-Session-Name: A
    ↓
Claude calls MCP server with header X-Agent-Session-Name: A
    ↓
MCP server reads header, passes parent_session_name=A to Jobs API
```

Update `servers/agent-launcher/lib/executor.py`:

```python
def _execute_start_session(self, job: Job, parent_session_name: Optional[str] = None) -> subprocess.Popen:
    """Execute a start_session job via ao-start."""
    # ... build command ...

    # Build environment
    env = os.environ.copy()

    # Set AGENT_SESSION_NAME so the session knows its own identity
    # This allows MCP servers to include the session name in HTTP headers
    # for callback support (X-Agent-Session-Name header)
    env["AGENT_SESSION_NAME"] = job.session_name

    # ... spawn subprocess ...
```

Same change for `_execute_resume_session()`.

**Verification:**
- Start a job with `parent_session_name`
- Session gets `parent_session_name` automatically (check via `GET /sessions`)
- Resume job updates `parent_session_name` even if original was different
- ao-start/ao-resume receive `AGENT_SESSION_NAME` in environment

---

### Phase 3: Simplify ao-start/ao-resume (Optional Cleanup)

**Files to modify:**
- `servers/agent-launcher/claude-code/ao-start`
- `servers/agent-launcher/claude-code/ao-resume`
- `servers/agent-launcher/claude-code/lib/claude_client.py`
- `servers/agent-launcher/claude-code/lib/session_client.py`

**Changes:**

Once Phase 2 is verified working, remove `parent_session_name` handling from these commands since the Agent Runtime now handles it:

1. In `ao-start`: Remove reading `AGENT_SESSION_NAME` env var and passing to `run_session_sync()`
2. In `claude_client.py`: Remove `parent_session_name` parameter from functions
3. In `session_client.py`: Remove `parent_session_name` from `create_session()`

**Note:** This cleanup is optional. The old code path will still work (it just won't be used when jobs come from the API).

---

### Phase 4: Refactor MCP Server

**Files to modify:**
- `interfaces/agent-orchestrator-mcp-server/libs/core_functions.py`
- `interfaces/agent-orchestrator-mcp-server/libs/utils.py`
- `interfaces/agent-orchestrator-mcp-server/libs/constants.py`
- `interfaces/agent-orchestrator-mcp-server/libs/types_models.py`
- `interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py`

#### 4.1 Add API Client

Create a new file `libs/api_client.py`:

```python
"""
HTTP client for Agent Runtime API.
"""

import asyncio
from typing import Optional, List, Dict, Any
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import json


class APIError(Exception):
    """Base exception for API errors."""
    pass


class APIClient:
    """Async HTTP client for Agent Runtime API using only stdlib."""

    DEFAULT_TIMEOUT = 10.0
    DEFAULT_POLL_INTERVAL = 2.0
    DEFAULT_COMPLETION_TIMEOUT = 600.0  # 10 minutes

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        """Make HTTP request using urllib (stdlib)."""
        url = f"{self.base_url}{path}"

        headers = {"Content-Type": "application/json"}
        body = json.dumps(data).encode() if data else None

        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except HTTPError as e:
            error_body = e.read().decode() if e.fp else str(e)
            raise APIError(f"HTTP {e.code}: {error_body}")
        except URLError as e:
            raise APIError(f"Request failed: {e.reason}")

    # Jobs API

    def create_job(
        self,
        job_type: str,
        session_name: str,
        prompt: str,
        agent_name: Optional[str] = None,
        project_dir: Optional[str] = None,
        parent_session_name: Optional[str] = None,
    ) -> str:
        """Create a job. Returns job_id."""
        data = {
            "type": job_type,
            "session_name": session_name,
            "prompt": prompt,
        }
        if agent_name:
            data["agent_name"] = agent_name
        if project_dir:
            data["project_dir"] = project_dir
        if parent_session_name:
            data["parent_session_name"] = parent_session_name

        result = self._request("POST", "/jobs", data)
        return result["job_id"]

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        return self._request("GET", f"/jobs/{job_id}")

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_COMPLETION_TIMEOUT,
    ) -> Dict[str, Any]:
        """Poll job until completed or failed."""
        import time
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise APIError(f"Job {job_id} timed out after {timeout}s")

            job = self.get_job(job_id)
            status = job.get("status")

            if status == "completed":
                return job
            elif status == "failed":
                error = job.get("error", "Unknown error")
                raise APIError(f"Job failed: {error}")

            time.sleep(poll_interval)

    # Sessions API

    def get_session_by_name(self, session_name: str) -> Optional[Dict[str, Any]]:
        """Get session by name. Returns None if not found."""
        try:
            result = self._request("GET", f"/sessions/by-name/{session_name}")
            return result.get("session")
        except APIError as e:
            if "404" in str(e):
                return None
            raise

    def get_session_status(self, session_id: str) -> str:
        """Get session status."""
        result = self._request("GET", f"/sessions/{session_id}/status")
        return result.get("status", "not_existent")

    def get_session_result(self, session_id: str) -> str:
        """Get session result."""
        result = self._request("GET", f"/sessions/{session_id}/result")
        return result.get("result", "")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        result = self._request("GET", "/sessions")
        return result.get("sessions", [])

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            self._request("DELETE", f"/sessions/{session_id}")
            return True
        except APIError:
            return False

    # Agents API

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agent blueprints."""
        return self._request("GET", "/agents")

    def get_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get agent by name."""
        try:
            return self._request("GET", f"/agents/{agent_name}")
        except APIError as e:
            if "404" in str(e):
                return None
            raise
```

#### 4.2 Update Constants

Update `libs/constants.py`:

```python
"""
Constants for Agent Orchestrator MCP Server
"""

import os

# API Configuration
ENV_API_URL = "AGENT_ORCHESTRATOR_API_URL"
DEFAULT_API_URL = "http://127.0.0.1:8765"

def get_api_url() -> str:
    """Get Agent Runtime API URL."""
    return os.environ.get(ENV_API_URL, DEFAULT_API_URL)

# Session name constraints
MAX_SESSION_NAME_LENGTH = 60
SESSION_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"

# Character limit for responses
CHARACTER_LIMIT = 25000

# HTTP Header for parent session (in HTTP mode)
HEADER_AGENT_SESSION_NAME = "X-Agent-Session-Name"

# Environment variable for parent session (in stdio mode)
ENV_AGENT_SESSION_NAME = "AGENT_SESSION_NAME"
```

#### 4.3 Update Types/Models

Update `libs/types_models.py`:

```python
"""
Type definitions for Agent Orchestrator MCP Server
"""

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ResponseFormat(str, Enum):
    """Response format options"""
    MARKDOWN = "markdown"
    JSON = "json"


class AgentInfo(BaseModel):
    """Information about an agent blueprint"""
    name: str
    description: str
    status: str = "active"


class SessionInfo(BaseModel):
    """Information about an agent session"""
    model_config = ConfigDict(populate_by_name=True)

    session_id: str
    session_name: str
    status: str
    project_dir: Optional[str] = None
    agent_name: Optional[str] = None
    parent_session_name: Optional[str] = None


class ServerConfig(BaseModel):
    """Server configuration"""
    api_url: str
```

#### 4.4 Rewrite Core Functions

Rewrite `libs/core_functions.py` to use the API client:

```python
"""
Core functions for Agent Orchestrator MCP Server.

These functions implement the actual logic by calling the Agent Runtime API.
"""

import asyncio
import json
import os
from typing import Literal, Optional

from api_client import APIClient, APIError
from constants import (
    get_api_url,
    ENV_AGENT_SESSION_NAME,
    HEADER_AGENT_SESSION_NAME,
    CHARACTER_LIMIT,
)
from logger import logger
from types_models import ServerConfig, ResponseFormat


def get_api_client(config: ServerConfig) -> APIClient:
    """Get API client instance."""
    return APIClient(config.api_url)


def get_parent_session_name(http_headers: Optional[dict] = None) -> Optional[str]:
    """
    Get parent session name from environment or HTTP headers.

    - stdio mode: reads from AGENT_SESSION_NAME env var
    - HTTP mode: reads from X-Agent-Session-Name header
    """
    # Try HTTP header first (if provided)
    if http_headers:
        parent = http_headers.get(HEADER_AGENT_SESSION_NAME)
        if parent:
            return parent

    # Fall back to environment variable
    return os.environ.get(ENV_AGENT_SESSION_NAME)


def truncate_response(text: str) -> tuple[str, bool]:
    """Truncate response if it exceeds character limit."""
    if len(text) <= CHARACTER_LIMIT:
        return text, False

    truncated = text[:CHARACTER_LIMIT] + "\n\n[Response truncated due to length]"
    return truncated, True


async def list_agent_blueprints_impl(
    config: ServerConfig,
    response_format: Literal["markdown", "json"] = "markdown",
) -> str:
    """List all available agent blueprints."""
    logger.info("list_agent_blueprints called", {"response_format": response_format})

    try:
        client = get_api_client(config)
        agents = client.list_agents()

        # Filter to active agents only
        active_agents = [a for a in agents if a.get("status") == "active"]

        if response_format == "json":
            return json.dumps({
                "total": len(active_agents),
                "agents": [{"name": a["name"], "description": a.get("description", "")} for a in active_agents]
            }, indent=2)
        else:
            if not active_agents:
                return "No agent blueprints found"

            lines = ["# Available Agent Blueprints", ""]
            for agent in active_agents:
                lines.append(f"## {agent['name']}")
                lines.append(agent.get("description", "No description"))
                lines.append("")
            return "\n".join(lines)

    except APIError as e:
        return f"Error: {str(e)}"


async def list_agent_sessions_impl(
    config: ServerConfig,
    response_format: Literal["markdown", "json"] = "markdown",
) -> str:
    """List all agent sessions."""
    logger.info("list_agent_sessions called", {"response_format": response_format})

    try:
        client = get_api_client(config)
        sessions = client.list_sessions()

        if response_format == "json":
            return json.dumps({
                "total": len(sessions),
                "sessions": sessions
            }, indent=2)
        else:
            if not sessions:
                return "No sessions found"

            lines = ["# Agent Sessions", "", f"Found {len(sessions)} session(s)", ""]
            for s in sessions:
                lines.append(f"## {s.get('session_name', 'unknown')}")
                lines.append(f"- **Session ID**: {s.get('session_id', 'unknown')}")
                lines.append(f"- **Status**: {s.get('status', 'unknown')}")
                lines.append(f"- **Project Directory**: {s.get('project_dir', 'N/A')}")
                lines.append("")
            return "\n".join(lines)

    except APIError as e:
        return f"Error: {str(e)}"


async def start_agent_session_impl(
    config: ServerConfig,
    session_name: str,
    prompt: str,
    agent_blueprint_name: Optional[str] = None,
    project_dir: Optional[str] = None,
    async_mode: bool = False,
    callback: bool = False,
    http_headers: Optional[dict] = None,
) -> str:
    """Start a new agent session."""
    logger.info("start_agent_session called", {
        "session_name": session_name,
        "agent_blueprint_name": agent_blueprint_name,
        "async_mode": async_mode,
        "callback": callback,
    })

    try:
        client = get_api_client(config)

        # Get parent session name for callback support
        parent_session_name = None
        if callback:
            parent_session_name = get_parent_session_name(http_headers)
            if not parent_session_name:
                logger.warn("callback=true but no parent session name available")

        # Create job
        job_id = client.create_job(
            job_type="start_session",
            session_name=session_name,
            prompt=prompt,
            agent_name=agent_blueprint_name,
            project_dir=project_dir,
            parent_session_name=parent_session_name,
        )

        logger.info(f"Created job {job_id} for session {session_name}")

        if async_mode:
            # Return immediately
            response = {
                "session_name": session_name,
                "job_id": job_id,
                "status": "running",
                "message": "Agent started in background. Use get_agent_session_status to poll for completion.",
            }
            if callback and parent_session_name:
                response["callback_to"] = parent_session_name
            return json.dumps(response, indent=2)

        # Synchronous: wait for completion
        logger.info(f"Waiting for job {job_id} to complete...")
        job = client.wait_for_job(job_id)

        # Get result from session
        session = client.get_session_by_name(session_name)
        if not session:
            return f"Error: Session '{session_name}' not found after job completed"

        result = client.get_session_result(session["session_id"])
        text, truncated = truncate_response(result)
        if truncated:
            logger.warn("start_agent_session: response truncated")
        return text

    except APIError as e:
        logger.error("start_agent_session error", {"error": str(e)})
        return f"Error: {str(e)}"


async def resume_agent_session_impl(
    config: ServerConfig,
    session_name: str,
    prompt: str,
    async_mode: bool = False,
    callback: bool = False,
    http_headers: Optional[dict] = None,
) -> str:
    """Resume an existing agent session."""
    logger.info("resume_agent_session called", {
        "session_name": session_name,
        "async_mode": async_mode,
        "callback": callback,
    })

    try:
        client = get_api_client(config)

        # Get parent session name for callback support
        parent_session_name = None
        if callback:
            parent_session_name = get_parent_session_name(http_headers)
            if not parent_session_name:
                logger.warn("callback=true but no parent session name available")

        # Create resume job
        job_id = client.create_job(
            job_type="resume_session",
            session_name=session_name,
            prompt=prompt,
            parent_session_name=parent_session_name,
        )

        logger.info(f"Created resume job {job_id} for session {session_name}")

        if async_mode:
            response = {
                "session_name": session_name,
                "job_id": job_id,
                "status": "running",
                "message": "Agent resumed in background. Use get_agent_session_status to poll for completion.",
            }
            if callback and parent_session_name:
                response["callback_to"] = parent_session_name
            return json.dumps(response, indent=2)

        # Synchronous: wait for completion
        job = client.wait_for_job(job_id)

        # Get result
        session = client.get_session_by_name(session_name)
        if not session:
            return f"Error: Session '{session_name}' not found after job completed"

        result = client.get_session_result(session["session_id"])
        text, _ = truncate_response(result)
        return text

    except APIError as e:
        return f"Error: {str(e)}"


async def get_agent_session_status_impl(
    config: ServerConfig,
    session_name: str,
    wait_seconds: int = 0,
) -> str:
    """Get session status."""
    logger.info("get_agent_session_status called", {
        "session_name": session_name,
        "wait_seconds": wait_seconds,
    })

    try:
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        client = get_api_client(config)
        session = client.get_session_by_name(session_name)

        if not session:
            return json.dumps({"status": "not_existent"}, indent=2)

        status = client.get_session_status(session["session_id"])
        return json.dumps({"status": status}, indent=2)

    except APIError as e:
        logger.error("get_agent_session_status error", {"error": str(e)})
        return json.dumps({"status": "not_existent"}, indent=2)


async def get_agent_session_result_impl(
    config: ServerConfig,
    session_name: str,
) -> str:
    """Get session result."""
    logger.info("get_agent_session_result called", {"session_name": session_name})

    try:
        client = get_api_client(config)
        session = client.get_session_by_name(session_name)

        if not session:
            return f"Error: Session '{session_name}' does not exist."

        status = client.get_session_status(session["session_id"])

        if status == "running":
            return f"Error: Session '{session_name}' is still running. Use get_agent_session_status to poll until finished."

        result = client.get_session_result(session["session_id"])
        text, truncated = truncate_response(result)
        if truncated:
            logger.warn("get_agent_session_result: response truncated")
        return text

    except APIError as e:
        return f"Error: {str(e)}"


async def delete_all_agent_sessions_impl(config: ServerConfig) -> str:
    """Delete all agent sessions."""
    logger.info("delete_all_agent_sessions called")

    try:
        client = get_api_client(config)
        sessions = client.list_sessions()

        if not sessions:
            return "No sessions to delete"

        deleted = 0
        for session in sessions:
            if client.delete_session(session["session_id"]):
                deleted += 1

        return f"Deleted {deleted} session(s)"

    except APIError as e:
        return f"Error: {str(e)}"
```

#### 4.5 Update Server Configuration

Update `libs/server.py` to:
1. Remove `AGENT_ORCHESTRATOR_COMMAND_PATH` dependency
2. Use `AGENT_ORCHESTRATOR_API_URL` for configuration
3. Pass HTTP headers to core functions (for HTTP mode)

```python
# In get_server_config():
def get_server_config() -> ServerConfig:
    """Get configuration from environment variables"""
    from constants import get_api_url
    return ServerConfig(api_url=get_api_url())
```

#### 4.6 Handle HTTP Headers in HTTP Mode

For HTTP mode, the MCP server needs to extract `X-Agent-Session-Name` header and pass it to core functions. This requires using FastMCP's context to access request headers.

```python
# In server.py, update tool implementations to pass headers:

@mcp.tool()
async def start_agent_session(...) -> str:
    # Get HTTP headers from FastMCP context (if available)
    http_headers = None
    try:
        from fastmcp import get_http_headers
        http_headers = get_http_headers()
    except ImportError:
        pass

    return await start_agent_session_impl(
        config, session_name, prompt, agent_blueprint_name,
        project_dir, async_mode, callback, http_headers
    )
```

#### 4.7 Update Entry Point

Update `agent-orchestrator-mcp.py`:
- Remove `AGENT_ORCHESTRATOR_COMMAND_PATH` auto-discovery
- Keep `AGENT_ORCHESTRATOR_API_URL` as the only required config

---

### Phase 5: Remove Unused Code

After Phase 4 is verified working:

**Files to delete or simplify:**
- `libs/utils.py` - Remove `execute_script()`, `execute_script_async()`, command mapping
- Keep only: `truncate_response()`, formatting functions if still needed

**Files to update:**
- `libs/constants.py` - Remove `CMD_*` constants, `ENV_COMMAND_PATH`

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | Agent Runtime API URL |
| `AGENT_SESSION_NAME` | (none) | Parent session name (stdio mode) |
| `MCP_SERVER_DEBUG` | `false` | Enable debug logging |

### HTTP Headers (HTTP mode only)

| Header | Description |
|--------|-------------|
| `X-Agent-Session-Name` | Parent session name for callback support |

---

## Testing Checklist

**Test Date:** 2025-12-08

**Known Bugs:** See [mcp-server-api-refactor-bugs.md](./mcp-server-api-refactor-bugs.md) for bugs discovered during testing.

### Phase 1-2 (Agent Runtime) - ALL PASSED ✅
- [x] `POST /jobs` accepts `parent_session_name`
- [x] `GET /jobs/{job_id}` returns `parent_session_name`
- [x] New session gets `parent_session_name` from job automatically
- [x] Resumed session updates `parent_session_name` from job

### Phase 4 (MCP Server via REST API) - ALL PASSED ✅
- [x] `list_agent_blueprints` returns agents from API
- [x] `list_agent_sessions` returns sessions from API *(Bug 1 fixed)*
- [x] `start_agent_session` (sync) creates job, waits, returns result
- [x] `start_agent_session` (async) creates job, returns immediately
- [x] `start_agent_session` with `callback=true` passes parent session name *(MCP tool works, REST API missing parameter - see Bug 2)*
- [x] `resume_agent_session` works for sync and async modes
- [x] `get_agent_session_status` returns correct status
- [x] `get_agent_session_result` returns session result
- [x] `delete_all_agent_sessions` deletes all sessions

### Callback Flow - PASSED ✅
- [x] Parent starts child with `callback=true` (via Jobs API)
- [x] Child session has correct `parent_session_name`
- [ ] Child completion triggers parent resume *(not tested - requires full callback architecture)*
- [x] Different parent resuming session updates `parent_session_name`

### Bug Fixes Applied
- **Bug 1 (FIXED):** Changed `s["name"]` to `s["session_name"]` in `rest_api.py:168`

---

## Rollback Plan

If issues are discovered:
1. Revert MCP server changes (restore subprocess-based implementation)
2. Agent Runtime changes are backward-compatible (no rollback needed)

The Agent Runtime extensions (Phase 1-2) are additive and don't break existing functionality.

---

## Dependencies

The refactored MCP server uses only:
- `mcp>=1.7.0` - MCP protocol
- `fastmcp>=2.0.0` - FastMCP framework
- `pydantic>=2.0.0` - Data validation
- `fastapi>=0.115.0` - REST API (optional, for API mode)
- `uvicorn>=0.32.0` - ASGI server (optional, for HTTP mode)

No additional HTTP client library needed - uses Python's `urllib` from stdlib.
