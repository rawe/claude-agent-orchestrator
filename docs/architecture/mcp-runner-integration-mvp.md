# MVP: Agent Orchestrator MCP Integration into Agent Runner

## Status

**Draft** - Pending review

## Overview

This document describes the MVP implementation for:
1. Embedding the Agent Orchestrator MCP server (HTTP variant) into the Agent Runner
2. Moving blueprint resolution from executor to Runner
3. Introducing schema version 2.0 for executor invocation with full `agent_blueprint`

## Scope

### In Scope (MVP)

1. **Embedded MCP Server**: HTTP-based MCP server running within Agent Runner (facade to Coordinator)
2. **All 7 MCP Tools**: Complete feature parity with standalone MCP server
3. **Dynamic Port Assignment**: Runner picks available port for MCP server
4. **Blueprint Resolution in Runner**: Runner fetches and resolves blueprint, passes to executor
5. **Schema 2.0**: New invocation schema with `agent_blueprint` instead of `agent_name`
6. **Placeholder Resolution**: Runner resolves `${AGENT_ORCHESTRATOR_MCP_URL}` and `${AGENT_SESSION_ID}`
7. **Auth Integration**: MCP server uses shared Auth0 client for Coordinator API calls

### Out of Scope (MVP)

- MCP proxy for other MCP servers (future Phase 2b)
- Stdio MCP mode (HTTP only)
- Blueprint caching in Runner

## Architecture

### Key Insight: Separation of Concerns

The embedded MCP server and the RunExecutor are **separate concerns**:

| Component | Responsibility |
|-----------|----------------|
| Embedded MCP Server | Facade to Coordinator. Receives MCP tool calls from Claude, forwards to Coordinator API. Does NOT spawn executors. |
| RunExecutor | Spawns executor subprocesses when Coordinator assigns work to this Runner. Fetches and resolves blueprints. |

The MCP server forwards `start_agent_session` calls to the Coordinator. The Coordinator decides which Runner (could be any Runner instance) executes the resulting run.

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent Runner Instance                              │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                 Embedded MCP Server (NEW)                             │  │
│  │                                                                       │  │
│  │   - FastMCP HTTP server on dynamic port (127.0.0.1:0)                │  │
│  │   - FACADE to Coordinator API (authenticated via Auth0)              │  │
│  │   - 7 MCP tools: start_session, resume_session, etc.                 │  │
│  │   - Does NOT spawn executors                                         │  │
│  │                                                                       │  │
│  │   Flow:                                                               │  │
│  │   Claude calls MCP tool → MCP server → POST /runs → Coordinator      │  │
│  │   Coordinator assigns run to Runner A, B, or C (any instance)        │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                 Blueprint Resolver (NEW)                              │  │
│  │                                                                       │  │
│  │   - Fetches blueprint from Coordinator: GET /agents/{name}           │  │
│  │   - Resolves placeholders in mcp_servers config                      │  │
│  │   - Returns fully resolved agent_blueprint object                    │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                 RunExecutor (MODIFIED)                                │  │
│  │                                                                       │  │
│  │   Before spawning executor:                                          │  │
│  │   1. Fetch blueprint via BlueprintResolver                           │  │
│  │   2. Resolve placeholders (MCP URL, session ID)                      │  │
│  │   3. Build schema 2.0 payload with agent_blueprint                   │  │
│  │   4. Spawn executor with resolved payload via stdin                  │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                 Coordinator Proxy (EXISTING, unchanged)               │  │
│  │                                                                       │  │
│  │   - For other executor → Coordinator communication if needed         │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                      Spawns           │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Executor (ao-claude-code-exec)                          │
│                                                                              │
│   Receives via stdin (schema 2.0):                                          │
│   {                                                                          │
│     "schema_version": "2.0",                                                │
│     "mode": "start" | "resume",                                             │
│     "session_id": "ses_abc123",                                             │
│     "prompt": "...",                                                        │
│     "project_dir": "/path/to/project",                                      │
│     "agent_blueprint": {                                                    │
│       "name": "worker-agent",                                               │
│       "system_prompt": "...",                                               │
│       "mcp_servers": { ... resolved URLs ... }                              │
│     }                                                                        │
│   }                                                                          │
│                                                                              │
│   Executor:                                                                  │
│   - Uses agent_blueprint directly (NO Coordinator API call)                 │
│   - Sets up Claude with system_prompt and mcp_servers                       │
│   - Claude makes MCP calls to embedded MCP server URL                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow: Starting a Child Session

