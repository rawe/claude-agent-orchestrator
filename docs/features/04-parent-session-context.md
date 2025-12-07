# Work Package 4: Parent Session Context

**Reference**: [agent-callback-architecture.md](./agent-callback-architecture.md)
- Read sections: "Parent Session Context", "Required Changes to ao-* Commands", "Parent Session Context via MCP HTTP Mode", "Implementation Plan > Phase 4"

## Goal

Enable child sessions to know their parent. When an orchestrator starts a child agent, the child's session records `parent_session_name`. This is the foundation for callbacks.

## Runnable State After Completion

- Sessions table tracks parent-child relationships
- Launcher sets `AGENT_SESSION_NAME` environment variable
- ao-start reads env var and passes to Sessions API
- MCP HTTP mode propagates parent context via headers
- Dashboard shows parent relationships (optional enhancement)

## Files to Modify

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

### MCP Server (for HTTP mode)

| File | Changes |
|------|---------|
| `interfaces/agent-orchestrator-mcp-server/libs/core_functions.py` | Extract header, set env var |

### Dashboard (optional)

| File | Changes |
|------|---------|
| `dashboard/src/types/agent.ts` | Add headers to MCPServerHttp |
| `dashboard/src/utils/mcpTemplates.ts` | Add X-Agent-Session-Name header template |

## Implementation Tasks

### 1. Database Schema Update (`database.py`)

Add column to sessions table:
```python
# In init_db() or migration
"""ALTER TABLE sessions ADD COLUMN parent_session_name TEXT"""
```

Handle migration gracefully (column may already exist).

### 2. Session Models (`models.py`)

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

### 3. Sessions API (`main.py`)

In `POST /sessions`:
- Accept `parent_session_name` field
- Store in database

In `GET /sessions/{id}` and `GET /sessions`:
- Return `parent_session_name` in response

### 4. Session Client (`lib/session_client.py`)

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

### 5. ao-start Command

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

### 6. Agent Launcher Executor (`executor.py`)

When spawning subprocess, set environment:
```python
def execute_job(job: Job) -> subprocess.Popen:
    env = os.environ.copy()
    env["AGENT_SESSION_NAME"] = job.session_name  # Parent context for children

    cmd = build_command(job)
    return subprocess.Popen(cmd, env=env, ...)
```

### 7. MCP Server HTTP Mode (Optional for POC)

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

### 8. Dashboard MCP Templates (Optional)

Update `MCPServerHttp` type:
```typescript
export interface MCPServerHttp {
  type: 'http';
  url: string;
  headers?: Record<string, string>;  // NEW
}
```

Add default template with placeholder:
```typescript
'agent-orchestrator-http': {
  type: 'http',
  url: 'http://localhost:9500/mcp',
  headers: {
    'X-Agent-Session-Name': '${AGENT_SESSION_NAME}'
  }
}
```

## Testing Checklist

- [ ] Start session via Launcher → check `parent_session_name` is null
- [ ] Start child via running orchestrator → child has `parent_session_name` set
- [ ] Query sessions API → `parent_session_name` returned correctly
- [ ] Multiple levels: orchestrator → child → grandchild (each knows parent)
- [ ] MCP HTTP mode: header propagates to subprocess (if implemented)

## Notes

- Environment variable name: `AGENT_SESSION_NAME`
- HTTP header name: `X-Agent-Session-Name`
- Placeholder pattern: `${AGENT_SESSION_NAME}`
- The Launcher sets env var for the session it starts (that session becomes parent of any children it spawns)
