# MCP Server Registry

**Status:** Implemented
**Affects:** Agent Coordinator, Agent Runner, Dashboard

## Overview

Centralized management of MCP server configurations with dynamic placeholder resolution. MCP servers are defined once in a registry with URLs and config schemas. Agents and capabilities reference them by name. Configuration values support placeholders that are resolved at run creation.

**Key Characteristics:**

- **Single source of truth** - MCP server URLs defined once, referenced everywhere
- **Config schemas** - Document what configuration each server accepts
- **Placeholder resolution** - Dynamic values injected at run creation
- **Config inheritance** - Registry defaults → Capability → Agent
- **LLM-invisible scope** - Run scope values never exposed to the LLM

## Motivation

### The Problem

MCP server configurations need to be managed across agents and capabilities. Without centralization:
- Same URL duplicated in multiple configs
- URL changes require editing multiple files
- No schema documenting what configuration each server accepts

Additionally, MCP servers often need run-specific values for scoping and authentication:
- **Context IDs** to isolate document access per workflow
- **Credentials** to authenticate with external services
- **Correlation IDs** to track related operations

Passing these values through agent parameters exposes them to the LLM, which causes problems:
- **LLM confusion** - Operational parameters like `context_id` distract from the actual task
- **Security risk** - Secrets visible to the LLM could leak into outputs or logs
- **Manual propagation** - Parent agents would need to explicitly pass values to child agents

### The Solution

A centralized registry where MCP servers are defined once, combined with a **scope** mechanism for LLM-invisible values.

**Registry:** MCP servers defined once with URLs and config schemas. Agents reference them by name.

**Scope:** Run-scoped values that:
- Are **never exposed to the LLM** - injected at transport level (HTTP headers)
- Flow through MCP server configuration via placeholders
- Are **automatically inherited** by child runs - the framework handles propagation, not the LLM

This means an agent can spawn child agents via Orchestrator MCP, and those children automatically inherit scope values like credentials and context IDs - without the LLM ever seeing or passing them.

## Key Concepts

### MCP Server Registry

A collection of MCP server definitions stored in `config/mcp-servers/{id}/mcp-server.json`. Each entry defines:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier used in references |
| `name` | Human-readable name |
| `url` | Base URL (can contain placeholders) |
| `config_schema` | Schema documenting accepted config keys |
| `default_config` | Default values for config keys |

### MCP Server Reference

Agents and capabilities reference registry entries using the `ref` syntax:

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

The `ref` field points to a registry entry ID. The `config` field provides values that override registry defaults.

### Placeholder Sources

Configuration values can contain placeholders using `${source.key}` syntax:

| Source | Syntax | Description |
|--------|--------|-------------|
| `params` | `${params.X}` | Agent input parameters (visible to LLM) |
| `scope` | `${scope.X}` | Run scope values (LLM-invisible) |
| `env` | `${env.X}` | Coordinator environment variables |
| `runtime` | `${runtime.X}` | Framework context (session_id, run_id) |
| `runner` | `${runner.X}` | Runner-specific values |

### Run Scope

LLM-invisible values provided at run creation that flow through agent execution. Unlike agent parameters (which the LLM sees and works with), scope values are framework-controlled and never enter the LLM context.

| Property | Description |
|----------|-------------|
| **LLM-invisible** | Injected at transport level (HTTP headers), never in LLM context |
| **Provided at run creation** | Caller supplies scope when starting a run |
| **Inherited by child runs** | Framework automatically propagates to child runs |
| **Used in config mappings** | Mapped to MCP server configuration via `${scope.X}` placeholders |

**Why LLM-invisible?**
- Keeps operational parameters out of the LLM's attention
- Enables passing secrets (API keys, tokens) without exposure risk
- Framework handles propagation - LLM doesn't need to know about or forward these values

Common scope keys: `context_id` (document scoping), `workflow_id` (correlation), `api_key` (authentication).

### Config Resolution

MCP server configuration is resolved in two steps:

**Step 1: MCP Server Merging (at agent load time)**

When an agent uses capabilities, MCP servers from all sources are merged:
- Capabilities' MCP servers are collected (in declaration order)
- Agent's MCP servers are added
- **Server names must be unique** - if the same name appears in multiple sources, an error is raised

**Step 2: Config Inheritance (at run creation time)**

For each MCP server reference, config values are merged:

```
Registry default_config    {"context_id": "default"}
            ↓
Ref config (override)      {"context_id": "${scope.context_id}"}
            ↓
Placeholder resolution     {"context_id": "ctx-123"}
```

The ref's config (whether declared in a capability or agent) overrides registry defaults. Then placeholders are resolved.

**Key point:** Config inheritance exists only between the registry's `default_config` and the config provided in the ref. Each MCP server name can only be declared once (either in a capability or in the agent, not both) - declaring the same name in multiple sources raises an error.

## Configuration

### Registry Entry