```
┌──────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Claude  │     │ Embedded    │     │ Coordinator │     │ Any Runner  │
│ (in exec)│     │ MCP Server  │     │             │     │ Instance    │
└────┬─────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
     │                  │                   │                   │
     │ start_agent_     │                   │                   │
     │ session(...)     │                   │                   │
     ├─────────────────►│                   │                   │
     │                  │                   │                   │
     │                  │ POST /runs        │                   │
     │                  │ (authenticated)   │                   │
     │                  ├──────────────────►│                   │
     │                  │                   │                   │
     │                  │                   │ Assign run to     │
     │                  │                   │ available Runner  │
     │                  │                   ├──────────────────►│
     │                  │                   │                   │
     │                  │   { run_id,       │                   │
     │                  │     session_id }  │                   │
     │                  │◄──────────────────┤                   │
     │                  │                   │                   │
     │  session info    │                   │                   │
     │◄─────────────────┤                   │                   │
     │                  │                   │                   │
```

## Schema 2.0: Executor Invocation

### Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ExecutorInvocation",
  "description": "Schema 2.0 - Executor receives resolved agent_blueprint",
  "type": "object",
  "required": ["schema_version", "mode", "session_id", "prompt"],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["2.0"],
      "description": "Schema version"
    },
    "mode": {
      "type": "string",
      "enum": ["start", "resume"],
      "description": "Execution mode"
    },
    "session_id": {
      "type": "string",
      "description": "Coordinator-generated session ID"
    },
    "prompt": {
      "type": "string",
      "description": "User prompt"
    },
    "project_dir": {
      "type": "string",
      "description": "Working directory (start mode)"
    },
    "agent_blueprint": {
      "type": "object",
      "description": "Fully resolved agent blueprint",
      "properties": {
        "name": { "type": "string" },
        "system_prompt": { "type": "string" },
        "mcp_servers": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "type": { "type": "string" },
              "url": { "type": "string" },
              "headers": { "type": "object" }
            }
          }
        }
      }
    }
  }
}
```

### Example: Start Mode

```json
{
  "schema_version": "2.0",
  "mode": "start",
  "session_id": "ses_abc123",
  "prompt": "Analyze the codebase and create documentation",
  "project_dir": "/home/user/project",
  "agent_blueprint": {
    "name": "documentation-writer",
    "system_prompt": "You are a documentation specialist...",
    "mcp_servers": {
      "orchestrator": {
        "type": "http",
        "url": "http://127.0.0.1:54321",
        "headers": {
          "X-Agent-Session-Id": "ses_abc123"
        }
      }
    }
  }
}
```

### Example: Resume Mode

```json
{
  "schema_version": "2.0",
  "mode": "resume",
  "session_id": "ses_abc123",
  "prompt": "Continue with the API documentation",
  "agent_blueprint": {
    "name": "documentation-writer",
    "system_prompt": "You are a documentation specialist...",
    "mcp_servers": {
      "orchestrator": {
        "type": "http",
        "url": "http://127.0.0.1:54321",
        "headers": {
          "X-Agent-Session-Id": "ses_abc123"
        }
      }
    }
  }
}
```

Note: `agent_blueprint` is provided for resume too (Runner re-fetches to get latest config).

## Placeholder Resolution

### Supported Placeholders

| Placeholder | Replaced With | Purpose |
|-------------|---------------|---------|
| `${AGENT_ORCHESTRATOR_MCP_URL}` | `http://127.0.0.1:<mcp_port>` | Embedded MCP server URL |
| `${AGENT_SESSION_ID}` | Current session ID | Session context for MCP calls |

### Blueprint Before/After Resolution

**Stored in Coordinator (with placeholders):**
```json
{
  "name": "worker-agent",
  "system_prompt": "You are a worker agent...",
  "mcp_servers": {
    "orchestrator": {
      "type": "http",
      "url": "${AGENT_ORCHESTRATOR_MCP_URL}",
      "headers": {
        "X-Agent-Session-Id": "${AGENT_SESSION_ID}"
      }
    }
  }
}
```

