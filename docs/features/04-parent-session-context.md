# Work Package 4: Parent Session Context

**Reference**: [agent-callback-architecture.md](./agent-callback-architecture.md)
- Read sections: "Callback Opt-In Mechanism", "Parent Session Context", "Required Changes to ao-* Commands", "Parent Session Context via MCP HTTP Mode", "Implementation Plan > Phase 4"

## Goal

Enable child sessions to know their parent. When an orchestrator starts a child agent with `callback=true`, the child's session records `parent_session_name`. This is the foundation for callbacks.

**Key insight**: Callback is opt-in via the MCP server's `callback` parameter. The MCP server is responsible for propagating parent context when callback is requested.

## Runnable State After Completion

- Sessions table tracks parent-child relationships
- Launcher sets `AGENT_SESSION_NAME` environment variable for sessions it starts
- MCP server propagates `AGENT_SESSION_NAME` when `callback=true`
- ao-start reads env var and passes to Sessions API
- Parent-child relationships visible in Sessions API responses

## Files to Modify

### MCP Server (callback opt-in)

| File | Changes |
|------|---------|
| `interfaces/agent-orchestrator-mcp-server/libs/server.py` | Add `callback` parameter to tools |
| `interfaces/agent-orchestrator-mcp-server/libs/core_functions.py` | Pass `callback` to execute_script_async |
| `interfaces/agent-orchestrator-mcp-server/libs/utils.py` | Propagate env var when callback=true |

### Agent Runtime

| File | Changes |
|------|---------|
| `servers/agent-runtime/database.py` | Add `parent_session_name` column |
| `servers/agent-runtime/models.py` | Add `parent_session_name` to session models |
| `servers/agent-runtime/main.py` | Accept `parent_session_name` in session creation |

### ao-* Commands

| File | Changes |
|------|---------|
| `plugins/.../commands/ao-start` | Read `AGENT_SESSION_NAME` env var |
| `plugins/.../commands/lib/session_client.py` | Pass `parent_session_name` to API |

### Agent Launcher

| File | Changes |
|------|---------|
| `servers/agent-launcher/lib/executor.py` | Set `AGENT_SESSION_NAME` in subprocess env |

### Dashboard (optional)

| File | Changes |
|------|---------|
| `dashboard/src/types/agent.ts` | Add headers to MCPServerHttp |
| `dashboard/src/utils/mcpTemplates.ts` | Add X-Agent-Session-Name header template |

## Implementation Tasks

### 1. MCP Server: Add `callback` Parameter to Tools (`libs/server.py`)

Add `callback: bool = False` parameter to start/resume tools:

```python
@mcp.tool()
async def start_agent_session(
    session_name: str,
    prompt: str,
    agent_blueprint_name: Optional[str] = None,
    project_dir: Optional[str] = None,
    async_mode: bool = False,
    callback: bool = False,  # NEW
) -> str:
    """Start a new agent session.

    Args:
        callback: If true (requires async_mode=true), parent will be resumed
                  when this child completes. Parent must be running via Launcher.
    """
```

### 2. MCP Server: Pass `callback` to Implementation (`libs/core_functions.py`)

Update `start_agent_session_impl` and `resume_agent_session_impl`:

```python
async def start_agent_session_impl(
    config: ServerConfig,
    session_name: str,
    prompt: str,
    agent_blueprint_name: Optional[str] = None,
    project_dir: Optional[str] = None,
    async_mode: bool = False,
    callback: bool = False,  # NEW
) -> str:
    # ...
    if async_mode:
        async_result = await execute_script_async(config, args, callback=callback)
        # ...
```

### 3. MCP Server: Propagate Env Var (`libs/utils.py`)

Update `execute_script_async()` to set `AGENT_SESSION_NAME` when callback=true:

