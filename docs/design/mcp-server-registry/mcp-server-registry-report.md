# MCP Server Registry - Implementation Report

## Summary

This report documents the implementation of the MCP Server Registry feature (Phase 2).

## Status

✅ **Complete**

## What Will Be Implemented

### 1. Database Schema & Models

**Files:**
- `servers/agent-coordinator/database.py` - Add `mcp_servers` table
- `servers/agent-coordinator/models.py` - Add registry models

**Database Table:**
```sql
CREATE TABLE mcp_servers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    config_schema TEXT,  -- JSON
    default_config TEXT, -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
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

### 4. Reference Syntax (Replaces Inline Format)

**Decision:** Drop inline format, require registry refs.

All MCP configs must use registry references:
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

The inline format (`type: "http"`, `type: "stdio"`) is no longer supported.

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
- Error cases (missing registry entry, invalid ref, etc.)

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

## Migration Strategy

### Backward Compatibility

The implementation supports BOTH inline format and ref-based format simultaneously:

**Inline format (legacy):**
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

**Ref format (new):**
```json
{
  "mcpServers": {
    "context-store": {
      "ref": "context-store",
      "config": {}
    }
  }
}
```

This allows gradual migration:
1. Create registry entries for MCP servers as needed
2. Update agent/capability configs to use refs when convenient
3. No forced migration - inline format continues to work

### Migration Steps (When Ready)

1. Create registry entry via POST /mcp-servers
2. Update `.mcp.json` file to use `{"ref": "...", "config": {...}}`
3. Test the agent/capability works correctly

## Files Changed Summary

| File | Change Type |
|------|------------|
| `servers/agent-coordinator/database.py` | Modified |
| `servers/agent-coordinator/models.py` | Modified |
| `servers/agent-coordinator/services/mcp_registry.py` | Created |
| `servers/agent-coordinator/services/placeholder_resolver.py` | Modified |
| `servers/agent-coordinator/main.py` | Modified |
| `servers/agent-coordinator/agent_storage.py` | Modified |
| `servers/agent-coordinator/capability_storage.py` | Modified |
| `servers/agent-coordinator/tests/test_mcp_registry.py` | Created |

## Implementation Progress

- [x] Database schema & models
- [x] Registry storage service
- [x] REST API endpoints
- [x] Reference syntax models (MCPServerRef)
- [x] Blueprint resolver with registry lookups
- [x] Required config validation
- [x] Tests
- [x] Backward compatibility for inline format
- [ ] (Optional) Migrate existing configs to ref format
- [ ] (Optional) Populate registry with existing MCP servers
