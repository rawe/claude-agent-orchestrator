# Agent Visibility Architecture

> **Status: DEPRECATED**
>
> This document describes the previous visibility system that has been replaced by the more flexible **Tags System**.
> See [Agent Management](./agent-management.md) for the current architecture.
>
> **Migration:** `visibility: "public"` → `tags: ["external"]`, `visibility: "internal"` → `tags: ["internal"]`, `visibility: "all"` → `tags: ["external", "internal"]`

---

**HISTORICAL DOCUMENTATION BELOW**

---

This document describes the two-level agent visibility system that controls which agents are discoverable in different contexts (external clients vs. internal framework).

## Overview

The agent visibility system introduces a `visibility` property on agent blueprints that determines where an agent can be discovered and used. This is separate from the `status` field (active/inactive) which remains an operational toggle.

### Key Distinction

| Property | Purpose | Nature |
|----------|---------|--------|
| `visibility` | Defines **who** can discover the agent | Intrinsic property (rarely changes) |
| `status` | Defines **if** the agent is currently available | Operational toggle (can change anytime) |

## Visibility Values

| Value | Description | External Context | Internal Context |
|-------|-------------|------------------|------------------|
| `public` | Entry-point agents for external clients (users, Claude Desktop) | Visible | Hidden |
| `internal` | Worker/specialist agents for orchestration framework | Hidden | Visible |
| `all` | Utility agents needed in both contexts | Visible | Visible |

**Default**: If `visibility` is omitted from `agent.json`, the agent defaults to `"all"` for backward compatibility (visible in both contexts, matching pre-feature behavior).

### Context Definitions

- **External Context**: Clients outside the framework (Claude Desktop, MCP clients, end users via dashboard)
- **Internal Context**: Agents spawned by the orchestration framework (sub-agents, workers)

### Design Rationale

This is NOT a simple hierarchy where "internal sees everything". The contexts are separate audiences:

- External clients should only see entry-point agents (`public` + `all`)
- Internal orchestrators should only see worker agents (`internal` + `all`)
- This prevents internal agents from accidentally using public-facing agents, avoiding recursion and confusion

## Agent Configuration

The `visibility` property is defined in the agent's `agent.json` file:

```json
{
  "name": "jira-researcher",
  "description": "Specialist for Jira research tasks",
  "visibility": "internal"
}
```

### Example Agent Configuration

| Agent | Visibility | External Sees | Internal Sees |
|-------|------------|---------------|---------------|
| `agent-orchestrator` | `public` | Yes | No |
| `simple-agent` | `public` | Yes | No |
| `jira-researcher` | `internal` | No | Yes |
| `web-researcher` | `internal` | No | Yes |
| `confluence-researcher` | `internal` | No | Yes |
| `context-store-agent` | `all` | Yes | Yes |

## Filtering Logic Matrix

```
┌─────────────────┬──────────────┬──────────────┬────────────────┐
│ visibility      │ context=     │ context=     │ context=       │
│                 │ external     │ internal     │ none (mgmt)    │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ public          │ Shown        │ Hidden       │ Shown          │
│ internal        │ Hidden       │ Shown        │ Shown          │
│ all             │ Shown        │ Shown        │ Shown          │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ + status filter │ active only  │ active only  │ all statuses   │
└─────────────────┴──────────────┴──────────────┴────────────────┘
```

- **`context=external`**: Returns agents with `visibility` in (`public`, `all`) AND `status` = `active`
- **`context=internal`**: Returns agents with `visibility` in (`internal`, `all`) AND `status` = `active`
- **`context=none`** (default): Returns all agents regardless of visibility (for management UI)

---

## Affected Components

### 1. Backend: Agent Storage

**File**: `servers/agent-runtime/agent_storage.py`

**Changes**:
- Read `visibility` field from `agent.json`
- Default to `"public"` if not present
- Include in Agent model returned by `_read_agent_from_dir()`

### 2. Backend: Data Models

**File**: `servers/agent-runtime/models.py`

**Changes**:
- Add `visibility` field to `Agent` model:

```python
class Agent(AgentBase):
    # ... existing fields
    visibility: Literal["public", "internal", "all"] = "all"
    status: Literal["active", "inactive"] = "active"
```

- Add `AgentCreate` and `AgentUpdate` models to include optional `visibility` field

### 3. Backend: API Endpoint

**File**: `servers/agent-runtime/main.py`

**Changes**:
- Add `context` query parameter to `GET /agents` endpoint:

```python
@app.get("/agents")
def list_agents(
    context: Optional[Literal["external", "internal"]] = Query(
        default=None,
        description="Filter by visibility context. None returns all agents."
    )
):
    agents = agent_storage.list_agents()

    if context == "external":
        agents = [a for a in agents if a.visibility in ("public", "all")]
    elif context == "internal":
        agents = [a for a in agents if a.visibility in ("internal", "all")]

    return agents
```

