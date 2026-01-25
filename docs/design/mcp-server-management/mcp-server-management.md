# MCP Server Management

**Status:** Draft
**Date:** 2026-01-25
**Author:** Claude (AI Design Document)

## Executive Summary

This document proposes a centralized MCP (Model Context Protocol) server management system for the Agent Orchestrator framework. The design introduces:

1. **MCP Server Registry** - A centralized store for MCP server definitions with metadata
2. **Discovery API** - Endpoints for looking up and querying available MCP servers
3. **Reference-based Configuration** - Capabilities and agents reference servers by name instead of inline config
4. **Coordinator-based URL Resolution** - The Coordinator resolves MCP server references and URLs before passing to Runners
5. **Parameterization** - Runtime parameters for dynamic MCP server configuration

## Problem Statement

### Current State

MCP servers are currently configured inline within capabilities and agents:

```
capabilities/neo4j-knowledge-graph/
├── capability.json
├── capability.text.md
└── capability.mcp.json          # Full MCP server config embedded here
```

```json
// capability.mcp.json
{
  "mcpServers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9003/mcp/"
    }
  }
}
```

### Problems

1. **No Central Registry**: MCP server definitions are scattered across capability and agent configs. There's no single place to see all available MCP servers.

2. **Configuration Duplication**: If multiple capabilities need the same MCP server (e.g., Context Store), each must define the full configuration inline. URL changes require updating every occurrence.

3. **Limited Discovery**: No API to query "what MCP servers are available?" - you must inspect each capability's config.

4. **Static URLs**: MCP server URLs are hardcoded. Environment-specific deployments (dev, staging, prod) require different config files.

5. **No Support Metadata**: No structured way to include support information (documentation links, contact info, version, health status).

6. **Resolution Location**: Currently, placeholder resolution (`${AGENT_ORCHESTRATOR_MCP_URL}`) happens in the Runner's `BlueprintResolver`. This limits what the Coordinator can do with MCP server information (e.g., validation, enrichment).

7. **No Parameterization**: MCP server configs cannot accept runtime parameters for dynamic behavior.

### Requirements

1. **Centralized Definition**: Define each MCP server once with full metadata
2. **Discovery API**: Query available MCP servers with filtering and search
3. **Reference by Name**: Capabilities reference MCP servers by name, not inline config
4. **URL Resolution**: Coordinator resolves URLs based on environment/deployment context
5. **Parameterization**: Support for runtime parameters in MCP server configs
6. **Support Metadata**: Include documentation, health endpoints, version info
7. **Dashboard Integration**: Manage MCP servers through the Dashboard UI

## Architecture Overview

### Current Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Agent Config    │────►│ Coordinator      │────►│ Runner          │
│ (inline MCP)    │     │ (merges caps)    │     │ (resolves URLs) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

- MCP server configs are inline in capabilities/agents
- Coordinator merges capability MCP servers into agent config
- Runner resolves placeholders (${AGENT_ORCHESTRATOR_MCP_URL})
- No discovery, no registry

### Proposed Flow

```
┌─────────────────┐     ┌──────────────────────────────────────────┐
│ MCP Server      │     │            Agent Coordinator             │
│ Registry        │     │                                          │
│                 │     │  ┌───────────────┐  ┌─────────────────┐  │
│ - context-store │◄────┼──│ Discovery API │  │ MCP Resolver    │  │
│ - neo4j-graph   │     │  │ GET /mcp-servers│ (name → config)  │  │
│ - orchestrator  │     │  └───────────────┘  └─────────────────┘  │
│                 │     │                             │             │
└─────────────────┘     │                             ▼             │
                        │  ┌───────────────────────────────────────┐│
┌─────────────────┐     │  │ Capability Resolver                   ││
│ Capability      │────►│  │ - Merges MCP refs into agent config  ││
│ (MCP refs)      │     │  │ - Resolves names → full configs      ││
│ neo4j-graph: {} │     │  │ - Applies parameters                 ││
└─────────────────┘     │  └───────────────────────────────────────┘│
                        │                             │             │
                        │                             ▼             │
                        │  ┌───────────────────────────────────────┐│
                        │  │ Blueprint Response                    ││
                        │  │ (fully resolved MCP configs)          ││
                        │  └───────────────────────────────────────┘│
                        └──────────────────────────────────────────┘
                                              │
                                              ▼
                        ┌──────────────────────────────────────────┐
                        │            Agent Runner                   │
                        │ - Receives resolved configs               │
                        │ - Only resolves runtime placeholders      │
                        │   (${AGENT_SESSION_ID})                   │
                        └──────────────────────────────────────────┘
```

