# MCP Server Registry

**Status:** Draft
**Date:** 2026-01-26

## Overview

A centralized registry for MCP server definitions with framework-controlled configuration injection. The registry provides a single source of truth for MCP server URLs and defines what configuration each server accepts. Configuration values are resolved through an inheritance chain and injected by the framework at the transport level—the LLM cannot influence them.

**Key Principles:**

1. MCP server URLs defined once in registry, referenced by name elsewhere
2. Config schemas document what configuration each server accepts (for UI/validation)
3. Config values flow through inheritance chain: Registry → Capability → Agent
4. Placeholders resolved at Coordinator level using params, scope, env, and runtime sources
5. Fully resolved configuration included in run payload to Runner
6. Framework injects configuration at transport level—LLM never sees them
7. Simple key-value configuration for auth and scoping

## Run Scope

Run scope provides framework-controlled values that flow through agent execution without LLM visibility. Unlike agent parameters (which the LLM sees and uses), run scope values are invisible to the LLM and are used exclusively for framework concerns like scoping, correlation, and authentication.

### Characteristics

| Property | Description |
|----------|-------------|
| **LLM-invisible** | Values never exposed to the LLM context |
| **Provided at run creation** | Caller supplies scope when starting a run |
| **Not persisted to session** | Must be provided fresh for each run |
| **Inherited by child runs** | When an agent spawns sub-agents, scope is automatically inherited |
| **Used in config mappings** | Values can be mapped to MCP server configuration |

### Use Cases

| Key | Purpose |
|-----|---------|
| `context_id` | Scope MCP server access (e.g., limit Context Store to specific documents) |
| `workflow_id` | Correlate related runs across systems |
| Credentials | Pass authentication tokens to MCP servers without LLM exposure |

### Example

```json
POST /runs
{
  "agent_name": "researcher",
  "params": {"topic": "API design"},
  "scope": {
    "context_id": "ctx-123",
    "workflow_id": "wf-456"
  }
}
```

The `params.topic` is visible to the LLM. The `scope.context_id` and `scope.workflow_id` are not.

## Placeholder Sources

Config values in MCP server configurations can reference dynamic values using placeholder syntax: `${source.key}`. The Coordinator resolves these placeholders before including the configuration in the run payload.

### Available Sources

| Source | Syntax | Description | Where Usable |
|--------|--------|-------------|--------------|
| **params** | `${params.X}` | Agent input parameters, validated against agent's parameter schema | Agent |
| **scope** | `${scope.X}` | Run scope values (LLM-invisible) | Registry, Capability, Agent |
| **env** | `${env.X}` | Environment variables from Coordinator | All levels |
| **runtime** | `${runtime.X}` | Framework-provided execution context | All levels |
| **runner** | `${runner.X}` | Runner-specific values (resolved by Runner, not Coordinator) | All levels |

### Runtime Keys (Coordinator)

The `runtime` source provides framework-managed values resolved at Coordinator level:

| Key | Description |
|-----|-------------|
| `session_id` | Current session identifier |
| `run_id` | Current run identifier |

### Runner Keys (Runner)

The `runner` source provides values only the Runner knows, resolved at Runner level:

| Key | Description |
|-----|-------------|
| `orchestrator_mcp_url` | URL of the embedded Orchestrator MCP (dynamic port) |

**Note**: The `runner` prefix clearly indicates these placeholders are NOT resolved by the Coordinator. They are resolved by the Runner because only the Runner has access to these values (e.g., the dynamic port of the embedded Orchestrator MCP).

### Resolution Location

Most resolution happens at Coordinator level, with one exception:

1. Coordinator merges: Registry defaults → Capability → Agent
2. Coordinator resolves placeholders using:
   - Run's params
   - Run's scope
   - Run's runtime (session_id, run_id)
   - Coordinator's environment variables
3. Fully resolved configuration included in run payload to Runner

### Placeholder Validation

When resolving placeholders, the Coordinator validates that required values are present. This happens at run creation time.

| Scenario | Config Key Required | Behavior |
|----------|---------------------|----------|
| Value present | - | Placeholder resolved, config key included |
| Value missing | Yes (`required: true`) | **Error** - run creation rejected, error returned to caller |
| Value missing | No | **Omit** - config key not included |

#### Why Validation at Coordinator