**Passed to executor (resolved):**
```json
{
  "name": "worker-agent",
  "system_prompt": "You are a worker agent...",
  "mcp_servers": {
    "orchestrator": {
      "type": "http",
      "url": "http://127.0.0.1:54321",
      "headers": {
        "X-Agent-Session-Id": "ses_abc123"
      }
    }
  }
}
```

### Resolution Logic

```python
def resolve_placeholders(
    blueprint: dict,
    session_id: str,
    mcp_server_url: str,
) -> dict:
    """
    Resolve placeholders in blueprint's mcp_servers config.

    Recursively walks mcp_servers and replaces:
    - ${AGENT_ORCHESTRATOR_MCP_URL} → mcp_server_url
    - ${AGENT_SESSION_ID} → session_id
    """
    result = copy.deepcopy(blueprint)
    mcp_servers = result.get("mcp_servers", {})

    for server_name, config in mcp_servers.items():
        # Resolve URL
        if "url" in config and isinstance(config["url"], str):
            config["url"] = config["url"].replace(
                "${AGENT_ORCHESTRATOR_MCP_URL}", mcp_server_url
            )

        # Resolve headers
        headers = config.get("headers", {})
        for key, value in headers.items():
            if isinstance(value, str):
                headers[key] = value.replace(
                    "${AGENT_SESSION_ID}", session_id
                )

    return result
```

## Directory Structure

```
servers/agent-runner/
├── lib/
│   ├── __init__.py
│   ├── auth0_client.py              # (existing)
│   ├── coordinator_proxy.py         # (existing)
│   ├── executor.py                  # (MODIFIED - uses BlueprintResolver)
│   ├── invocation.py                # (MODIFIED - schema 2.0)
│   ├── blueprint_resolver.py        # (NEW)
│   │
│   └── agent_orchestrator_mcp/      # (NEW - dedicated library)
│       ├── __init__.py              # Exports: MCPServer
│       ├── server.py                # FastMCP server with 7 tools
│       ├── coordinator_client.py    # Async HTTP client with auth
│       ├── tools.py                 # MCP tool implementations
│       ├── context.py               # HTTP header extraction
│       ├── constants.py             # Character limits, header names
│       └── schemas.py               # ExecutionMode, etc.
│
├── executors/
│   └── claude-code/
│       ├── ao-claude-code-exec      # (MODIFIED - uses agent_blueprint)
│       └── lib/
│           └── claude_client.py     # (MODIFIED - no Coordinator API call)
```

## Component Specifications

### 1. MCPServer (`agent_orchestrator_mcp/server.py`)

```python
class MCPServer:
    """
    Embedded MCP server - facade to Agent Coordinator.

    Runs FastMCP HTTP server on dynamic port.
    Forwards MCP tool calls to Coordinator API.
    Does NOT spawn executors.
    """

    def __init__(
        self,
        coordinator_url: str,
        auth0_client: Optional[Auth0M2MClient] = None,
    ):
        """
        Args:
            coordinator_url: Agent Coordinator API URL
            auth0_client: Auth0 client for authenticated API calls
        """
        self._coordinator_url = coordinator_url
        self._auth0_client = auth0_client
        self._port: int = 0
        self._server_thread: Optional[Thread] = None

    @property
    def port(self) -> int:
        """Port the server is listening on (0 if not started)."""

    @property
    def url(self) -> str:
        """Full URL: http://127.0.0.1:<port>"""

    def start(self) -> int:
        """Start server on dynamic port. Returns assigned port."""

    def stop(self) -> None:
        """Stop the server gracefully."""
```

### 2. CoordinatorClient (`agent_orchestrator_mcp/coordinator_client.py`)