```python
async def execute_script_async(
    config: ServerConfig,
    args: List[str],
    stdin_input: Optional[str] = None,
    callback: bool = False,  # NEW
) -> AsyncExecutionResult:
    # ...
    env = os.environ.copy()

    # Propagate parent session context for callbacks
    if callback:
        parent_session = os.environ.get("AGENT_SESSION_NAME")
        if parent_session:
            env["AGENT_SESSION_NAME"] = parent_session
            logger.info(f"Callback enabled, propagating parent session: {parent_session}")
        else:
            logger.warn("callback=true but AGENT_SESSION_NAME not set - callback will not work")

    process = subprocess.Popen(
        uv_args,
        # ...
        env=env,  # Use modified env
        # ...
    )
```

### 4. Database Schema Update (`database.py`)

Add column to sessions table:
```python
# In init_db() or migration
"""ALTER TABLE sessions ADD COLUMN parent_session_name TEXT"""
```

Handle migration gracefully (column may already exist).

### 5. Session Models (`models.py`)

Update `SessionCreate`:
```python
class SessionCreate(BaseModel):
    session_id: str
    session_name: str
    project_dir: str
    agent_name: Optional[str] = None
    parent_session_name: Optional[str] = None  # NEW
```

Update session queries to return `parent_session_name`.

### 6. Sessions API (`main.py`)

In `POST /sessions`:
- Accept `parent_session_name` field
- Store in database

In `GET /sessions/{id}` and `GET /sessions`:
- Return `parent_session_name` in response

### 7. Session Client (`lib/session_client.py`)

Update `create_session()`:
```python
def create_session(
    self,
    session_id: str,
    session_name: str,
    project_dir: str,
    agent_name: Optional[str] = None,
    parent_session_name: Optional[str] = None,  # NEW
) -> dict:
    data = {...}
    if parent_session_name:
        data["parent_session_name"] = parent_session_name
    return self._post("/sessions", data)
```

### 8. ao-start Command

Read environment variable and pass to session creation:
```python
# In ao-start main function
parent_session_name = os.environ.get("AGENT_SESSION_NAME")

# Pass to claude_client or session_client
session_client.create_session(
    ...,
    parent_session_name=parent_session_name,
)
```

### 9. Agent Launcher Executor (`executor.py`)

When spawning subprocess, set environment:
```python
def execute_job(job: Job) -> subprocess.Popen:
    env = os.environ.copy()
    env["AGENT_SESSION_NAME"] = job.session_name  # Parent context for children

    cmd = build_command(job)
    return subprocess.Popen(cmd, env=env, ...)
```

### 10. MCP Server HTTP Mode (Optional for POC)

In `core_functions.py`, when executing ao-* commands:
```python
# Extract header from FastMCP context
from fastmcp import get_http_headers

headers = get_http_headers()
parent_session = headers.get("X-Agent-Session-Name")

# Set in subprocess environment
env = os.environ.copy()
if parent_session:
    env["AGENT_SESSION_NAME"] = parent_session
```

### 11. Dashboard MCP Templates (Optional)

Update `MCPServerHttp` type:
```typescript
export interface MCPServerHttp {
  type: 'http';
  url: string;
  headers?: Record<string, string>;  // NEW
}
```

## Testing Checklist

- [ ] MCP tool shows `callback` parameter in schema
- [ ] `async_mode=true, callback=false` → No parent_session_name set (existing behavior)
- [ ] `async_mode=true, callback=true` → parent_session_name set in child session
- [ ] Start session via Launcher → `AGENT_SESSION_NAME` env var is set
- [ ] Query sessions API → `parent_session_name` returned correctly
- [ ] Multiple levels: orchestrator → child (with callback) → grandchild

## Notes

- **Callback is opt-in**: Only when `callback=true` is passed to MCP tool
- Environment variable name: `AGENT_SESSION_NAME`
- HTTP header name: `X-Agent-Session-Name`
- The Launcher sets env var for the session it starts (that session becomes parent of any children it spawns via MCP with callback=true)
