# MCP Server Registry

**Status:** Draft
**Date:** 2026-01-25

## Overview

A centralized registry for MCP server definitions with framework-controlled HTTP header injection. The registry provides a single source of truth for MCP server URLs and defines what headers each server accepts. Headers are resolved through an inheritance chain and injected by the framework—the LLM cannot influence them.

**Key Principles:**

1. MCP server URLs defined once in registry, referenced by name elsewhere
2. Header schemas document what headers each server accepts (for UI/validation)
3. Header values flow through inheritance chain: Registry → Capability → Agent → Run → Parent
4. Framework injects headers at HTTP transport level—LLM never sees them
5. Simple key-value headers for auth and scoping (no JWT complexity for most servers)
6. Orchestrator MCP remains special case with Auth0 M2M

## Problem Statement

### Current State

MCP server configurations are scattered across agent and capability configs with hardcoded URLs:

```
config/agents/atlassian-agent/agent.mcp.json:
  "url": "http://localhost:9000/mcp"

config/agents/neo4j-agent/agent.mcp.json:
  "url": "http://localhost:9003/mcp/"

config/capabilities/neo4j-knowledge-graph/capability.mcp.json:
  "url": "http://localhost:9003/mcp/"
```

### Problems

| Problem | Impact |
|---------|--------|
| **Scattered URLs** | Changing a URL (e.g., localhost → production) requires editing multiple files |
| **No central management** | No single view of "what MCP servers exist and where they are" |
| **Limited header support** | Only `${AGENT_SESSION_ID}` and `${AGENT_ORCHESTRATOR_MCP_URL}` placeholders exist |
| **No scoping mechanism** | Cannot scope MCP server access (e.g., limit Jira to specific projects) |
| **No generic auth** | Each MCP server handles auth differently, no unified pattern |
| **Config duplication** | Same MCP server definition copied across agents/capabilities |

### Use Cases Not Currently Supported

1. **Context Store scoping**: Agent should only see documents tagged with `project-123`
2. **Atlassian scoping**: Agent should only access Jira projects `ALPHA` and `BETA`
3. **Neo4j partitioning**: Agent should only query subgraph `team-alpha`
4. **API key auth**: MCP server requires `X-API-Key` header for access
5. **Multi-environment**: Same agent config works in dev (localhost) and prod (different URLs)

## What This Design Solves

| Solved | How |
|--------|-----|
| **Centralized URL management** | Registry is single source of truth for all MCP server URLs |
| **Framework-controlled headers** | Headers injected at HTTP level, LLM cannot influence |
| **Flexible scoping** | Any header can be used for scoping (X-Context-Scope, X-Jira-Projects, etc.) |
| **Simple auth pattern** | Auth via configurable headers (X-API-Key, Authorization, custom) |
| **Multi-level configuration** | Capability sets defaults, agent overrides, run overrides further |
| **UI-friendly** | Header schemas enable form-based editing in Dashboard |
| **Reduced duplication** | Define MCP server once, reference by name |

## What This Design Does NOT Solve

| Not Solved | Why | Future Work |
|------------|-----|-------------|
| **Dynamic token acquisition** | Adds complexity; only Orchestrator MCP needs this | Extend auth types later |
| **Client-provided credentials** | Run endpoint doesn't accept client auth yet | Add to run API later |
| **Secret store integration** | Keep config simple for now | Add vault/secret manager integration |
| **MCP server discovery** | Out of scope | Service mesh / discovery pattern |
| **Per-request scoping** | Too complex, per-session is sufficient | Not planned |
| **Cross-MCP-server policies** | E.g., "if accessing Jira, must also log to audit" | Not planned |

## Design

### Data Model

#### MCP Server Registry Entry

Stored in Coordinator database, managed via API/Dashboard.