No new endpoints are created. The existing `/agents` endpoint is extended with the optional query parameter.

---

### 4. MCP Server

**Files**:
- `mcps/agent-orchestrator/libs/constants.py`
- `mcps/agent-orchestrator/libs/core_functions.py`
- `mcps/agent-orchestrator/libs/server.py`

The MCP server needs to know which context it's operating in to filter agents appropriately.

#### HTTP Mode: Header Configuration

A new HTTP header is introduced following the existing pattern for `X-Agent-Session-Name`:

**New constant** in `constants.py`:
```python
# HTTP Header for visibility context (in HTTP mode)
HEADER_AGENT_VISIBILITY_CONTEXT = "X-Agent-Visibility-Context"

# Environment variable for visibility context (in stdio mode)
ENV_AGENT_VISIBILITY_CONTEXT = "AGENT_VISIBILITY_CONTEXT"
```

**MCP template** in `dashboard/src/utils/mcpTemplates.ts`:
```typescript
'agent-orchestrator-http': {
  type: 'http',
  url: 'http://localhost:9500/mcp',
  headers: {
    'X-Agent-Session-Name': '${AGENT_SESSION_NAME}',
    'X-Agent-Visibility-Context': '${AGENT_VISIBILITY_CONTEXT}',
  },
},
```

The `${AGENT_VISIBILITY_CONTEXT}` placeholder is replaced at runtime, similar to `${AGENT_SESSION_NAME}`.

#### STDIO Mode: Environment Variable

For stdio transport, the context is passed via environment variable:

```bash
AGENT_VISIBILITY_CONTEXT=external  # For Claude Desktop / external clients
AGENT_VISIBILITY_CONTEXT=internal  # For internal framework agents
```

#### Context Retrieval

**New function** in `core_functions.py`:
```python
def get_visibility_context(http_headers: Optional[dict] = None) -> Optional[str]:
    """
    Get visibility context from environment or HTTP headers.

    - stdio mode: reads from AGENT_VISIBILITY_CONTEXT env var
    - HTTP mode: reads from X-Agent-Visibility-Context header

    Returns: "external", "internal", or None (defaults to "external" if not set)
    """
    if http_headers:
        header_key_lower = HEADER_AGENT_VISIBILITY_CONTEXT.lower()
        context = http_headers.get(header_key_lower)
        if context:
            return context

    return os.environ.get(ENV_AGENT_VISIBILITY_CONTEXT, "external")
```

#### Implementation in `list_agent_blueprints_impl`

```python
async def list_agent_blueprints_impl(
    config: ServerConfig,
    response_format: Literal["markdown", "json"] = "markdown",
    http_headers: Optional[dict] = None,
) -> str:
    """List available agent blueprints filtered by visibility context."""

    context = get_visibility_context(http_headers)

    client = get_api_client(config)
    agents = await client.list_agents(context=context)

    # Further filter to active agents only
    active_agents = [a for a in agents if a.get("status") == "active"]

    # ... rest of formatting logic
```

---

### 5. Skills: ao-list-blueprints

**File**: `plugins/orchestrator/skills/orchestrator/commands/ao-list-blueprints`

**Changes**:
- Add optional `--context` flag to specify visibility context
- Default to `"internal"` when called from within the orchestrator framework

```python
@app.command()
def main(
    context: str = typer.Option(
        "internal",
        "--context", "-c",
        help="Visibility context: 'external' or 'internal'"
    )
):
    agents = list_agents_api(context=context)
    # ... display logic
```

**Changes to `agent_api.py`**:
```python
def list_agents_api(context: str = "internal") -> list[dict]:
    """
    List agents from API filtered by visibility context.

    Args:
        context: "external" or "internal" (default: "internal")
    """
    result = _request("GET", f"/agents?context={context}")
    return [a for a in result if a.get("status") == "active"]
```

### 6. Skills: ao-start and ao-resume (NO CHANGES)

**Important Design Decision**: The `ao-start` and `ao-resume` commands do NOT implement visibility filtering.

**Rationale**:
- If a client doesn't know about an agent (because it was filtered out during listing), it cannot attempt to start/resume a session with that agent
- The filtering happens at discovery time (`ao-list-blueprints`), not at execution time
- This simplifies the implementation and avoids redundant checks
- If an agent name is known and passed to `ao-start`, it should work regardless of visibility

---

### 7. Dashboard: Frontend Types

**File**: `dashboard/src/types/agent.ts`

**Changes**:
```typescript
export type AgentVisibility = 'public' | 'internal' | 'all';

export interface Agent {
  name: string;
  description: string;
  system_prompt: string | null;
  mcp_servers: Record<string, MCPServerConfig> | null;
  skills: string[] | null;
  visibility: AgentVisibility;  // New field
  status: AgentStatus;
  created_at: string;
  modified_at: string;
}
```

