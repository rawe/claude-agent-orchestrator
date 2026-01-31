# Architecture: MCP Server Integration into Agent Runner

## Status

**Implemented** - The MCP server is embedded in the Agent Runner. Placeholder resolution happens at Coordinator (except `${runner.*}` which is resolved at Runner).

## Context

### Previous State (Historical)

The Agent Orchestrator MCP server was previously a standalone component that:
1. Exposed MCP tools (`start_session`, `resume_session`, etc.) for spawning child agents
2. Ran in stdio mode (Claude Desktop/CLI subprocess) or HTTP mode (standalone server)
3. Made unauthenticated HTTP calls to the Agent Coordinator
4. Relied on `AGENT_SESSION_ID` environment variable and HTTP headers to identify the calling session

### Problems with Current Architecture

**1. Authentication Gap**

When the Coordinator has `AUTH_ENABLED=true`, the MCP server cannot communicate with it. The MCP server would need its own Auth0 M2M credentials, creating:
- Secret distribution complexity (especially for stdio mode)
- Duplication of auth logic already in the Agent Runner
- Additional M2M application in Auth0

**2. Limited Context Passing**

Currently, context flows through environment variables:
```
Runner → sets AGENT_SESSION_ID env var → Executor → MCP server reads env → passes as header
```

This pattern doesn't scale:
- Adding more context values requires executor changes
- Each executor framework must handle the env-to-header mapping
- No central place to enrich context with metadata

**3. Executor Complexity**

Executors currently handle:
- Agent blueprint resolution (API call to get config)
- MCP server configuration
- System prompt configuration
- Session binding

This makes executors complex and framework-specific logic gets mixed with orchestration logic.

**4. MCP Configuration Management**

Agent blueprints include MCP server configurations. The orchestrator MCP server is one such capability. Currently:
- Executor resolves the blueprint
- Executor passes MCP config to the agent framework
- No opportunity for the Runner to modify or enhance the config

---

## Proposed Architecture

### Core Idea

Move the MCP server functionality into the Agent Runner, leveraging:
- Runner's existing Auth0 M2M authentication
- Runner's knowledge of sessions, blueprints, and runs
- The established proxy pattern for executor communication

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent Runner                                 │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │  Auth0M2MClient  │  │ Blueprint        │  │ Session          │   │
│  │  (existing)      │  │ Resolver (new)   │  │ Context (new)    │   │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │
│           │                     │                     │              │
│           ▼                     ▼                     ▼              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Coordinator Proxy (existing)               │   │
│  │   Forwards: /sessions, /runs, /agents → Coordinator           │   │
│  │   Auth: Injects Bearer token                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    MCP Gateway (new, embedded, HTTP)          │   │
│  │   - Single instance for all executors                         │   │
│  │   - Orchestrator MCP: native (start_session, resume_session)  │   │
│  │   - Other MCPs: proxied (Context Store, Atlassian, etc.)      │   │
│  │   - Enriches requests with session/blueprint context          │   │
│  │   - Uses authenticated Coordinator client                     │   │
│  │   - Single interception point for all MCP traffic             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Executor Spawner                           │   │
│  │   - Resolves blueprint BEFORE spawning                        │   │
│  │   - Passes resolved config (not agent_name)                   │   │
│  │   - Sets MCP URL pointing to Runner's MCP server              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                     Spawns         │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Executor (simplified)                        │
│                                                                      │
│   Receives:                                                          │
│   - session_id                                                       │
│   - prompt                                                           │
│   - project_dir                                                      │
│   - resolved_config: { system_prompt, mcp_servers }                  │
│                                                                      │
│   Does NOT:                                                          │
│   - Resolve agent blueprints                                         │
│   - Know about authentication                                        │
│   - Modify MCP configurations                                        │
│                                                                      │
│   ALL MCP calls go to: Runner's MCP Gateway (URLs rewritten by Runner)│
│   Passes: X-Agent-Session-Id header                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Benefits

**1. Authentication Solved**

The Runner already authenticates with Auth0 M2M. The embedded MCP server uses this same authentication when calling Coordinator APIs. No secret distribution needed.

**2. Context Enrichment**

When an executor's MCP call arrives at the Runner:
```
Executor sends:
  POST /mcp/tools/start_session
  X-Agent-Session-Id: ses_parent123
  Body: { "agent_name": "worker", "prompt": "..." }

Runner's MCP server:
  1. Looks up session ses_parent123 in its registry
  2. Knows the parent's agent blueprint, project_dir, etc.
  3. Can add parent_session_id, inherit settings, validate permissions
  4. Calls Coordinator with enriched request
```

Future context additions require no executor changes.

**3. Simplified Executors**

Executors become thin wrappers around agent frameworks:
- Receive fully resolved configuration
- Start the agent with the provided config
- Pass session_id header on MCP calls
- Report completion/failure