Resolving and validating at Coordinator level enables:
- **Immediate feedback** - Caller receives error response directly (e.g., "missing required scope.context_id")
- **No failed runs** - Invalid configurations never become runs
- **Clear errors** - Caller knows exactly what's missing before run starts

#### Validation Example

Registry defines:
```json
{
  "config_schema": {
    "context_id": {"type": "string", "required": true},
    "workflow_id": {"type": "string", "required": false}
  }
}
```

Agent configures:
```json
{
  "config": {
    "context_id": "${scope.context_id}",
    "workflow_id": "${scope.workflow_id}"
  }
}
```

Run created with:
```json
{
  "scope": {"context_id": "ctx-123"}
}
```

Result:
- `context_id`: resolved to `"ctx-123"` ✓
- `workflow_id`: omitted (optional, value missing) ✓

If `scope` had no `context_id`:
```json
HTTP 400 Bad Request
{
  "error": "Missing required value: scope.context_id for config key 'context_id'"
}
```

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
| **No scoping mechanism** | Cannot scope MCP server access (e.g., limit Jira to specific projects) |
| **No generic auth** | Each MCP server handles auth differently, no unified pattern |
| **Config duplication** | Same MCP server definition copied across agents/capabilities |
| **No dynamic values** | Cannot inject run-specific values into MCP configuration |

### Use Cases Addressed

1. **Context Store scoping**: Agent should only see documents tagged with `project-123`
2. **Atlassian scoping**: Agent should only access Jira projects `ALPHA` and `BETA`
3. **Neo4j partitioning**: Agent should only query subgraph `team-alpha`
4. **API key auth**: MCP server requires API key passed via configuration
5. **Multi-environment**: Same agent config works in dev (localhost) and prod (different URLs)
6. **Sub-agent context**: Child agents inherit parent's scope automatically

## What This Design Solves

| Solved | How |
|--------|-----|
| **Centralized URL management** | Registry is single source of truth for all MCP server URLs |
| **Framework-controlled config** | Configuration injected at transport level, LLM cannot influence |
| **Flexible scoping** | Any config key can be used for scoping via placeholders |
| **Simple auth pattern** | Auth via configurable values (API keys, tokens) |
| **Multi-level configuration** | Capability sets defaults, agent overrides |
| **UI-friendly** | Config schemas enable form-based editing in Dashboard |
| **Reduced duplication** | Define MCP server once, reference by name |
| **Immediate validation** | Missing required values caught at run creation |
| **Sub-agent inheritance** | Scope automatically passed to child runs |

## What This Design Does NOT Solve

