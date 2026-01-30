# MCP Server Registry - Implementation Report

## Status

✅ **Complete** - File-based storage implemented, inline format not supported.

## Implementation

### Storage

MCP servers stored as files in `config/mcp-servers/{id}/mcp-server.json`.

**Storage module**: `servers/agent-coordinator/mcp_server_storage.py`

Functions:
- `get_mcp_servers_dir()` - Get storage directory
- `list_mcp_servers()` - List all servers
- `get_mcp_server(id)` - Get by ID
- `create_mcp_server(data)` - Create new server
- `update_mcp_server(id, updates)` - Update server
- `delete_mcp_server(id)` - Delete server

### Models

**File**: `servers/agent-coordinator/models.py`

- `ConfigSchemaField` - Schema definition for a config field
- `MCPServerConfigSchema` - Type alias: `dict[str, ConfigSchemaField]`
- `MCPServerRegistryEntry` - Full registry entry
- `MCPServerRegistryCreate` - For POST requests
- `MCPServerRegistryUpdate` - For PUT requests
- `MCPServerRef` - Reference format in agent/capability configs

### Service Layer

**File**: `servers/agent-coordinator/services/mcp_registry.py`

- CRUD operations delegating to storage
- `resolve_mcp_server_ref()` - Resolve ref to URL + config
- `validate_required_config()` - Check required fields present

### REST API

```
GET    /mcp-servers           - List all
POST   /mcp-servers           - Create
GET    /mcp-servers/{id}      - Get by ID
PUT    /mcp-servers/{id}      - Update
DELETE /mcp-servers/{id}      - Delete
```

### Reference Format

All HTTP MCP configs use registry references:
```json
{
  "mcpServers": {
    "context-store": {
      "ref": "context-store",
      "config": {"context_id": "${scope.context_id}"}
    }
  }
}
```

**Exception**: stdio-based servers (Playwright) use inline format in agent configs.

## Registry Entries

Stored in `config/mcp-servers/`:

| ID | Name | URL |
|----|------|-----|
| `context-store` | Context Store | http://localhost:9501/mcp |
| `ado` | Azure DevOps | http://localhost:9001/mcp |
| `atlassian` | Atlassian | http://localhost:9000/mcp |
| `neo4j` | Neo4j Cypher | http://localhost:9003/mcp/ |
| `orchestrator` | Agent Orchestrator | ${runner.orchestrator_mcp_url} |

**Note**: Playwright is NOT in registry (stdio-based). Browser-tester agent uses inline stdio format.

## Files

| File | Purpose |
|------|---------|
| `mcp_server_storage.py` | File-based storage operations |
| `services/mcp_registry.py` | Service layer with ref resolution |
| `models.py` | Pydantic models |
| `tests/test_mcp_registry.py` | Unit tests (23 tests) |
| `config/mcp-servers/*/mcp-server.json` | Server configs (5 files) |
| `config/agents/browser-tester/agent.mcp.json` | Inline stdio for Playwright |

## Deferred

- Dashboard integration (MCP servers management page)
- Config schema editor in UI forms