## Design Approaches

### Approach 1: MCP Server Registry (Recommended)

**Concept**: Introduce a new first-class entity `MCP Server` stored in the Coordinator, with its own CRUD API and storage.

#### Storage Structure

```
.agent-orchestrator/
├── agents/
├── capabilities/
└── mcp-servers/                   # NEW: MCP server definitions
    ├── context-store/
    │   └── mcp-server.json
    ├── neo4j-graph/
    │   └── mcp-server.json
    └── orchestrator/
        └── mcp-server.json
```

#### MCP Server Definition Schema

```json
// mcp-servers/context-store/mcp-server.json
{
  "name": "context-store",
  "description": "Document storage and semantic search",
  "version": "1.0.0",

  "transport": {
    "type": "http",
    "url": "${CONTEXT_STORE_URL}/mcp/",
    "headers": {
      "Authorization": "Bearer ${CONTEXT_STORE_TOKEN}"
    }
  },

  "parameters_schema": {
    "type": "object",
    "properties": {
      "namespace": {
        "type": "string",
        "description": "Document namespace for scoping"
      }
    }
  },

  "support": {
    "documentation_url": "https://docs.example.com/context-store",
    "health_endpoint": "/health",
    "contact": "platform-team@example.com",
    "sla": "99.9%"
  },

  "environments": {
    "development": {
      "url": "http://localhost:8766/mcp/"
    },
    "staging": {
      "url": "https://context-store.staging.example.com/mcp/"
    },
    "production": {
      "url": "https://context-store.prod.example.com/mcp/"
    }
  },

  "tags": ["storage", "search", "documents"]
}
```

#### Capability Reference Format

Capabilities reference MCP servers by name instead of inline config:

```json
// capabilities/document-access/capability.json
{
  "name": "document-access",
  "description": "Access to document storage",
  "mcp_servers": {
    "context-store": {
      "parameters": {
        "namespace": "project-alpha"
      }
    }
  }
}
```

Alternative shorthand for no parameters:

```json
{
  "mcp_servers": ["context-store", "neo4j-graph"]
}
```

#### Resolution Flow