| Not Solved | Why | Future Work |
|------------|-----|-------------|
| **Dynamic token acquisition** | Adds complexity; only Orchestrator MCP needs this | Extend auth types later |
| **Secret store integration** | Keep config simple for now | Add vault/secret manager integration |
| **MCP server discovery** | Out of scope | Service mesh / discovery pattern |
| **Per-request scoping** | Too complex, per-session is sufficient | Not planned |
| **Scope parameter documentation** | Agent-dependent, complex to infer | Separate documentation |

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
  "config_schema": {
    "context_id": {
      "type": "string",
      "description": "Context for document isolation",
      "required": true
    },
    "workflow_id": {
      "type": "string",
      "description": "Workflow correlation ID",
      "required": false
    },
    "api_key": {
      "type": "string",
      "description": "API key for authentication",
      "required": false,
      "sensitive": true
    }
  },
  "default_config": {
    "context_id": "default"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier, used in references |
| `name` | string | Human-readable name |
| `description` | string | What this MCP server provides |
| `url` | string | Base URL for MCP transport (can contain placeholders) |
| `config_schema` | object | Defines accepted config keys with type, description, required flag |
| `default_config` | object | Default config values (can be overridden) |

#### Config Schema Field Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | string | `"string"`, `"json"`, `"boolean"`, `"number"` |
| `description` | string | Explains what the config key controls |
| `required` | boolean | If true, must be provided at some level |
| `sensitive` | boolean | If true, value hidden in UI, not logged |
| `internal` | boolean | If true, framework-managed (e.g., run_id) |
| `example` | string | Example value for documentation |

#### MCP Server Reference (in Capability/Agent)

Capabilities and agents **reference** the registry:

```json
{
  "mcpServers": {
    "context-store": {
      "ref": "context-store",
      "config": {
        "context_id": "${scope.context_id}"
      }
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ref` | string | References registry entry by ID |
| `config` | object | Config values to set/override at this level (can contain placeholders) |

### Config Resolution Chain

MCP server configuration is resolved through an inheritance chain. Later sources override earlier ones.

```
1. Registry defaults        {"context_id": "default"}
           │
           ▼
2. Capability config        {"context_id": "shared-knowledge"}
           │
           ▼
3. Agent config             {"context_id": "${scope.context_id}"}
           │
           ▼
4. Placeholder resolution   {"context_id": "ctx-123"}  (from run's scope)
```

#### Resolution Rules

| Rule | Behavior |
|------|----------|
| **Override** | Later value replaces earlier value for same key |
| **Remove** | Set key to `null` to explicitly remove it |
| **Placeholders** | Resolved after inheritance, using run's params, scope, env, runtime |

#### Example Resolution

```
Registry (context-store):
  default_config:
    context_id: "default"
    api_key: "${env.CONTEXT_STORE_API_KEY}"

Capability (research-tools):
  config:
    context_id: "${scope.context_id}"

Agent (project-researcher):
  (no override)

Run:
  scope:
    context_id: "project-alpha"

─────────────────────────────────────────────────

Final resolved config:
  context_id: "project-alpha"       (from scope, via capability placeholder)
  api_key: "sk-xxxx-actual-key"     (from Coordinator env)
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Coordinator                               │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    MCP Server Registry                                 │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │  │
│  │  │context-store│ │  atlassian  │ │   neo4j     │ │orchestrator │     │  │
│  │  │ URL, Schema │ │ URL, Schema │ │ URL, Schema │ │ (special)   │     │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Blueprint Resolver                                  │  │
│  │  1. Load agent + capabilities                                          │  │
│  │  2. For each MCP ref: lookup registry, get URL                         │  │
│  │  3. Merge config: registry → capability → agent                        │  │
│  │  4. Resolve placeholders (params, scope, env, runtime)                 │  │
│  │  5. Validate required values present                                   │  │
│  │  6. Include resolved config in run payload                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    │ Run payload with resolved MCP config   │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Runner                                    │
│                                                                              │
│  Receives run payload with fully resolved MCP configuration.                 │
│  No additional API calls or resolution needed.                               │
│  Passes configuration directly to executor.                                  │
│                                                                              │
│  * Orchestrator MCP embedded here (special case with Auth0 M2M)              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ Executor invokes agent
                                     │ with resolved mcp config
                                     ▼
     ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
     │  Context Store   │   │    Atlassian     │   │      Neo4j       │
     │   :9501/mcp      │   │    :9000/mcp     │   │    :9003/mcp     │
     │                  │   │                  │   │                  │
     │ Config:          │   │ Config:          │   │ Config:          │
     │ context_id       │   │ jira_projects    │   │ partition        │
     │ api_key          │   │ api_key          │   │ api_key          │
     └──────────────────┘   └──────────────────┘   └──────────────────┘
```

### Special Case: Orchestrator MCP

The Agent Orchestrator MCP server is embedded in the Agent Runner and has special requirements:

| Aspect | Regular MCP Servers | Orchestrator MCP |
|--------|---------------------|------------------|
| **Location** | External service | Embedded in Runner |
| **URL** | From registry | Dynamic port, injected via `${runner.orchestrator_mcp_url}` |
| **Auth** | Via config values | Auth0 M2M (shared with Runner) |
| **Context** | Via config values | Via run_id config key |

#### Minimal Configuration

The Orchestrator MCP only requires the current run ID:

```json
{
  "id": "orchestrator",
  "name": "Agent Orchestrator",
  "url": "${runner.orchestrator_mcp_url}",
  "config_schema": {
    "run_id": {
      "type": "string",
      "description": "Current run ID for parent context",
      "required": true,
      "internal": true
    }
  }
}
```

#### Scope Inheritance

When creating a child agent, the Coordinator:
1. Receives parent `run_id` from Orchestrator MCP
2. Looks up parent run → retrieves `scope`
3. Creates child run with same `scope`
4. Child agent inherits parent's scope without explicit passing

The LLM never sees or manipulates scope values.

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
  "config_schema": {
    "jira_projects": {
      "type": "string",
      "description": "Comma-separated Jira project keys",
      "required": false,
      "example": "PROJ-A,PROJ-B"
    },
    "confluence_spaces": {
      "type": "string",
      "description": "Comma-separated Confluence space keys",
      "required": false,
      "example": "DEV,DOCS"
    },
    "api_key": {
      "type": "string",
      "description": "API key for Atlassian access",
      "required": true,
      "sensitive": true
    }
  },
  "default_config": {
    "api_key": "${env.ATLASSIAN_API_KEY}"
  }
}
```

### Run Creation

```json
POST /runs
{
  "type": "start_session",
  "agent_name": "project-researcher",
  "prompt": "Research the API design",
  "params": {
    "topic": "authentication"
  },
  "scope": {
    "context_id": "ctx-123",
    "workflow_id": "wf-456"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Run type (start_session, resume_session) |
| `agent_name` | string | Agent to run |
| `prompt` | string | Prompt for the agent |
| `params` | object | Agent parameters (validated against agent's params_schema, visible to LLM) |
| `scope` | object | Run scope (not validated, invisible to LLM, inherited by child runs) |

### Run Payload to Runner

The run payload sent to the Runner includes fully resolved MCP configuration:

```json
{
  "run_id": "run-abc-123",
  "session_id": "session-xyz",
  "agent_name": "project-researcher",
  "prompt": "Research the API design",
  "params": {"topic": "authentication"},
  "resolved_mcp_servers": {
    "context-store": {
      "type": "http",
      "url": "http://localhost:9501/mcp",
      "config": {
        "context_id": "ctx-123",
        "api_key": "sk-xxxx-actual-key"
      }
    }
  }
}
```

## Configuration Examples

### Example 1: Context Store with Scoping

**Registry entry:**
```json
{
  "id": "context-store",
  "url": "http://localhost:9501/mcp",
  "config_schema": {
    "context_id": {"type": "string", "required": true, "description": "Context for document isolation"},
    "workflow_id": {"type": "string", "required": false, "description": "Workflow correlation ID"}
  },
  "default_config": {
    "context_id": "default"
  }
}
```

**Capability (research-capability):**
```json
{
  "mcpServers": {
    "docs": {
      "ref": "context-store",
      "config": {
        "context_id": "${scope.context_id}"
      }
    }
  }
}
```

**Agent (sprint-researcher):**
```json
{
  "capabilities": ["research-capability"],
  "params_schema": {
    "topic": {"type": "string", "required": true}
  }
}
```

**Run request:**
```json
POST /runs
{
  "agent_name": "sprint-researcher",
  "params": {"topic": "API design"},
  "scope": {"context_id": "sprint-42"}
}
```

**Resolved config (in run payload to Runner):**
```json
{
  "mcpServers": {
    "docs": {
      "type": "http",
      "url": "http://localhost:9501/mcp",
      "config": {
        "context_id": "sprint-42"
      }
    }
  }
}
```

### Example 2: Atlassian with API Key

**Registry entry:**
```json
{
  "id": "atlassian",
  "url": "http://localhost:9000/mcp",
  "config_schema": {
    "api_key": {"type": "string", "required": true, "sensitive": true, "description": "Atlassian API key"},
    "jira_projects": {"type": "string", "required": false, "description": "Comma-separated project keys"}
  }
}
```

**Capability (jira-access):**
```json
{
  "mcpServers": {
    "jira": {
      "ref": "atlassian",
      "config": {
        "api_key": "${env.ATLASSIAN_API_KEY}",
        "jira_projects": "${scope.allowed_projects}"
      }
    }
  }
}
```

**Agent (project-assistant):**
```json
{
  "capabilities": ["jira-access"],
  "params_schema": {
    "task": {"type": "string", "required": true}
  }
}
```

**Run request:**
```json
POST /runs
{
  "agent_name": "project-assistant",
  "params": {"task": "List open bugs"},
  "scope": {"allowed_projects": "ALPHA,BETA"}
}
```

**Resolved config (in run payload to Runner):**
```json
{
  "mcpServers": {
    "jira": {
      "type": "http",
      "url": "http://localhost:9000/mcp",
      "config": {
        "api_key": "sk-xxxx-actual-key-from-coordinator-env",
        "jira_projects": "ALPHA,BETA"
      }
    }
  }
}
```

Note: `api_key` resolved from Coordinator's environment variable `ATLASSIAN_API_KEY`. The actual secret never appears in agent configuration.

### Example 3: Orchestrator MCP (Special Case)

The Orchestrator MCP enables agents to spawn sub-agents. It requires special handling.

**Registry entry:**
```json
{
  "id": "orchestrator",
  "url": "${runner.orchestrator_mcp_url}",
  "config_schema": {
    "run_id": {"type": "string", "required": true, "internal": true, "description": "Current run ID"}
  }
}
```

**Capability (orchestration):**
```json
{
  "mcpServers": {
    "orchestrator": {
      "ref": "orchestrator",
      "config": {
        "run_id": "${runtime.run_id}"
      }
    }
  }
}
```

**Agent (lead-researcher) - an orchestrator agent:**
```json
{
  "capabilities": ["orchestration", "research-capability"],
  "params_schema": {
    "research_topic": {"type": "string", "required": true}
  }
}
```

**Run request:**
```json
POST /runs
{
  "agent_name": "lead-researcher",
  "params": {"research_topic": "Authentication patterns"},
  "scope": {"context_id": "project-123", "workflow_id": "wf-789"}
}
```

**Resolved config (in run payload to Runner):**
```json
{
  "mcpServers": {
    "orchestrator": {
      "type": "http",
      "url": "http://127.0.0.1:54321/mcp",
      "config": {
        "run_id": "run-abc-123"
      }
    },
    "docs": {
      "type": "http",
      "url": "http://localhost:9501/mcp",
      "config": {
        "context_id": "project-123"
      }
    }
  }
}
```

**When lead-researcher spawns a sub-agent:**

1. LLM calls Orchestrator MCP tool: `start_agent("detail-researcher", "Research OAuth2")`
2. Orchestrator MCP sends to Coordinator: `run_id: "run-abc-123"`
3. Coordinator looks up `run-abc-123` → finds `scope: {context_id: "project-123", workflow_id: "wf-789"}`
4. Coordinator creates child run with **same scope**
5. Child agent inherits `context_id` and `workflow_id` - same Context Store documents accessible
6. LLM never sees or manipulates scope values

### Example 4: Multiple Agents Sharing Same MCP Server

Three agents share the same Neo4j server but with different scopes:

**Registry:**
```json
{
  "id": "neo4j",
  "url": "http://localhost:9003/mcp/",
  "config_schema": {
    "partition": {"type": "string", "required": false}
  }
}
```

**Agents:**
```json
// team-alpha-analyst
{
  "mcpServers": {
    "kg": {
      "ref": "neo4j",
      "config": {"partition": "${scope.team_partition}"}
    }
  }
}

// team-beta-analyst (same config, different scope at runtime)
{
  "mcpServers": {
    "kg": {
      "ref": "neo4j",
      "config": {"partition": "${scope.team_partition}"}
    }
  }
}

// global-analyst (no partition = full access)
{
  "mcpServers": {
    "kg": {
      "ref": "neo4j",
      "config": {}
    }
  }
}
```

**Run requests:**
```json
// Team Alpha run
{"agent_name": "team-alpha-analyst", "scope": {"team_partition": "team-alpha"}}

// Team Beta run
{"agent_name": "team-beta-analyst", "scope": {"team_partition": "team-beta"}}

// Global run (no partition)
{"agent_name": "global-analyst", "scope": {}}
```

## MCP Server Implementation Requirements

For MCP servers to support this pattern, they must:

1. **Read config from transport** - HTTP headers, STDIO env vars, etc.
2. **Apply filtering** based on config values
3. **Reject/limit** access when required config is missing (if enforcing)

### Example: Context Store MCP Server (HTTP)

```python
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request

mcp = FastMCP("context-store")

def get_config_from_request(request: Request) -> dict:
    """Extract config from HTTP headers."""
    return {
        "context_id": request.headers.get("x-context-id", "default"),
        "workflow_id": request.headers.get("x-workflow-id")
    }

@mcp.tool()
async def list_documents(tags: list[str] = None):
    request = get_current_request()
    config = get_config_from_request(request)

    # Query scoped to context
    docs = await db.query_documents(
        context_id=config["context_id"],
        tags=tags
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

Page for CRUD operations on MCP server registry:

- **List View**: Table with ID, name, URL, config key count
- **Create/Edit Form**:
  - ID field (validated, immutable after creation)
  - Name, description
  - URL field (can contain placeholders)
  - Config schema editor (add/remove keys with type, description, flags)
  - Default config editor

### Capability/Agent Edit Forms

Forms with MCP server selection:

- **MCP Servers Section**:
  - Dropdown to select from registry
  - For each selected server, show config fields based on schema
  - Form fields rendered based on config type (string input, JSON editor, checkbox)
  - Sensitive fields shown as password inputs
  - Placeholder syntax helper (show available sources)

### Visual Indicator for Resolution

Show inheritance chain in UI:

```
┌─────────────────────────────────────────────────────┐
│ MCP Server: context-store                           │
├─────────────────────────────────────────────────────┤
│ context_id                                          │
│ ┌─────────────────────────────────────────────────┐ │
│ │ [${scope.context_id}]                           │ │
│ │ ↑ Overrides: registry default (default)         │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ api_key                                             │
│ ┌─────────────────────────────────────────────────┐ │
│ │ [${env.CONTEXT_STORE_API_KEY}]                  │ │
│ │ ↑ From: registry default                        │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Implementation Notes

### Prerequisite: Centralized Resolution

Before implementing the full placeholder system, the following architectural change is required:

1. **Move MCP config resolution to Coordinator** - Currently fragmented across Runner/Executor
2. **Include resolved config in run payload** - Runner receives self-contained payload
3. **Use Coordinator's environment** - All `${env.X}` resolved from Coordinator, not Runner
4. **Runner resolves `${runner.X}` only** - The `${runner.orchestrator_mcp_url}` placeholder is resolved by Runner (not Coordinator) because only the Runner knows the dynamic port of the embedded Orchestrator MCP

This foundational change ensures:
- Single source of truth for resolution logic
- Immediate validation feedback to callers
- Simplified Runner (no additional API calls, only resolves `${runner.*}` placeholders)
- Centralized secret management

See [MCP Resolution at Coordinator](mcp-resolution-at-coordinator.md) for detailed implementation plan.

### Transport Abstraction

The `config` field in MCP server references is transport-agnostic:
- **HTTP transport**: Config values become HTTP headers
- **STDIO transport**: Config values become environment variables

The registry's `config_schema` documents accepted keys. The transport layer maps them appropriately.

## Limitations

| Limitation | Rationale |
|------------|-----------|
| **No per-request scoping** | Session-level scoping is sufficient; per-request adds complexity |
| **No config validation at runtime** | MCP servers responsible for validating their config |
| **Simple merge (last wins)** | Complex merge strategies add cognitive load |
| **Scope not validated** | Scope keys are arbitrary; validation would require schema |
| **Coordinator env vars only** | Centralized secrets; Runner env not accessible |

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| **Sensitive config values** | Mark as `sensitive: true`, UI hides value, not logged |
| **LLM accessing config** | Config injected at transport level, not exposed to LLM |
| **Config spoofing** | Framework controls config; LLM tool params don't include config |
| **Credential exposure** | Use `${env.X}` placeholders, resolved at Coordinator with actual secrets |
| **Scope manipulation** | LLM cannot see or modify scope; framework-controlled |
| **Child run scope** | Inherited automatically; LLM cannot change parent's scope |

## Future Considerations

### Dynamic Auth Providers

Extend registry to support dynamic token acquisition:

```json
{
  "id": "external-api",
  "auth": {
    "type": "oauth2_client_credentials",
    "token_url": "https://auth.example.com/token",
    "client_id": "${env.EXTERNAL_CLIENT_ID}",
    "client_secret": "${env.EXTERNAL_CLIENT_SECRET}",
    "scope": "api:read api:write"
  }
}
```

### Secret Store Integration

Reference secrets by name instead of env vars:

```json
{
  "default_config": {
    "api_key": {"$secret": "atlassian-api-key"}
  }
}
```

### Scope Schema (Optional)

Optional schema for documenting expected scope keys:

```json
{
  "scope_schema": {
    "context_id": {"type": "string", "description": "Context for document scoping"},
    "workflow_id": {"type": "string", "description": "Workflow correlation"}
  }
}
```

## Related Documents

- [Agent Types](../../architecture/agent-types.md) - Autonomous vs procedural agents
- [Capabilities System](../../features/capabilities-system.md) - How capabilities reference MCP servers
- [Auth OIDC](../../architecture/auth-oidc.md) - Authentication with Auth0