```json
{
  "id": "context-store",
  "name": "Context Store",
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
    }
  },
  "default_config": {
    "context_id": "default"
  }
}
```

### Config Schema Field Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | string | `"string"`, `"integer"`, `"boolean"` |
| `description` | string | Explains what the config key controls |
| `required` | boolean | If true, must be provided at some level |
| `sensitive` | boolean | If true, value hidden in UI |

### Capability Reference

```json
{
  "mcpServers": {
    "graph": {
      "ref": "neo4j",
      "config": {
        "partition": "${scope.team_partition}"
      }
    }
  }
}
```

### Agent Reference

```json
{
  "mcpServers": {
    "orchestrator": {
      "ref": "orchestrator",
      "config": {
        "X-Agent-Tags": "internal"
      }
    }
  }
}
```

## Data Model

### MCPServerRegistryEntry

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "url": "string",
  "config_schema": {
    "key": {
      "type": "string",
      "description": "string",
      "required": false,
      "sensitive": false
    }
  },
  "default_config": {}
}
```

### MCPServerRef

```json
{
  "ref": "string",
  "config": {}
}
```

## API

This feature uses the following Agent Coordinator endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp-servers` | GET | List all MCP server definitions |
| `/mcp-servers` | POST | Create new MCP server definition |
| `/mcp-servers/{id}` | GET | Get MCP server by ID |
| `/mcp-servers/{id}` | PUT | Update MCP server definition |
| `/mcp-servers/{id}` | DELETE | Delete MCP server definition |

Run creation accepts `scope` parameter:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/runs` | POST | Create run with `scope` for LLM-invisible values |

See [Agent Coordinator API Reference](../components/agent-coordinator/API.md) for full details.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Coordinator                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  MCP Server Registry                        │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │ │
│  │  │context-store │ │  atlassian   │ │ orchestrator │        │ │
│  │  │ URL, Schema  │ │ URL, Schema  │ │ URL, Schema  │        │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Blueprint Resolver                         │ │
│  │  1. Load agent + capabilities                               │ │
│  │  2. For each MCP ref: lookup registry, get URL              │ │
│  │  3. Merge config: registry → capability → agent             │ │
│  │  4. Resolve placeholders (params, scope, env, runtime)      │ │
│  │  5. Validate required values present                        │ │
│  │  6. Store resolved blueprint in run                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Run payload with resolved MCP config
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Runner                              │
│                                                                  │
│  Receives run with pre-resolved MCP configuration.               │
│  Resolves ONLY ${runner.orchestrator_mcp_url} placeholder.       │
│  Passes configuration directly to executor.                      │
└─────────────────────────────────────────────────────────────────┘
```

## Examples

### Context Store with Scoping

Run request with scope:
```json
{
  "agent_name": "researcher",
  "prompt": "Find relevant documents",
  "scope": {
    "context_id": "project-alpha"
  }
}
```

Agent references registry with placeholder:
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

Resolved configuration in run payload:
```json
{
  "docs": {
    "url": "http://localhost:9501/mcp",
    "config": {
      "context_id": "project-alpha"
    }
  }
}
```

### Scope Inheritance

Parent run created with scope:
```json
{
  "agent_name": "lead-researcher",
  "scope": {"context_id": "ctx-123", "api_key": "secret-token"}
}
```

When lead-researcher spawns a child agent via Orchestrator MCP, it simply requests the agent:
```
LLM: "Start detail-researcher to analyze the documents"
```

The **framework** (not the LLM) looks up the parent's scope and creates the child run with inherited values:
```json
{
  "agent_name": "detail-researcher",
  "scope": {"context_id": "ctx-123", "api_key": "secret-token"}
}
```

The LLM never sees `context_id` or `api_key` - these values flow through the agent hierarchy at the framework level.

## Error Handling & Edge Cases

### Missing Required Config

If a required config value is missing after placeholder resolution, run creation fails:

```json
{
  "error": "missing_required_mcp_config",
  "message": "MCP server 'context-store' missing required config: context_id",
  "server_name": "context-store",
  "missing_fields": ["context_id"]
}
```

### Unresolved Placeholders

Placeholders referencing missing values (e.g., `${scope.missing}`) are detected as unresolved. If the config key is required, run creation fails.

## Dashboard Integration

### MCP Servers Page

Management page at `/mcp-servers`:
- List view with ID, Name, URL, Config Fields
- Create/Edit/Delete MCP servers
- Config schema editor with field types
- Default config values editor

### Agent/Capability Editors

MCP server selection in editors:
- Dropdown to add servers from registry
- Config fields rendered based on registry's config_schema
- Placeholder documentation via info popover

## References

- [ADR-018: Centralized Placeholder Resolution](../adr/ADR-018-centralized-placeholder-resolution.md)
- [ADR-019: MCP Server Registry](../adr/ADR-019-mcp-server-registry.md)
- [Capabilities System](./capabilities-system.md)