This makes adding new executor types (LangChain, AutoGen, etc.) much simpler.

**4. Centralized MCP Configuration**

The Runner can:
- Adjust MCP server URLs (point orchestrator MCP to itself)
- Add capability-specific MCP servers based on blueprint
- Validate MCP configurations before spawning

---

## Implementation Strategy

### Phase 1: Move Blueprint Resolution to Runner (Prerequisite)

**Goal:** Executor receives `agent_blueprint` instead of `agent_name`

The executor shouldn't know or care whether the blueprint was resolved by the Runner or came from elsewhere - it simply receives the configuration it needs to run.

**Changes:**

1. **Modify Run payload structure**

   Current (executor receives):
   ```json
   {
     "schema_version": "1.0",
     "mode": "start",
     "session_id": "ses_abc123",
     "agent_name": "my-agent",
     "prompt": "Hello",
     "project_dir": "/path/to/project"
   }
   ```

   New (executor receives for **start**):
   ```json
   {
     "schema_version": "2.0",
     "mode": "start",
     "session_id": "ses_abc123",
     "prompt": "Hello",
     "project_dir": "/path/to/project",
     "agent_blueprint": {
       "name": "my-agent",
       "system_prompt": "You are a helpful assistant...",
       "mcp_servers": {
         "orchestrator": {
           "type": "http",
           "url": "http://127.0.0.1:9999",
           "headers": {
             "X-Agent-Session-Id": "ses_abc123"
           }
         }
       }
     }
   }
   ```

   New (executor receives for **resume**):
   ```json
   {
     "schema_version": "2.0",
     "mode": "resume",
     "session_id": "ses_abc123",
     "executor_session_id": "claude-sdk-uuid-xyz",
     "prompt": "Continue working",
     "project_dir": "/path/to/project",
     "agent_blueprint": {
       "name": "my-agent",
       "system_prompt": "You are a helpful assistant...",
       "mcp_servers": {
         "orchestrator": {
           "type": "http",
           "url": "http://127.0.0.1:9999",
           "headers": {
             "X-Agent-Session-Id": "ses_abc123"
           }
         }
       }
     }
   }
   ```

   Notes:
   - `executor_session_id`: Required for resume. The ID the executor uses to find the session in its own storage (e.g., Claude SDK's session UUID). **Open question:** How this is provided to the executor (in Run object, separate fetch, etc.) needs to be decided. Currently, the executor fetches it itself via session API.
   - `agent_blueprint`: Same for start and resume. Executor decides which fields to use based on `mode`.
   - `mcp_servers`: Placeholders are resolved in two stages:
     - **Coordinator** resolves `${runtime.*}`, `${params.*}`, `${scope.*}`, `${env.*}` at run creation
     - **Runner** resolves `${runner.orchestrator_mcp_url}` (dynamic port known only at Runner)
   - See [Placeholder Reference](../../reference/placeholder-reference.md) for details.

2. **Runner resolves blueprint before spawning**

   ```python
   # In Runner's executor spawning logic

   async def spawn_executor(self, run: Run):
       # Resolve blueprint in Runner (not executor)
       agent_blueprint = None
       if run.agent_name:
           agent_blueprint = await self.resolve_blueprint(run.agent_name)
           # Modify MCP config (e.g., inject Runner's MCP URL)
           agent_blueprint = self.adjust_mcp_config(agent_blueprint)

       # Build invocation - executor decides what to use from agent_blueprint
       invocation = {
           "schema_version": "2.0",
           "mode": run.type.replace("_session", ""),
           "session_id": run.session_id,
           "prompt": run.prompt,
           "project_dir": run.project_dir,
           "agent_blueprint": agent_blueprint,
       }

       # For resume: provide executor_session_id
       # OPEN: How to get this - from Run object? Separate fetch? TBD.
       if run.type == "resume_session":
           invocation["executor_session_id"] = ...  # TBD

       await self.executor.execute(invocation)
   ```

3. **Simplify executor**

   Remove from executor:
   - `get_agent_api()` calls
   - Blueprint validation logic

   Executor uses `agent_blueprint` fields directly (mcp_servers, system_prompt).

**Files to modify:**
- `servers/agent-runner/lib/invocation.py` - New schema version
- `servers/agent-runner/lib/executor.py` - Blueprint resolution
- `servers/agent-runner/executors/claude-code/ao-claude-code-exec` - Simplify
- `servers/agent-runner/executors/claude-code/lib/claude_client.py` - Accept resolved config

---

### Phase 2: Embed MCP Server in Runner

**Goal:** Runner hosts MCP server, executors connect to it

**Changes:**

1. **Add MCP server component to Runner**

   ```python
   # servers/agent-runner/lib/mcp_server.py

   class RunnerMCPServer:
       """MCP server embedded in Agent Runner."""

       def __init__(
           self,
           coordinator_client: CoordinatorAPIClient,
           session_registry: RunningRunsRegistry,
       ):
           self.coordinator = coordinator_client
           self.sessions = session_registry
           self._port: int = 0

       async def handle_start_session(
           self,
           request: StartSessionRequest,
           session_id: str,  # From X-Agent-Session-Id header
       ) -> StartSessionResponse:
           """Handle start_session MCP tool call."""
           # Enrich with context from parent session
           parent_run = self.sessions.get_by_session_id(session_id)

           # Call Coordinator with enriched request
           return await self.coordinator.create_run(
               type="start_session",
               agent_name=request.agent_name,
               prompt=request.prompt,
               parent_session_id=session_id,
               project_dir=parent_run.project_dir if parent_run else None,
               # ... additional context
           )
   ```

2. **Start MCP server alongside proxy**

   ```python
   # In Runner.start()

   def start(self):
       # Existing proxy
       self.proxy.start()
       os.environ["AGENT_ORCHESTRATOR_API_URL"] = self.proxy.url

       # New: MCP server (Runner knows its own URL, no env var needed)
       self.mcp_server.start()
       # URL is injected into agent_blueprint via adjust_mcp_config()
   ```

3. **Placeholder resolution (two-stage)**

   Placeholders are resolved at two levels:

   | Stage | Placeholder | Resolved By | Example |
   |-------|-------------|-------------|---------|
   | 1 | `${runtime.session_id}` | Coordinator | Session ID for MCP headers |
   | 1 | `${params.*}`, `${scope.*}`, `${env.*}` | Coordinator | Config values |
   | 2 | `${runner.orchestrator_mcp_url}` | Runner | Dynamic MCP server URL |

   Blueprint config (before Coordinator resolution):
   ```json
   "mcp_servers": {
     "orchestrator": {
       "type": "http",
       "url": "${runner.orchestrator_mcp_url}",
       "headers": {
         "X-Agent-Session-Id": "${runtime.session_id}"
       }
     }
   }
   ```

   After Coordinator resolution (in run payload):
   ```json
   "mcp_servers": {
     "orchestrator": {
       "type": "http",
       "url": "${runner.orchestrator_mcp_url}",
       "headers": {
         "X-Agent-Session-Id": "ses_abc123"
       }
     }
   }
   ```

   After Runner resolution (passed to executor):
   ```json
   "mcp_servers": {
     "orchestrator": {
       "type": "http",
       "url": "http://127.0.0.1:9999",
       "headers": {
         "X-Agent-Session-Id": "ses_abc123"
       }
     }
   }
   ```

   **Why `${runner.orchestrator_mcp_url}` is resolved at Runner:**

   The Orchestrator MCP server is embedded in the Runner (not a standalone service). The Runner assigns a dynamic port at startup, so only the Runner knows its own MCP URL. The `${runner.*}` prefix signals: "this value is Runner-specific - preserve it for Runner-level resolution."

   See [Placeholder Reference](../../reference/placeholder-reference.md) for full details.

**Files to create/modify:**
- `servers/agent-runner/lib/mcp_server.py` - New MCP server component
- `servers/agent-runner/agent-runner` - Start MCP server
- `servers/agent-runner/lib/executor.py` - Set MCP URL env var

---

### Phase 2b: MCP Proxy for External MCP Servers

**Goal:** Runner proxies ALL MCP traffic, not just orchestrator

**Architecture:**

```
Executor
    │
    │  (all MCP URLs point to Runner)
    ▼
Runner
    ├── /mcp/orchestrator   → handled internally (native)
    ├── /mcp/context-store  → proxy → Context Store MCP
    ├── /mcp/atlassian      → proxy → Atlassian MCP server
    └── /mcp/*              → proxy → configured MCP servers
```

**Why proxy everything through Runner:**

1. **Single interception point** - All MCP calls flow through one place in the code
2. **Future auth hook** - Can add authentication layer for external MCPs
3. **Executor isolation** - Executors don't know real MCP locations
4. **Centralized logging/monitoring** - Observe all MCP usage
5. **Distributed load** - Each Runner handles only its 4-5 executors (not centralized bottleneck)

**Runner placeholder:**

| Placeholder | Resolved By | Notes |
|-------------|-------------|-------|
| `${runner.orchestrator_mcp_url}` | Runner | Orchestrator MCP embedded in Runner |

The Runner resolves only `${runner.orchestrator_mcp_url}` - all other placeholders are resolved by Coordinator at run creation.

See `servers/agent-runner/lib/executor.py:210` for implementation.

**Open questions for Phase 2b:**

1. How does Runner know where to proxy each MCP? (config file? Coordinator registry?)
2. How to handle MCP server credentials when proxying?
3. Should proxy support both HTTP and stdio MCP backends?

---

### Phase 3: Context Enrichment

**Goal:** Runner's MCP adds metadata that executors don't have

**Enrichment opportunities:**

| Context | Source | Use Case |
|---------|--------|----------|
| `parent_session_id` | Session registry | Callback routing |
| `parent_agent_name` | Blueprint cache | Logging, permissions |
| `project_dir` | Run data | Inherit working directory |
| `runner_id` | Runner config | Debugging, affinity |
| `capability_tags` | Blueprint | Future: permission checking |

**Implementation:**

```python
async def handle_mcp_request(self, request, session_id: str):
    # Look up calling session's context
    context = self.get_session_context(session_id)

    # Enrich request
    enriched = {
        **request.dict(),
        "parent_session_id": session_id,
        "parent_agent_name": context.agent_name,
        "project_dir": request.project_dir or context.project_dir,
        # Future additions here - no executor changes needed
    }

    return await self.coordinator.create_run(**enriched)
```

---

## Migration Path

### Backward Compatibility

1. **Schema versioning** - Executor invocation uses `schema_version` field
2. **Gradual rollout** - Runner can detect executor capabilities
3. **External clients** - Use `--mcp-port` flag on Agent Runner to expose MCP endpoint

### Migration Steps

1. **Step 1:** Add schema version 2.0 support to executors (accept agent_blueprint)
2. **Step 2:** Runner resolves blueprints, passes both old and new format initially
3. **Step 3:** Remove blueprint resolution from executors
4. **Step 4:** Add MCP server to Runner
5. **Step 5:** Update agent blueprints to use Runner's MCP URL
6. **Step 6:** ✅ Standalone MCP server removed - embedded in Agent Runner

---

## Design Decisions

### Decided

1. **HTTP-only MCP servers**
   - The agent orchestration framework uses HTTP-based MCP servers only
   - Stdio MCP servers exist for external clients (Claude Desktop) but are not used within executor orchestration
   - This simplifies the architecture: Runner hosts HTTP MCP endpoint

2. **Blueprint resolution on every run (no caching)**
   - Blueprint is re-resolved for both start and resume
   - This ensures configuration changes take effect immediately
   - Future optimization possible but not planned

3. **System prompt handling**
   - Runner provides `agent_blueprint` with all fields (including `system_prompt`)
   - Executor passes `system_prompt` to `ClaudeAgentOptions.system_prompt` (not prepended to user message)
   - System prompt is only used for new sessions (`mode=start`), not for resume

4. **Scope: Orchestrator MCP native, other MCPs proxied**
   - **Orchestrator MCP**: Implemented directly in Runner (same domain - Runner already uses Sessions/Runs/Agents APIs)
   - **Other MCPs** (Atlassian, Context Store, etc.): Proxied through Runner
   - Executors never connect directly to any MCP server - all MCP traffic goes through Runner
   - This provides a single interception point for all MCP calls

### Open Questions

1. **Single Port vs Separate Ports**
   - Proxy on port X, MCP on port Y?
   - Or combine: proxy handles `/api/*`, MCP handles `/mcp/*`?

2. **MCP Server Framework**
   - Reuse existing FastMCP setup?
   - Or lightweight HTTP handlers in Runner?

3. **MCP Gateway Location: Runner (decided)**
   - All MCP traffic goes through Runner (not Coordinator)
   - Rationale: Distributed load - each Runner handles only its 4-5 executors, vs Coordinator handling all Runners × all executors
   - Runner = natural scale-out point for MCP traffic

   **Open:** Authentication for external MCP servers
   - How to authenticate with external MCPs (Atlassian, etc.) when proxying?
   - Options: Runner holds credentials, per-MCP M2M, credential injection
   - Decision deferred

4. **executor_session_id for Resume**
   - Currently: Executor fetches it itself via session API
   - Options: Include in Run object? Runner fetches and passes? Executor continues to fetch?
   - Needs decision as part of the executor interface redesign

---

## Summary

| Aspect | Before | Now |
|--------|--------|-----|
| Blueprint resolution | Executor | Coordinator (at run creation) |
| Placeholder resolution | Executor | Coordinator + Runner (`${runner.*}` only) |
| Orchestrator MCP | Standalone | Native in Runner |
| Other MCPs | Direct executor connection | Proxied through Runner |
| Authentication | None (or separate M2M) | Uses Runner's M2M |
| Context passing | Env vars, limited | Centralized, extensible |
| Executor complexity | High | Low (thin wrapper) |
| Adding new context | Requires executor changes | Coordinator/Runner changes |
| MCP interception | Not possible | Single point in Runner |

This architecture aligns with the principle established in the auth cleanup: **the Runner is the authentication and orchestration boundary; executors are framework-specific adapters that don't handle infrastructure concerns.**