```json
{
  "id": "context-store",
  "name": "Context Store",
  "description": "Document storage for agent context",
  "url": "http://localhost:9501/mcp",
  "header_schema": {
    "X-Context-Namespace": {
      "type": "string",
      "description": "Namespace for document isolation",
      "required": true
    },
    "X-Context-Scope-Filters": {
      "type": "json",
      "description": "JSON object with scope filters (e.g., root_session_id)",
      "required": false
    },
    "X-API-Key": {
      "type": "string",
      "description": "API key for authentication",
      "required": false,
      "sensitive": true
    }
  },
  "default_headers": {
    "X-Context-Namespace": "default"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier, used in references |
| `name` | string | Human-readable name |
| `description` | string | What this MCP server provides |
| `url` | string | Base URL for MCP HTTP transport |
| `header_schema` | object | Defines accepted headers with type, description, required flag |
| `default_headers` | object | Default header values (can be overridden) |

#### Header Schema Field Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | string | `"string"`, `"json"`, `"boolean"`, `"number"` |
| `description` | string | Explains what the header controls |
| `required` | boolean | If true, must be provided at some level |
| `sensitive` | boolean | If true, value hidden in UI, not logged |
| `example` | string | Example value for documentation |

#### MCP Server Reference (in Capability/Agent)

Instead of full MCP config, capabilities and agents **reference** the registry:

**Old format (current):**
```json
{
  "mcpServers": {
    "context-store-http": {
      "type": "http",
      "url": "http://localhost:9501/mcp"
    }
  }
}
```

**New format (with registry):**
```json
{
  "mcpServers": {
    "context-store": {
      "ref": "context-store",
      "headers": {
        "X-Context-Namespace": "project-alpha"
      }
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ref` | string | References registry entry by ID |
| `headers` | object | Header values to set/override at this level |

### Header Resolution Chain

Headers are resolved through an inheritance chain. Later sources override earlier ones.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Header Resolution Chain                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   1. Registry defaults          {"X-Context-Namespace": "default"}          │
│              │                                                               │
│              ▼                                                               │
│   2. Capability headers         {"X-Context-Namespace": "shared-knowledge"} │
│              │                                                               │
│              ▼                                                               │
│   3. Agent headers              {"X-Context-Namespace": "project-alpha"}    │
│              │                                                               │
│              ▼                                                               │
│   4. Run request headers        {"X-Context-Namespace": "project-beta"}     │
│              │                                                               │
│              ▼                                                               │
│   5. Parent session inherit     (child inherits parent's resolved headers)  │
│              │                                                               │
│              ▼                                                               │
│   Final: {"X-Context-Namespace": "project-beta"}                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Resolution Rules

| Rule | Behavior |
|------|----------|
| **Override** | Later value replaces earlier value for same header |
| **Remove** | Set header to `null` to explicitly remove it |
| **Merge (objects)** | For `type: "json"` headers, shallow merge by default |
| **Inherit** | Child sessions inherit parent's final resolved headers |

#### Example Resolution

```
Registry (context-store):
  default_headers:
    X-Context-Namespace: "default"
    X-API-Key: "registry-key"

Capability (research-tools):
  headers:
    X-Context-Namespace: "research"

Agent (project-researcher):
  headers:
    X-Context-Namespace: "project-alpha"
    X-Context-Scope-Filters: {"department": "engineering"}

Run request:
  mcp_headers:
    context-store:
      X-Context-Scope-Filters: {"team": "platform"}

─────────────────────────────────────────────────

Final resolved headers:
  X-Context-Namespace: "project-alpha"       (from agent, overrode capability)
  X-API-Key: "registry-key"                  (from registry default)
  X-Context-Scope-Filters: {"team": "platform"}  (from run, overrode agent)
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Coordinator                               │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    MCP Server Registry                                 │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │  │
│  │  │context-store│ │  atlassian  │ │   neo4j     │ │orchestrator*│     │  │
│  │  │ URL, Schema │ │ URL, Schema │ │ URL, Schema │ │ (special)   │     │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Blueprint Resolver                                  │  │
│  │  1. Load agent + capabilities                                          │  │
│  │  2. For each MCP ref: lookup registry, get URL                         │  │
│  │  3. Merge headers: registry → capability → agent                       │  │
│  │  4. Return blueprint with resolved MCP configs                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    │ GET /agents/{name}                     │
│                                    │ Returns: resolved mcp_servers          │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Runner                                    │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Run-Level Resolution                                │  │
│  │  1. Receive blueprint from Coordinator                                 │  │
│  │  2. Apply run-level mcp_headers overrides                              │  │
│  │  3. Apply parent session inheritance (for sub-agents)                  │  │
│  │  4. Replace placeholders (${AGENT_SESSION_ID}, etc.)                   │  │
│  │  5. Pass fully resolved config to executor                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  * Orchestrator MCP embedded here (special case with Auth0 M2M)             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ Executor invokes Claude Code
                                     │ with resolved mcp_servers config
                                     ▼
     ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
     │  Context Store   │   │    Atlassian     │   │      Neo4j       │
     │   :9501/mcp      │   │    :9000/mcp     │   │    :9003/mcp     │
     │                  │   │                  │   │                  │
     │ Headers:         │   │ Headers:         │   │ Headers:         │
     │ X-Context-*      │   │ X-Jira-Projects  │   │ X-Neo4j-*        │
     │ X-API-Key        │   │ X-API-Key        │   │ X-API-Key        │
     └──────────────────┘   └──────────────────┘   └──────────────────┘
```

### Special Case: Orchestrator MCP

The Agent Orchestrator MCP server is embedded in the Agent Runner and has special requirements:

| Aspect | Regular MCP Servers | Orchestrator MCP |
|--------|---------------------|------------------|
| **Location** | External service | Embedded in Runner |
| **URL** | Static in registry | Dynamic port, injected via placeholder |
| **Auth** | Simple headers | Auth0 M2M (shared with Runner) |
| **Session context** | Via headers | Via `X-Agent-Session-Id` header |

The Orchestrator MCP **can** be in the registry for documentation purposes, but its URL and auth are handled specially:

```json
{
  "id": "orchestrator",
  "name": "Agent Orchestrator",
  "description": "Spawn and manage sub-agents",
  "url": "${AGENT_ORCHESTRATOR_MCP_URL}",
  "auth_type": "auth0_m2m",
  "header_schema": {
    "X-Agent-Session-Id": {
      "type": "string",
      "description": "Parent session ID for callback context",
      "required": true,
      "internal": true
    }
  }
}
```

The `auth_type: "auth0_m2m"` and `internal: true` flags indicate special framework handling.

## API Design

### Registry CRUD Endpoints

```
GET    /mcp-servers                    List all MCP server definitions
POST   /mcp-servers                    Create new MCP server definition
GET    /mcp-servers/{id}               Get MCP server by ID
PUT    /mcp-servers/{id}               Update MCP server definition
DELETE /mcp-servers/{id}               Delete MCP server definition
```

#### Create/Update MCP Server

```json
POST /mcp-servers
{
  "id": "atlassian",
  "name": "Atlassian (Jira + Confluence)",
  "description": "Access Jira issues and Confluence pages",
  "url": "http://localhost:9000/mcp",
  "header_schema": {
    "X-Jira-Projects": {
      "type": "string",
      "description": "Comma-separated Jira project keys",
      "required": false,
      "example": "PROJ-A,PROJ-B"
    },
    "X-Confluence-Spaces": {
      "type": "string",
      "description": "Comma-separated Confluence space keys",
      "required": false,
      "example": "DEV,DOCS"
    },
    "X-API-Key": {
      "type": "string",
      "description": "API key for Atlassian access",
      "required": true,
      "sensitive": true
    }
  },
  "default_headers": {
    "X-API-Key": "${ATLASSIAN_API_KEY}"
  }
}
```

### Run Creation with MCP Headers

```json
POST /runs
{
  "type": "start_session",
  "agent_name": "project-researcher",
  "prompt": "Research the API design",
  "mcp_headers": {
    "context-store": {
      "X-Context-Namespace": "project-beta",
      "X-Context-Scope-Filters": {"sprint": "sprint-5"}
    },
    "atlassian": {
      "X-Jira-Projects": "BETA,BETA-OPS"
    }
  }
}
```

### Resolved Blueprint Response

```json
GET /agents/project-researcher
{
  "name": "project-researcher",
  "system_prompt": "...",
  "mcp_servers": {
    "context-store": {
      "type": "http",
      "url": "http://localhost:9501/mcp",
      "headers": {
        "X-Context-Namespace": "project-alpha",
        "X-Context-Scope-Filters": "{\"department\": \"engineering\"}",
        "X-API-Key": "${CONTEXT_STORE_API_KEY}"
      }
    },
    "atlassian": {
      "type": "http",
      "url": "http://localhost:9000/mcp",
      "headers": {
        "X-Jira-Projects": "ALPHA",
        "X-API-Key": "${ATLASSIAN_API_KEY}"
      }
    }
  }
}
```

Note: Environment variable placeholders (`${VAR}`) are resolved by the Runner/Executor, not the Coordinator.

## Configuration Examples

### Example 1: Context Store with Scoping

**Registry entry:**
```json
{
  "id": "context-store",
  "url": "http://localhost:9501/mcp",
  "header_schema": {
    "X-Context-Namespace": {"type": "string", "required": true},
    "X-Context-Scope-Filters": {"type": "json", "required": false}
  },
  "default_headers": {
    "X-Context-Namespace": "default"
  }
}
```

**Capability (research-capability):**
```json
{
  "mcpServers": {
    "docs": {
      "ref": "context-store",
      "headers": {
        "X-Context-Namespace": "research-docs"
      }
    }
  }
}
```

**Agent (sprint-researcher):**
```json
{
  "capabilities": ["research-capability"],
  "mcpServers": {
    "docs": {
      "headers": {
        "X-Context-Scope-Filters": {"type": "sprint-artifact"}
      }
    }
  }
}
```

**Run request:**
```json
{
  "agent_name": "sprint-researcher",
  "mcp_headers": {
    "docs": {
      "X-Context-Scope-Filters": {"sprint_id": "sprint-42"}
    }
  }
}
```

**Final resolved:**
```json
{
  "docs": {
    "type": "http",
    "url": "http://localhost:9501/mcp",
    "headers": {
      "X-Context-Namespace": "research-docs",
      "X-Context-Scope-Filters": "{\"sprint_id\": \"sprint-42\"}"
    }
  }
}
```

### Example 2: Atlassian with Project Scoping

**Registry entry:**
```json
{
  "id": "atlassian",
  "url": "http://localhost:9000/mcp",
  "header_schema": {
    "X-Jira-Projects": {"type": "string", "required": false},
    "X-Confluence-Spaces": {"type": "string", "required": false},
    "X-API-Key": {"type": "string", "required": true, "sensitive": true}
  },
  "default_headers": {
    "X-API-Key": "${ATLASSIAN_API_KEY}"
  }
}
```

**Agent (alpha-project-assistant):**
```json
{
  "mcpServers": {
    "jira": {
      "ref": "atlassian",
      "headers": {
        "X-Jira-Projects": "ALPHA,ALPHA-OPS",
        "X-Confluence-Spaces": null
      }
    }
  }
}
```

This agent can only access ALPHA projects and has no Confluence access (header explicitly removed).

### Example 3: Multiple Agents Sharing Same MCP Server

Three agents share the same Neo4j server but with different scopes:

**Registry:**
```json
{
  "id": "neo4j",
  "url": "http://localhost:9003/mcp/",
  "header_schema": {
    "X-Neo4j-Partition": {"type": "string", "required": false}
  }
}
```

**Agents:**
```json
// team-alpha-analyst
{"mcpServers": {"kg": {"ref": "neo4j", "headers": {"X-Neo4j-Partition": "team-alpha"}}}}

// team-beta-analyst
{"mcpServers": {"kg": {"ref": "neo4j", "headers": {"X-Neo4j-Partition": "team-beta"}}}}

// global-analyst
{"mcpServers": {"kg": {"ref": "neo4j", "headers": {}}}}  // No partition = full access
```

## MCP Server Implementation Requirements

For MCP servers to support this pattern, they must:

1. **Read scoping headers** from HTTP request
2. **Apply filtering** based on header values
3. **Reject/limit** access when required headers are missing (if enforcing)

### Example: Context Store MCP Server

```python
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request

mcp = FastMCP("context-store")

def get_scope_from_headers(request: Request) -> dict:
    """Extract scope from HTTP headers."""
    return {
        "namespace": request.headers.get("x-context-namespace", "default"),
        "scope_filters": json.loads(
            request.headers.get("x-context-scope-filters", "{}")
        )
    }

@mcp.tool()
async def list_documents(tags: list[str] = None):
    request = get_current_request()
    scope = get_scope_from_headers(request)

    # Query scoped to namespace and filters
    docs = await db.query_documents(
        namespace=scope["namespace"],
        scope_filters=scope["scope_filters"],
        tags=tags  # User/LLM-provided filter
    )
    return docs
```

### Example: Atlassian MCP Server

```python
@mcp.tool()
async def search_issues(jql: str):
    request = get_current_request()
    allowed_projects = request.headers.get("x-jira-projects", "").split(",")

    if allowed_projects and allowed_projects[0]:
        # Inject project filter into JQL
        project_filter = f"project IN ({','.join(allowed_projects)})"
        jql = f"({jql}) AND {project_filter}"

    return await jira_client.search(jql)
```

## Dashboard Integration

### MCP Servers Management Page

New page for CRUD operations on MCP server registry:

- **List View**: Table with ID, name, URL, header count
- **Create/Edit Form**:
  - ID field (validated, immutable after creation)
  - Name, description
  - URL field
  - Header schema editor (add/remove headers with type, description, flags)
  - Default headers editor

### Capability/Agent Edit Forms

Updated forms with MCP server selection:

- **MCP Servers Section**:
  - Dropdown to select from registry
  - For each selected server, show header fields based on schema
  - Form fields rendered based on header type (string input, JSON editor, checkbox)
  - Sensitive fields shown as password inputs

### Visual Indicator for Resolution

Show inheritance chain in UI:

```
┌─────────────────────────────────────────────────────┐
│ MCP Server: context-store                           │
├─────────────────────────────────────────────────────┤
│ X-Context-Namespace                                 │
│ ┌─────────────────────────────────────────────────┐ │
│ │ [project-alpha]                                 │ │
│ │ ↑ Overrides: capability (research-docs)         │ │
│ │ ↑ Default: default                             │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ X-Context-Scope-Filters                             │
│ ┌─────────────────────────────────────────────────┐ │
│ │ [{"department": "engineering"}]                │ │
│ │ ↑ From: this agent                             │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Migration Strategy

### Phase 1: Registry Infrastructure (Backward Compatible)

1. Add `mcp_servers` table to Coordinator database
2. Add CRUD API endpoints
3. Add Dashboard page for registry management
4. Seed registry with current hardcoded MCP servers

Existing agent/capability configs continue to work unchanged.

### Phase 2: Reference Support

1. Update Blueprint Resolver to handle `ref` syntax
2. Support both old (inline URL) and new (ref) formats
3. Update Dashboard to offer ref-based configuration
4. Migrate existing configs to use refs (optional)

### Phase 3: Header Resolution

1. Implement header inheritance chain in Blueprint Resolver
2. Add `mcp_headers` to run creation API
3. Update Runner to apply run-level headers
4. Implement parent session inheritance

### Phase 4: Deprecate Inline URLs

1. Warn when inline URLs used in agent/capability configs
2. Dashboard defaults to ref-based configuration
3. Migration tooling to convert inline to refs

## Limitations

| Limitation | Rationale |
|------------|-----------|
| **No per-request scoping** | Session-level scoping is sufficient; per-request adds complexity |
| **No header validation at runtime** | MCP servers responsible for validating their headers |
| **No cross-server policies** | Keep it simple; can add policy layer later if needed |
| **Simple merge (last wins)** | Complex merge strategies add cognitive load |
| **Environment vars resolved by Runner** | Coordinator doesn't have access to Runner's env |

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| **Sensitive headers in config** | Mark as `sensitive: true`, UI hides value, not logged |
| **LLM accessing headers** | Headers injected at HTTP level, not exposed to LLM |
| **Header spoofing** | Framework controls headers; LLM tool params don't include headers |
| **Credential exposure** | Use env var placeholders, resolved at runtime |

## Future Considerations

### Dynamic Auth Providers

Extend registry to support dynamic token acquisition:

```json
{
  "id": "external-api",
  "auth": {
    "type": "oauth2_client_credentials",
    "token_url": "https://auth.example.com/token",
    "client_id": "${EXTERNAL_CLIENT_ID}",
    "client_secret": "${EXTERNAL_CLIENT_SECRET}",
    "scope": "api:read api:write"
  }
}
```

### Client-Provided Credentials

Allow run endpoint to accept client credentials:

```json
POST /runs
{
  "agent_name": "analyst",
  "credentials": {
    "atlassian": {"api_key": "user-provided-key"}
  }
}
```

### Secret Store Integration

Reference secrets by name instead of env vars:

```json
{
  "default_headers": {
    "X-API-Key": {"$secret": "atlassian-api-key"}
  }
}
```

## Related Documents

- [Context Store Scoping](../context-store-scoping/context-store-scoping.md) - Namespace/scope_filters design for Context Store
- [External Service Token Architecture](../external-service-auth/external-service-token-architecture-with-scoping.md) - JWT-based alternative (for comparison)
- [Capabilities System](../../features/capabilities-system.md) - How capabilities reference MCP servers