```python
class CoordinatorClient:
    """
    Async HTTP client for Agent Coordinator API.

    Injects Bearer token from Auth0 client when available.
    """

    def __init__(
        self,
        base_url: str,
        auth0_client: Optional[Auth0M2MClient] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._auth0_client = auth0_client

    def _get_auth_headers(self) -> dict:
        """Get Authorization header if auth configured."""
        if self._auth0_client and self._auth0_client.is_configured:
            token = self._auth0_client.get_access_token()
            if token:
                return {"Authorization": f"Bearer {token}"}
        return {}

    # Runs API
    async def create_run(self, ...) -> dict
    async def get_run(self, run_id: str) -> dict
    async def wait_for_run(self, run_id: str, ...) -> dict

    # Sessions API
    async def get_session(self, session_id: str) -> Optional[dict]
    async def get_session_status(self, session_id: str) -> str
    async def get_session_result(self, session_id: str) -> str
    async def list_sessions(self) -> list[dict]
    async def delete_session(self, session_id: str) -> bool

    # Agents API
    async def list_agents(self, tags: Optional[str] = None) -> list[dict]
    async def get_agent(self, agent_name: str) -> Optional[dict]
```

### 3. BlueprintResolver (`lib/blueprint_resolver.py`)

```python
class BlueprintResolver:
    """
    Fetches agent blueprints from Coordinator and resolves placeholders.
    """

    def __init__(
        self,
        coordinator_url: str,
        auth0_client: Optional[Auth0M2MClient] = None,
    ):
        self._coordinator_url = coordinator_url
        self._auth0_client = auth0_client

    async def resolve(
        self,
        agent_name: str,
        session_id: str,
        mcp_server_url: str,
    ) -> dict:
        """
        Fetch blueprint and resolve placeholders.

        Args:
            agent_name: Blueprint name to fetch
            session_id: For ${AGENT_SESSION_ID} replacement
            mcp_server_url: For ${AGENT_ORCHESTRATOR_MCP_URL} replacement

        Returns:
            Resolved agent_blueprint dict

        Raises:
            BlueprintNotFoundError: If blueprint doesn't exist
        """

    def resolve_placeholders(
        self,
        blueprint: dict,
        session_id: str,
        mcp_server_url: str,
    ) -> dict:
        """Replace placeholders in mcp_servers config."""
```

### 4. MCP Tools (`agent_orchestrator_mcp/tools.py`)

All 7 tools from standalone MCP server:

| Tool | Purpose |
|------|---------|
| `list_agent_blueprints` | List available blueprints (filtered by X-Agent-Tags header) |
| `list_agent_sessions` | List all sessions |
| `start_agent_session` | Start new session (sync/async_poll/async_callback) |
| `resume_agent_session` | Resume existing session |
| `get_agent_session_status` | Poll session status |
| `get_agent_session_result` | Get completed session result |
| `delete_all_agent_sessions` | Delete all sessions |

Context extracted from HTTP headers:
- `X-Agent-Session-Id` - parent session for callbacks
- `X-Agent-Tags` - filter visible blueprints
- `X-Additional-Demands` - JSON with hostname, project_dir, executor_type, tags

## Changes to Existing Components

### RunExecutor (`lib/executor.py`)

```python
class RunExecutor:
    def __init__(
        self,
        default_project_dir: str,
        blueprint_resolver: BlueprintResolver,  # NEW
        mcp_server_url: str,                    # NEW
    ):
        self.default_project_dir = default_project_dir
        self.blueprint_resolver = blueprint_resolver
        self.mcp_server_url = mcp_server_url
        self.executor_path = get_executor_path()

    async def execute_run(self, run: Run) -> subprocess.Popen:
        # Determine mode
        mode = "start" if run.type == "start_session" else "resume"

        # Resolve blueprint (NEW)
        agent_blueprint = None
        if run.agent_name:
            agent_blueprint = await self.blueprint_resolver.resolve(
                agent_name=run.agent_name,
                session_id=run.session_id,
                mcp_server_url=self.mcp_server_url,
            )

        # Build schema 2.0 payload (CHANGED)
        payload = {
            "schema_version": "2.0",
            "mode": mode,
            "session_id": run.session_id,
            "prompt": run.prompt,
        }

        if mode == "start":
            payload["project_dir"] = run.project_dir or self.default_project_dir

        if agent_blueprint:
            payload["agent_blueprint"] = agent_blueprint

        # Spawn executor (unchanged mechanism)
        return self._spawn_executor(payload)
```

### ExecutorInvocation (`lib/invocation.py`)

```python
SCHEMA_VERSION = "2.0"
SUPPORTED_VERSIONS = {"1.0", "2.0"}  # Backward compat

@dataclass
class ExecutorInvocation:
    schema_version: str
    mode: Literal["start", "resume"]
    session_id: str
    prompt: str
    project_dir: Optional[str] = None
    agent_blueprint: Optional[dict] = None  # NEW (schema 2.0)
    agent_name: Optional[str] = None        # DEPRECATED (schema 1.0 compat)
    metadata: dict = field(default_factory=dict)
```