1. **Agent Request**: `GET /agents/my-agent`
2. **Capability Resolution**: Load agent's capabilities, each may reference MCP servers
3. **MCP Server Resolution**: For each referenced server name:
   - Lookup in MCP Server Registry
   - Apply environment-specific config (based on Coordinator's deployment env)
   - Apply parameters from capability reference
   - Resolve URL placeholders (environment variables)
4. **Return Merged Config**: Fully resolved `mcp_servers` dict in blueprint

#### Discovery API

```http
# List all MCP servers
GET /mcp-servers
Response: [
  {
    "name": "context-store",
    "description": "Document storage and semantic search",
    "version": "1.0.0",
    "transport_type": "http",
    "tags": ["storage", "search"],
    "support": { ... }
  }
]

# Get specific MCP server with full config
GET /mcp-servers/{name}
Response: {
  "name": "context-store",
  "description": "...",
  "transport": { ... },
  "parameters_schema": { ... },
  "support": { ... },
  "resolved_url": "http://localhost:8766/mcp/"  # For current environment
}

# Search MCP servers by tag
GET /mcp-servers?tags=storage,search
```

#### Pros

- Clean separation: MCP servers are independent entities
- Full discovery: List, search, inspect all available servers
- Environment-aware: Same definition works across deployments
- Parameterization: Schema-validated runtime parameters
- Support metadata: Documentation, health checks, contacts

#### Cons

- New entity to manage (storage, API, UI)
- Migration path needed for existing inline configs
- More indirection (capability → reference → registry)

---

### Approach 2: Enhanced Capabilities (Minimal Change)

**Concept**: Keep MCP configs in capabilities but add metadata and a discovery endpoint that aggregates them.

#### Enhanced Capability MCP Config

```json
// capability.mcp.json
{
  "mcpServers": {
    "context-store": {
      "type": "http",
      "url": "http://localhost:8766/mcp/",

      "metadata": {
        "version": "1.0.0",
        "description": "Document storage",
        "documentation_url": "...",
        "health_endpoint": "/health"
      },

      "environments": {
        "production": { "url": "https://prod.example.com/mcp/" }
      }
    }
  }
}
```

#### Aggregated Discovery API

```http
# Aggregate all MCP servers across capabilities
GET /mcp-servers
```

The Coordinator scans all capabilities and returns unique MCP server definitions.

#### Pros

- Minimal schema changes
- No new storage entity
- Capabilities remain self-contained

#### Cons

- Discovery requires scanning all capabilities
- Same MCP server may be defined differently in different capabilities
- No canonical definition - first-encountered wins for conflicts
- Parameters harder to implement consistently

---

### Approach 3: Hybrid Registry with Inline Override

**Concept**: Registry stores defaults, capabilities can override specific fields.

```json
// Registry: mcp-servers/context-store/mcp-server.json
{
  "name": "context-store",
  "transport": {
    "type": "http",
    "url": "${CONTEXT_STORE_URL}/mcp/"
  }
}

// Capability: capability.mcp.json - overrides specific fields
{
  "mcpServers": {
    "context-store": {
      "override": {
        "headers": {
          "X-Namespace": "project-alpha"
        }
      }
    }
  }
}
```

Resolution merges registry config with capability overrides.

#### Pros

- Best of both: centralized defaults + capability-specific customization
- Flexible for advanced use cases

#### Cons

- Complex merging logic
- Harder to understand final config
- Debugging which override won is difficult

---

## Recommended Approach: MCP Server Registry (Approach 1)

**Rationale**:

1. **Clarity**: MCP servers are a distinct concern from capabilities. A capability describes "what domain knowledge an agent has" while an MCP server describes "how to connect to a service."

2. **Reusability**: The same Context Store MCP server definition should be used by all capabilities that need document access. Copy-paste leads to drift.

3. **Discovery**: Operators need to see "what MCP servers are available in this deployment" - this is a natural query that requires a registry.

4. **Environment Management**: Production deployments need different URLs. A registry with environment-specific configs is the standard pattern.

5. **Parameterization**: Some MCP servers need runtime parameters (namespace, tenant ID). A schema-based approach in the registry enables validation.

## Detailed Design

### Data Model

#### MCPServer Entity

```python
class MCPServerTransport(BaseModel):
    """MCP server transport configuration."""
    type: Literal["http", "stdio"]

    # HTTP transport
    url: Optional[str] = None
    headers: Optional[dict[str, str]] = None

    # Stdio transport
    command: Optional[str] = None
    args: Optional[list[str]] = None
    env: Optional[dict[str, str]] = None


class MCPServerEnvironmentConfig(BaseModel):
    """Environment-specific transport overrides."""
    url: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    # Other fields that may vary by environment


class MCPServerSupport(BaseModel):
    """Support and operational metadata."""
    documentation_url: Optional[str] = None
    health_endpoint: Optional[str] = None
    contact: Optional[str] = None
    sla: Optional[str] = None
    version: Optional[str] = None


class MCPServer(BaseModel):
    """MCP Server registry entry."""
    name: str
    description: str
    transport: MCPServerTransport

    parameters_schema: Optional[dict] = None  # JSON Schema for parameters
    support: Optional[MCPServerSupport] = None
    environments: Optional[dict[str, MCPServerEnvironmentConfig]] = None
    tags: list[str] = []

    created_at: datetime
    modified_at: datetime
```

#### MCPServerReference (in Capabilities/Agents)

```python
class MCPServerReference(BaseModel):
    """Reference to an MCP server from a capability or agent."""
    # Can be just a name (string) or a dict with parameters
    name: str
    parameters: Optional[dict] = None  # Runtime parameters
    alias: Optional[str] = None  # Override the server name in final config
```

### Storage

#### File Layout

```
.agent-orchestrator/
└── mcp-servers/
    └── {server-name}/
        └── mcp-server.json
```

#### Storage Module

```python
# servers/agent-coordinator/mcp_server_storage.py

class MCPServerStorage:
    """File-based storage for MCP server definitions."""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir

    def list(self) -> list[MCPServerSummary]:
        """List all MCP servers with summary info."""
        ...

    def get(self, name: str) -> MCPServer:
        """Get full MCP server definition."""
        ...

    def create(self, server: MCPServerCreate) -> MCPServer:
        """Create new MCP server definition."""
        ...

    def update(self, name: str, updates: MCPServerUpdate) -> MCPServer:
        """Update MCP server definition."""
        ...

    def delete(self, name: str) -> None:
        """Delete MCP server definition."""
        ...

    def search(self, tags: list[str] = None, query: str = None) -> list[MCPServerSummary]:
        """Search MCP servers by tags or text."""
        ...
```

### API Endpoints

#### MCP Servers CRUD

```http
# List all MCP servers
GET /mcp-servers
Query params:
  - tags: comma-separated list for filtering
  - search: text search in name/description

Response: {
  "mcp_servers": [
    {
      "name": "context-store",
      "description": "Document storage and semantic search",
      "transport_type": "http",
      "tags": ["storage", "search"],
      "has_parameters": true,
      "support": {
        "version": "1.0.0",
        "documentation_url": "..."
      }
    }
  ]
}

# Get specific MCP server
GET /mcp-servers/{name}
Query params:
  - environment: resolve URLs for specific environment (default: current)

Response: {
  "mcp_server": {
    "name": "context-store",
    "description": "...",
    "transport": {
      "type": "http",
      "url": "http://localhost:8766/mcp/",  # Resolved for environment
      "headers": { ... }
    },
    "parameters_schema": { ... },
    "support": { ... },
    "tags": [...]
  }
}

# Create MCP server
POST /mcp-servers
Request: {
  "name": "my-mcp-server",
  "description": "...",
  "transport": { ... },
  "parameters_schema": { ... },
  "support": { ... },
  "environments": { ... },
  "tags": [...]
}

# Update MCP server
PATCH /mcp-servers/{name}
Request: { partial update }

# Delete MCP server
DELETE /mcp-servers/{name}
Response: 204 No Content
```

#### Validate MCP Server Reference

```http
# Validate that a reference can be resolved
POST /mcp-servers/{name}/validate
Request: {
  "parameters": {
    "namespace": "project-alpha"
  }
}

Response: {
  "valid": true,
  "resolved_config": {
    "type": "http",
    "url": "...",
    "headers": { ... }
  },
  "warnings": []
}
```

### Resolution Pipeline

#### Where Resolution Happens

| Placeholder | Resolved By | When |
|-------------|-------------|------|
| MCP server names | Coordinator | `GET /agents/{name}` response |
| `${ENV_VAR}` patterns | Coordinator | Same as above |
| `${AGENT_SESSION_ID}` | Runner | Before spawning executor |
| `${AGENT_ORCHESTRATOR_MCP_URL}` | Runner | Before spawning executor |

#### Resolution Algorithm

```python
# In Coordinator's capability resolver

def resolve_mcp_servers(
    agent: Agent,
    capabilities: list[Capability],
    mcp_registry: MCPServerStorage,
    environment: str,
) -> dict[str, MCPServerConfig]:
    """
    Resolve all MCP server references to full configs.

    Steps:
    1. Collect MCP refs from capabilities (in order)
    2. Collect MCP refs from agent (if any)
    3. For each ref:
       a. Lookup in registry
       b. Apply environment-specific overrides
       c. Resolve environment variable placeholders
       d. Apply parameters
       e. Check for name conflicts
    4. Return merged dict
    """
    resolved = {}

    # Process capabilities in order
    for cap in capabilities:
        for ref in cap.mcp_server_refs:
            config = resolve_single_ref(ref, mcp_registry, environment)
            name = ref.alias or ref.name

            if name in resolved:
                raise MCPServerConflictError(
                    f"MCP server '{name}' defined in multiple places"
                )

            resolved[name] = config

    # Process agent-level refs (if any)
    for ref in agent.mcp_server_refs:
        config = resolve_single_ref(ref, mcp_registry, environment)
        name = ref.alias or ref.name

        if name in resolved:
            raise MCPServerConflictError(...)

        resolved[name] = config

    return resolved


def resolve_single_ref(
    ref: MCPServerReference,
    registry: MCPServerStorage,
    environment: str,
) -> dict:
    """Resolve a single MCP server reference."""
    server = registry.get(ref.name)

    # Start with base transport config
    config = server.transport.model_dump()

    # Apply environment overrides
    if environment in server.environments:
        env_config = server.environments[environment]
        config = deep_merge(config, env_config)

    # Resolve environment variable placeholders
    config = resolve_env_placeholders(config)

    # Apply parameters
    if ref.parameters:
        validate_parameters(ref.parameters, server.parameters_schema)
        config = apply_parameters(config, ref.parameters)

    return config
```

### Capability Schema Update

#### New Format

```json
// capability.json
{
  "name": "document-access",
  "description": "Provides document storage capabilities",

  "mcp_servers": {
    "docs": {
      "server": "context-store",
      "parameters": {
        "namespace": "shared-docs"
      }
    }
  }
}
```

Or simplified format when no parameters:

```json
{
  "mcp_servers": ["context-store", "neo4j-graph"]
}
```

#### Backward Compatibility

The capability loader detects format:

1. **Array of strings**: `["context-store"]` → reference by name, no params
2. **Dict with `server` key**: `{"docs": {"server": "context-store"}}` → reference with alias/params
3. **Dict with `type` key**: `{"neo4j": {"type": "http", ...}}` → legacy inline config (deprecated)

```python
def parse_mcp_config(raw: Union[list, dict]) -> list[MCPServerReference]:
    """Parse capability MCP config to references."""

    if isinstance(raw, list):
        # ["server1", "server2"]
        return [MCPServerReference(name=s) for s in raw]

    refs = []
    for key, value in raw.items():
        if isinstance(value, str):
            # {"alias": "server-name"}
            refs.append(MCPServerReference(name=value, alias=key))
        elif "server" in value:
            # {"alias": {"server": "name", "parameters": {...}}}
            refs.append(MCPServerReference(
                name=value["server"],
                alias=key,
                parameters=value.get("parameters"),
            ))
        elif "type" in value:
            # Legacy inline config - deprecated
            logger.warning(f"Inline MCP config deprecated: {key}")
            # Handle legacy format...

    return refs
```

### Dashboard Integration

#### MCP Servers Management Page

New page at `/mcp-servers`:

1. **List View**
   - Table: Name, Description, Transport Type, Tags, Version
   - Filter by tags
   - Search by name/description
   - Health status indicator (if health endpoint configured)

2. **Detail View**
   - Full configuration
   - Environment-specific URLs
   - Parameter schema
   - Support information
   - "Used by" list (capabilities/agents referencing this server)

3. **Create/Edit Form**
   - Name (validated, unique)
   - Description (required)
   - Transport configuration (type switcher: HTTP/stdio)
   - Environment URLs (repeatable section)
   - Parameters schema (JSON editor)
   - Support metadata
   - Tags (multi-select/create)

4. **Validation Panel**
   - Test connection button
   - Show resolved config for each environment

#### Agent/Capability Edit Forms

Update existing forms:

- Replace inline MCP JSON editor with server selector
- Multi-select from registered MCP servers
- Show selected servers with parameter inputs (based on schema)
- Preview panel shows resolved config

### Parameterization

#### Parameter Resolution

Parameters are applied to the resolved config using template substitution:

```json
// MCP Server definition
{
  "name": "context-store",
  "transport": {
    "type": "http",
    "url": "http://localhost:8766/mcp/",
    "headers": {
      "X-Namespace": "{{namespace}}"
    }
  },
  "parameters_schema": {
    "type": "object",
    "required": ["namespace"],
    "properties": {
      "namespace": {
        "type": "string",
        "description": "Document namespace"
      }
    }
  }
}
```

```json
// Capability reference
{
  "mcp_servers": {
    "docs": {
      "server": "context-store",
      "parameters": {
        "namespace": "project-alpha"
      }
    }
  }
}
```

```json
// Resolved output
{
  "docs": {
    "type": "http",
    "url": "http://localhost:8766/mcp/",
    "headers": {
      "X-Namespace": "project-alpha"
    }
  }
}
```

#### Parameter Sources

Parameters can come from multiple sources (in priority order):

1. **Capability reference**: Explicit parameters in the reference
2. **Agent parameters**: Passed at run creation time
3. **Session context**: Inherited from parent session
4. **Defaults**: Defined in the parameter schema

### Environment URL Resolution

#### Configuration

The Coordinator knows its deployment environment via:

```bash
AGENT_ORCHESTRATOR_ENVIRONMENT=production  # or: development, staging
```

#### Resolution

When resolving MCP server configs:

```python
def get_resolved_url(server: MCPServer, environment: str) -> str:
    """Get URL for specific environment."""

    # Check environment-specific config first
    if server.environments and environment in server.environments:
        env_config = server.environments[environment]
        if env_config.url:
            return resolve_env_vars(env_config.url)

    # Fall back to base transport URL
    return resolve_env_vars(server.transport.url)


def resolve_env_vars(value: str) -> str:
    """Resolve ${ENV_VAR} patterns."""
    import re
    import os

    pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'

    def replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(pattern, replacer, value)
```

### Support Metadata

#### Health Checks

If an MCP server defines a health endpoint:

```json
{
  "support": {
    "health_endpoint": "/health"
  }
}
```

The Dashboard can:
1. Periodically check health (relative to resolved URL)
2. Show status indicator in the list view
3. Alert on unhealthy servers

#### Documentation Links

```json
{
  "support": {
    "documentation_url": "https://docs.example.com/context-store",
    "api_reference_url": "https://api.example.com/context-store/openapi"
  }
}
```

The Dashboard can:
1. Show documentation links in the detail view
2. Fetch and display OpenAPI spec (if available)

## Migration Path

### Phase 1: Registry Introduction

1. Add MCP Server storage and API to Coordinator
2. Add MCP Servers management page to Dashboard
3. Migrate existing MCP configs to registry entries
4. Both inline and reference formats work

### Phase 2: Capability Migration

1. Update capability.mcp.json files to use references
2. Dashboard defaults to reference format
3. Warn on inline configs

### Phase 3: Full Adoption

1. Remove support for inline MCP configs in capabilities
2. All MCP servers must be in registry
3. Clean up legacy code

## Example Configurations

### Built-in MCP Servers

#### Orchestrator

```json
// mcp-servers/orchestrator/mcp-server.json
{
  "name": "orchestrator",
  "description": "Agent orchestration tools (start_session, resume_session)",
  "transport": {
    "type": "http",
    "url": "${AGENT_ORCHESTRATOR_MCP_URL}",
    "headers": {
      "X-Agent-Session-Id": "${AGENT_SESSION_ID}"
    }
  },
  "support": {
    "documentation_url": "/docs/architecture/mcp-runner-integration.md",
    "version": "2.0"
  },
  "tags": ["orchestration", "built-in"]
}
```

Note: `${AGENT_ORCHESTRATOR_MCP_URL}` and `${AGENT_SESSION_ID}` are Runner-resolved placeholders.

#### Context Store

```json
// mcp-servers/context-store/mcp-server.json
{
  "name": "context-store",
  "description": "Document storage with tagging and semantic search",
  "transport": {
    "type": "http",
    "url": "${CONTEXT_STORE_MCP_URL}"
  },
  "parameters_schema": {
    "type": "object",
    "properties": {
      "namespace": {
        "type": "string",
        "description": "Document namespace for scoping"
      }
    }
  },
  "support": {
    "health_endpoint": "/health",
    "documentation_url": "/docs/components/context-store/MCP.md",
    "version": "1.0.0"
  },
  "environments": {
    "development": {
      "url": "http://localhost:9501/mcp"
    },
    "docker": {
      "url": "http://context-store:9501/mcp"
    }
  },
  "tags": ["storage", "search", "documents"]
}
```

### Capability Using Registry

```json
// capabilities/document-research/capability.json
{
  "name": "document-research",
  "description": "Research documents in the context store",
  "mcp_servers": {
    "docs": {
      "server": "context-store",
      "parameters": {
        "namespace": "research-docs"
      }
    }
  }
}
```

### Agent Using Capability

```json
// agents/researcher/agent.json
{
  "name": "researcher",
  "description": "Research agent with document access",
  "capabilities": ["document-research", "orchestration"],
  "tags": ["research"]
}
```

Resolved blueprint includes:
```json
{
  "mcp_servers": {
    "docs": {
      "type": "http",
      "url": "http://localhost:9501/mcp",
      "headers": {
        "X-Namespace": "research-docs"
      }
    },
    "orchestrator": {
      "type": "http",
      "url": "http://127.0.0.1:9999",  // Resolved by Runner
      "headers": {
        "X-Agent-Session-Id": "ses_abc123"  // Resolved by Runner
      }
    }
  }
}
```

## Open Questions

1. **Registry Scope**: Should MCP servers be global or per-project? Current design assumes global registry.

2. **Credentials Management**: How to handle MCP server credentials (API keys, tokens)? Options:
   - Environment variables only (current approach)
   - Coordinator secrets store
   - External secrets manager integration

3. **Versioning**: Should MCP server definitions be versioned? Capabilities could pin to specific versions.

4. **Caching**: Should resolved configs be cached? Currently resolved on each request.

5. **Validation Timing**: When to validate MCP server connectivity?
   - At definition time (may fail if server not running)
   - At run time (may be too late)
   - Periodic health checks (background task)

## Summary

This design introduces a centralized MCP Server Registry that solves the problems of:
- Scattered, duplicated MCP configurations
- Limited discovery and visibility
- Static, environment-specific URLs
- Missing support metadata

The recommended approach (Approach 1) provides:
- Clear separation of concerns (MCP servers as first-class entities)
- Full CRUD API with discovery endpoints
- Environment-aware URL resolution
- Schema-validated parameterization
- Dashboard integration for management

Implementation can proceed incrementally:
1. Add registry storage and API
2. Add Dashboard management page
3. Migrate capabilities to reference format
4. Deprecate inline configs