### 8. Dashboard: Agent Manager Page

**File**: `dashboard/src/pages/AgentManager.tsx`

**Changes**:
- Display `visibility` column in agent table
- Show visibility badge with distinct styling (e.g., colored chips: public=blue, internal=orange, all=green)
- No context filtering - shows ALL agents for management purposes

### 9. Dashboard: Agent Editor

**File**: `dashboard/src/components/features/agents/AgentEditor.tsx`

**Changes**:
- Add `visibility` field to the agent editor form
- Implement as a dropdown/select with three options:
  - `all` - "All Contexts (default)"
  - `public` - "External Only (Claude Desktop, users)"
  - `internal` - "Internal Only (orchestrator framework)"
- Field should be editable for both new and existing agents
- Include help text explaining each option

**UI Mockup**:
```
┌─────────────────────────────────────────────────────┐
│ Agent Editor                                        │
├─────────────────────────────────────────────────────┤
│ Name:        [jira-researcher        ]              │
│ Description: [Specialist for Jira... ]              │
│                                                     │
│ Visibility:  [ Internal Only        ▼]              │
│              ┌─────────────────────────┐            │
│              │ All Contexts (default)  │            │
│              │ External Only           │            │
│              │ Internal Only         ← │            │
│              └─────────────────────────┘            │
│                                                     │
│ ℹ️ Controls where this agent can be discovered:     │
│   • External: Claude Desktop, MCP clients, users   │
│   • Internal: Orchestrator framework, sub-agents   │
│                                                     │
│ System Prompt: [                     ]              │
│ MCP Servers:   [+ Add Template      ▼]              │
│ Skills:        [                     ]              │
├─────────────────────────────────────────────────────┤
│                          [Cancel] [Save]            │
└─────────────────────────────────────────────────────┘
```

### 10. Dashboard: Chat Page

**File**: `dashboard/src/pages/Chat.tsx`

**Changes**:
- Use `context=external` when fetching blueprints for the dropdown
- Only show `public` and `all` agents to end users

```typescript
// Fetch with external context
const blueprints = await agentService.listAgents('external');

// Filter in dropdown (redundant but safe)
.filter((bp) => bp.status === 'active' && bp.visibility !== 'internal')
```

### 11. Dashboard: Agent Service

**File**: `dashboard/src/services/agentService.ts`

**Changes**:
```typescript
async listAgents(context?: 'external' | 'internal'): Promise<Agent[]> {
  const params = context ? `?context=${context}` : '';
  const response = await api.get<Agent[]>(`/agents${params}`);
  return response.data;
}
```

---

## Configuration Examples

### External Client (Claude Desktop)

When configuring the MCP server for Claude Desktop, set the visibility context to `external`:

**HTTP Configuration** (in `agent.mcp.json` or MCP config):
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "type": "http",
      "url": "http://localhost:9500/mcp",
      "headers": {
        "X-Agent-Session-Name": "${AGENT_SESSION_NAME}",
        "X-Agent-Visibility-Context": "external"
      }
    }
  }
}
```

**STDIO Configuration** (in Claude Desktop config):
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "python",
      "args": ["-m", "mcps.agent-orchestrator"],
      "env": {
        "AGENT_VISIBILITY_CONTEXT": "external"
      }
    }
  }
}
```

### Internal Agent (Orchestrator Spawning Sub-Agents)

When the orchestrator framework spawns agents internally:

**Agent's MCP config** (`agent.mcp.json`):
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "type": "http",
      "url": "http://localhost:9500/mcp",
      "headers": {
        "X-Agent-Session-Name": "${AGENT_SESSION_NAME}",
        "X-Agent-Visibility-Context": "internal"
      }
    }
  }
}
```

---

## Migration Path

1. **Phase 1**: Add `visibility` field to backend models with default `"public"`
2. **Phase 2**: Update API to support `context` query parameter
3. **Phase 3**: Update MCP server to read context from headers/env
4. **Phase 4**: Update skills (`ao-list-blueprints`) to use context
5. **Phase 5**: Update dashboard to display and filter by visibility
6. **Phase 6**: Add visibility to existing agent configurations as needed

Existing agents without a `visibility` field will default to `"all"`, maintaining backward compatibility (visible everywhere, just like before this feature).

---

## Summary

This architecture enables a clean separation between:
- **Public agents**: Entry points for external users
- **Internal agents**: Worker agents for the orchestration framework
- **All agents**: Utilities needed in both contexts

The visibility is an intrinsic property of the agent defined in `agent.json`, filtered at the API level via query parameter, and communicated to the MCP server via HTTP headers (for HTTP transport) or environment variables (for STDIO transport).