### ao-claude-code-exec (Executor)

```python
# In executor startup

invocation = ExecutorInvocation.from_stdin()

if invocation.agent_blueprint:
    # Schema 2.0: Use provided blueprint directly
    system_prompt = invocation.agent_blueprint.get("system_prompt")
    mcp_servers = invocation.agent_blueprint.get("mcp_servers", {})
elif invocation.agent_name:
    # Schema 1.0 backward compat: Fetch from Coordinator (deprecated)
    blueprint = fetch_blueprint(invocation.agent_name)
    system_prompt = blueprint.get("system_prompt")
    mcp_servers = blueprint.get("mcp_servers", {})
else:
    # No blueprint
    system_prompt = None
    mcp_servers = {}

# Set up Claude with system_prompt and mcp_servers
# NO placeholder resolution needed - already done by Runner
```

## Agent Runner Startup

```python
# In agent-runner main

async def main():
    # 1. Initialize Auth0 client (existing)
    auth0_client = Auth0M2MClient(...)

    # 2. Start Coordinator Proxy (existing)
    proxy = CoordinatorProxy(coordinator_url, auth0_client)
    proxy.start()
    os.environ["AGENT_ORCHESTRATOR_API_URL"] = proxy.url

    # 3. Start embedded MCP server (NEW)
    mcp_server = MCPServer(coordinator_url, auth0_client)
    mcp_server.start()
    logger.info(f"Embedded MCP server on port {mcp_server.port}")

    # 4. Create blueprint resolver (NEW)
    blueprint_resolver = BlueprintResolver(coordinator_url, auth0_client)

    # 5. Create executor with resolver (MODIFIED)
    executor = RunExecutor(
        default_project_dir=config.default_project_dir,
        blueprint_resolver=blueprint_resolver,
        mcp_server_url=mcp_server.url,
    )

    # 6. Start run poller/supervisor (existing)
    ...
```

## Testing Strategy

### Unit Tests

1. **BlueprintResolver**
   - Placeholder resolution in nested structures
   - Missing placeholders passed through unchanged
   - Blueprint fetch with/without auth

2. **MCPServer**
   - Starts on dynamic port
   - All 7 tools respond correctly
   - Auth header injection

3. **Schema 2.0 Invocation**
   - Parsing with agent_blueprint
   - Backward compat with schema 1.0 (agent_name)

### Integration Tests

1. **End-to-end flow**
   - Runner starts with embedded MCP
   - Run assigned to Runner
   - Blueprint resolved with placeholders
   - Executor receives schema 2.0 payload
   - Claude connects to embedded MCP
   - MCP call forwarded to Coordinator

2. **Placeholder resolution**
   - Create blueprint with placeholders in Coordinator
   - Verify executor receives resolved values

## Migration

### For Users

1. Update agent blueprints in Coordinator to use placeholders:
   ```json
   {
     "mcp_servers": {
       "orchestrator": {
         "type": "http",
         "url": "${AGENT_ORCHESTRATOR_MCP_URL}",
         "headers": {
           "X-Agent-Session-Id": "${AGENT_SESSION_ID}"
         }
       }
     }
   }
   ```

2. Deploy updated Agent Runner with embedded MCP server

3. Standalone MCP server no longer needed for orchestrated agents

### Backward Compatibility

- Schema 1.0 with `agent_name` still supported (executor fetches blueprint)
- Gradual migration: new Runners use schema 2.0, old executors still work

## Summary

| Aspect | Before (Current) | After (MVP) |
|--------|------------------|-------------|
| Blueprint resolution | Executor fetches from Coordinator | Runner fetches and resolves |
| MCP server | Standalone process | Embedded in Runner |
| Invocation schema | 1.0 with agent_name | 2.0 with agent_blueprint |
| Placeholder resolution | Not supported | Runner resolves before spawn |
| Executor Coordinator calls | Yes (fetch blueprint) | No (receives resolved blueprint) |
| MCP authentication | None or separate M2M | Uses Runner's Auth0 client |
