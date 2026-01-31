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
- `validate_required_config()` - Check required fields present (detects unresolved placeholders)

### Required Config Validation

At run creation, required config fields are validated after placeholder resolution:
- Missing required fields → 400 error with `missing_required_mcp_config`
- Unresolved placeholders (e.g., `${scope.missing}`) → treated as missing
- Embedded placeholders (e.g., `Bearer ${scope.token}`) → also detected via regex

**Error response:**
```json
{
  "error": "missing_required_mcp_config",
  "message": "MCP server 'orchestrator' missing required config: X-Agent-Session-Id",
  "server_name": "orchestrator",
  "missing_fields": ["X-Agent-Session-Id"]
}
```

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

| ID | Name | URL | Config Schema |
|----|------|-----|---------------|
| `context-store` | Context Store | http://localhost:9501/mcp | - |
| `ado` | Azure DevOps | http://localhost:9001/mcp | - |
| `atlassian` | Atlassian | http://localhost:9000/mcp | - |
| `neo4j` | Neo4j Cypher | http://localhost:9003/mcp/ | - |
| `orchestrator` | Agent Orchestrator | ${runner.orchestrator_mcp_url} | X-Agent-Session-Id (required), X-Agent-Tags, X-Additional-Demands |

### Orchestrator Config Schema

The orchestrator MCP server has `config_schema` defining HTTP headers and `default_config` for common defaults:

```json
{
  "config_schema": {
    "X-Agent-Session-Id": {"type": "string", "required": true},
    "X-Agent-Tags": {"type": "string", "required": false},
    "X-Additional-Demands": {"type": "string", "required": false}
  },
  "default_config": {
    "X-Agent-Session-Id": "${runtime.session_id}"
  }
}
```

Config keys map directly to HTTP header names. The `default_config` provides `X-Agent-Session-Id` automatically via placeholder.

## Files

| File | Purpose |
|------|---------|
| `mcp_server_storage.py` | File-based storage operations |
| `services/mcp_registry.py` | Service layer with ref resolution |
| `models.py` | Pydantic models |
| `tests/test_mcp_registry.py` | Unit tests (24 tests) |
| `config/mcp-servers/*/mcp-server.json` | Server configs (5 files) |
| `config/agents/browser-tester/agent.mcp.json` | Inline stdio for Playwright |

## Dashboard Integration

### MCP Servers Management Page

New page at `/mcp-servers` for managing MCP server registry entries.

**Features:**
- Table with ID, Name, URL, Config Fields columns
- Create/Edit/Delete MCP servers
- Config schema editor with field types (string, integer, boolean)
- Default config values editor

**Files:**
- `apps/dashboard/src/pages/McpServers.tsx` - Page component
- `apps/dashboard/src/components/features/mcp-servers/McpServerTable.tsx` - Table
- `apps/dashboard/src/components/features/mcp-servers/McpServerEditor.tsx` - Modal editor
- `apps/dashboard/src/components/features/mcp-servers/ConfigSchemaEditor.tsx` - Schema editor

### MCPServerSelector Component

New component replacing `MCPJsonEditor` for selecting MCP servers in agent/capability editors.

**Features:**
- Dropdown to add servers from registry
- Config fields rendered based on registry's config_schema
- Config values override registry defaults (inheritance: registry → capability → agent)
- Shows default values from registry
- Placeholder documentation via info popover

**File:** `apps/dashboard/src/components/features/agents/MCPServerSelector.tsx`

### Type Changes

**Added to `types/agent.ts`:**
- `MCPServerRef` interface: `{ref: string, config?: Record<string, unknown>}`
- `isMCPServerRef()` type guard
- `isMCPServerStdio()` type guard

**Removed:**
- `MCPServerHttp` type (HTTP servers must use registry refs)

**New file `types/mcpServer.ts`:**
- `ConfigSchemaField` - Schema definition for config field
- `MCPServerConfigSchema` - Type alias for schema dict
- `MCPServerRegistryEntry` - Full registry entry
- `MCPServerRegistryCreate` - For POST requests
- `MCPServerRegistryUpdate` - For PUT requests

### Files Modified

| File | Change |
|------|--------|
| `types/agent.ts` | Added MCPServerRef, removed MCPServerHttp |
| `types/index.ts` | Export mcpServer types |
| `router.tsx` | Added /mcp-servers route |
| `components/layout/Sidebar.tsx` | Added MCP Servers nav item |
| `pages/index.ts` | Export McpServers page |
| `components/features/agents/AgentEditor.tsx` | Use MCPServerSelector |
| `components/features/capabilities/CapabilityEditor.tsx` | Use MCPServerSelector |

### Files Deleted

- `utils/mcpTemplates.ts` - Template quick-add buttons replaced by registry
- `components/features/agents/MCPJsonEditor.tsx` - Replaced by MCPServerSelector

### New Files

| File | Purpose |
|------|---------|
| `types/mcpServer.ts` | Registry TypeScript types |
| `services/mcpServerService.ts` | API service for /mcp-servers |
| `hooks/useMcpServers.ts` | React hook for MCP servers |
| `pages/McpServers.tsx` | Management page |
| `components/features/mcp-servers/index.ts` | Barrel export |
| `components/features/mcp-servers/McpServerTable.tsx` | Table component |
| `components/features/mcp-servers/McpServerEditor.tsx` | Editor modal |
| `components/features/mcp-servers/ConfigSchemaEditor.tsx` | Config schema editor |
| `components/features/agents/MCPServerSelector.tsx` | Server selector for editors |
| `components/features/mcp-servers/PlaceholderInfo.tsx` | Placeholder documentation popover |

## Executor Integration

### Claude Code Format Transformation

The Claude Code executor transforms MCP configs from coordinator format to Claude Code SDK format.

**File:** `servers/agent-runner/executors/claude-code/lib/claude_client.py`

**Function:** `transform_mcp_servers_for_claude_code()`

```
Coordinator format:     {"url": "...", "config": {...}}
Claude Code format:     {"type": "http", "url": "...", "headers": {...}}
```

The transformation:
- Renames `config` → `headers` (config values become HTTP headers)
- Adds `type: "http"` (only HTTP MCP servers supported via registry)

This keeps the registry simple (no `type` field needed) while producing the correct format for Claude Code.

### Config Structure

Config uses **flat structure** - no nested `headers` object:

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

Config keys map directly to HTTP header names. The registry's `default_config` provides common defaults (e.g., `X-Agent-Session-Id`), so agents only specify overrides.
