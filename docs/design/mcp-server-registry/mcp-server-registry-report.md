# MCP Server Registry - Implementation Report

## Summary

This report documents the implementation of the MCP Server Registry feature (Phase 2).

## Status

✅ **Complete** - File-based storage implemented, inline format no longer supported.

## What Was Implemented

### 1. File-Based Storage & Models

**Files:**
- `servers/agent-coordinator/mcp_server_storage.py` - File I/O operations for MCP server registry
- `servers/agent-coordinator/models.py` - Registry models

**Storage Structure:**
```
config/mcp-servers/{id}/
    mcp-server.json     # Server configuration
```

**Example `mcp-server.json`:**
```json
{
  "id": "context-store",
  "name": "Context Store",
  "description": "Stores and retrieves agent context data",
  "url": "http://localhost:9501/mcp",
  "config_schema": {
    "fields": {
      "context_id": {"type": "string", "required": true}
    }
  },
  "default_config": {"timeout": 30}
}
```

**Models:**
- `MCPServerRegistryEntry` - Full registry entry
- `MCPServerRegistryCreate` - For POST requests
- `MCPServerRegistryUpdate` - For PUT requests
- `MCPServerRef` - Reference format in agent/capability configs

### 2. Registry Storage Service

**File:** `servers/agent-coordinator/services/mcp_registry.py`

Functions:
- `list_mcp_servers()` - List all registry entries
- `get_mcp_server(id)` - Get single entry by ID
- `create_mcp_server(entry)` - Create new entry
- `update_mcp_server(id, entry)` - Update existing entry
- `delete_mcp_server(id)` - Delete entry
- `validate_config_schema(schema)` - Validate schema structure

### 3. REST API Endpoints

**File:** `servers/agent-coordinator/main.py`

```
GET    /mcp-servers           - List all MCP servers
POST   /mcp-servers           - Create MCP server
GET    /mcp-servers/{id}      - Get MCP server by ID
PUT    /mcp-servers/{id}      - Update MCP server
DELETE /mcp-servers/{id}      - Delete MCP server
```

### 4. Reference Syntax (Required Format)

All MCP configs **must** use registry references for HTTP servers:
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

The inline format (`type: "http"`) is **not supported** and will raise an error.

**Exception:** stdio-based servers (like Playwright) use inline format directly in agent configs since the registry only supports HTTP servers.

### 5. Blueprint Resolution with Registry Lookups

**File:** `servers/agent-coordinator/services/placeholder_resolver.py`

Enhanced resolution:
1. For each MCP server with `ref` field:
   - Lookup registry entry by ID
   - Get URL from registry
   - Merge configs: registry defaults → capability → agent
2. Resolve placeholders (existing)
3. Validate required values (new - using `config_schema.required`)

### 6. Required Config Validation

**File:** `servers/agent-coordinator/main.py`

In `create_run()`:
- After resolving blueprint, validate required configs
- If missing required values, return HTTP 400 with clear error message

### 7. Tests

**File:** `servers/agent-coordinator/tests/test_mcp_registry.py`

Test cases:
- CRUD operations on registry
- Config schema validation
- Registry reference resolution
- Config inheritance chain
- Required value validation
- Inline format rejection (error cases)

## Registry Entries

The following MCP servers are stored in `config/mcp-servers/`:

| ID | Name | URL | Description |
|----|------|-----|-------------|
| `context-store` | Context Store | http://localhost:9501/mcp | Stores and retrieves agent context data |
| `ado` | Azure DevOps | http://localhost:9001/mcp | Azure DevOps work items and pipelines |
| `atlassian` | Atlassian | http://localhost:9000/mcp | Jira and Confluence integration |
| `neo4j` | Neo4j Cypher | http://localhost:9003/mcp/ | Neo4j graph database queries |
| `orchestrator` | Agent Orchestrator | ${runner.orchestrator_mcp_url} | Spawn and manage child agents |

**Note:** Playwright is NOT in the registry (it's stdio-based). The `browser-tester` agent uses inline stdio format:
```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

## Migrated Config Files

### Capabilities (5 files)
- `config/capabilities/context-store/capability.mcp.json` → `{"ref": "context-store"}`
- `config/capabilities/ado/capability.mcp.json` → `{"ref": "ado"}`
- `config/capabilities/atlassian/capability.mcp.json` → `{"ref": "atlassian"}`
- `config/capabilities/project-knowledge/capability.mcp.json` → `{"ref": "neo4j"}`
- `config/capabilities/agent-orchestrator/capability.mcp.json` → `{"ref": "orchestrator", "config": {...}}`

### Agents (13 files)
- `config/agents/ado-agent/agent.mcp.json`
- `config/agents/agent-orchestrator/agent.mcp.json`
- `config/agents/agent-orchestrator-external/agent.mcp.json`
- `config/agents/agent-orchestrator-internal/agent.mcp.json`
- `config/agents/atlassian-agent/agent.mcp.json`
- `config/agents/browser-tester/agent.mcp.json` (inline stdio for Playwright)
- `config/agents/bug-evaluator/agent.mcp.json`
- `config/agents/context-store-agent/agent.mcp.json`
- `config/agents/knowledge-coordinator/agent.mcp.json`
- `config/agents/knowledge-project-context-agent/agent.mcp.json`
- `config/agents/module-research-coordinator/agent.mcp.json`
- `config/agents/neo4j-agent/agent.mcp.json`
- `config/agents/self-improving-agent/agent.mcp.json`

## What Is Deferred

### Dashboard Integration

**Reason:** Focus on backend/API first, dashboard can be added later.

The following dashboard features are deferred:
- MCP Servers management page (list, create, edit, delete)
- Config schema editor in capability/agent forms
- Visual inheritance chain display

**Breaking Change Impact:**
- Dashboard has templates for old inline MCP config format
- These templates must be updated to use ref-based format
- Agent/capability creation forms need to reference registry instead of inline config
- This is a required change when dashboard is implemented

## Files Changed Summary

| File | Change Type |
|------|------------|
| `servers/agent-coordinator/mcp_server_storage.py` | Created |
| `servers/agent-coordinator/models.py` | Modified |
| `servers/agent-coordinator/services/mcp_registry.py` | Modified |
| `servers/agent-coordinator/services/placeholder_resolver.py` | Modified |
| `servers/agent-coordinator/main.py` | Modified |
| `servers/agent-coordinator/agent_storage.py` | Modified |
| `servers/agent-coordinator/capability_storage.py` | Modified |
| `servers/agent-coordinator/database.py` | Modified (removed MCP table/functions) |
| `servers/agent-coordinator/tests/test_mcp_registry.py` | Modified |
| `config/mcp-servers/*/mcp-server.json` | Created (5 files) |
| `config/capabilities/*.mcp.json` | Modified (5 files) |
| `config/agents/*.mcp.json` | Modified (13 files) |

**Deleted:**
- `servers/agent-coordinator/data/mcp_servers_seed.json` (replaced by file-based storage)

## Implementation Progress

- [x] File-based storage & models
- [x] Registry storage service
- [x] REST API endpoints
- [x] Reference syntax models (MCPServerRef)
- [x] Blueprint resolver with registry lookups
- [x] Required config validation
- [x] Tests
- [x] Remove backward compatibility for inline format
- [x] Migrate existing configs to ref format
- [x] Create registry config files
- [x] Handle stdio servers (Playwright) with inline format
