# Design: STDIO MCP Server Support

**Status:** Draft
**Author:** Architecture Review
**Date:** 2025-02-03

## Overview

This design introduces STDIO MCP server support to the MCP Server Registry, enabling locally-executed MCP servers that communicate via stdin/stdout. STDIO MCP servers are defined in the registry and reference centralized scripts for code delivery.

**Key Principle:** STDIO MCP servers combine two existing features:
- **MCP Server Registry** - defines the server configuration and metadata
- **Centralized Script Management** - delivers the executable code to runners

This is the first feature where these two systems intersect, requiring careful design to maintain consistency and robustness.

## Motivation

### Current Limitation

The MCP Server Registry only supports HTTP-based MCP servers:
- Servers must be network-accessible
- Requires running external services
- Not suitable for local-only tools or air-gapped environments

### Motivating Example: Context Store MCP

The **Context Store** is a document management system that persists knowledge across agent sessions. Its MCP server provides tools for document operations:

| Tool | Purpose |
|------|---------|
| `doc_create`, `doc_write`, `doc_edit` | Create and modify documents |
| `doc_query`, `doc_search`, `doc_read` | Find and read documents |
| `doc_push` | **Upload a local file** to Context Store |
| `doc_pull` | **Download a document** to local filesystem |

**The Problem with HTTP for File Operations:**

The `doc_push` and `doc_pull` tools operate on **local file paths**. When an agent needs to upload a file it created or download a document to process locally:

```
Agent creates file:     /project/output/report.csv
Agent calls:            doc_push(file_path="/project/output/report.csv")
MCP server must:        Read file from /project/output/report.csv
```

| Transport | MCP Server Location | File Access | Works? |
|-----------|---------------------|-------------|--------|
| HTTP | Remote container | Different filesystem | **No** |
| HTTP | Same host | Same filesystem | Yes, but... |
| STDIO | Agent subprocess | **Same filesystem** | **Yes** |

**Why HTTP Falls Short:**

With HTTP-based MCP, the workaround for file operations is:
1. Agent reads file content into memory
2. Agent passes content as parameter to `doc_write` (instead of `doc_push`)
3. Content flows through the LLM context

This **wastes tokens** - a 100KB file consumes ~25K tokens just for transport. For downloading, the agent must receive the entire content through `doc_read`, process it, and write to disk manually.

**Why STDIO is Essential:**

With STDIO transport, the MCP server runs as a **subprocess of the agent**, sharing the same filesystem:

```
Agent (executor)
    └── spawns → MCP Server (STDIO subprocess)
                     └── can read/write same files as agent
```

The `doc_push` and `doc_pull` operations become efficient:
- **Push:** MCP server reads file directly from disk, uploads to Context Store
- **Pull:** MCP server downloads from Context Store, writes directly to disk
- **No token overhead** - file content never passes through LLM context

This enables agents to efficiently manage large files, generated artifacts, and local workspace content.

### Use Cases for STDIO MCP Servers

1. **Local file processing tools** - MCP servers that operate on local filesystem (like Context Store push/pull)
2. **Development/testing** - Run MCP servers without network infrastructure
3. **Air-gapped environments** - Deployments without external network access
4. **Custom tools** - Project-specific MCP servers distributed with agents

### Why Combine with Scripts?

STDIO MCP servers require executable code to be present on the runner. The Scripts feature already solves code distribution:
- Centralized storage in Coordinator
- Automatic sync to runners
- PEP 723 inline dependency management
- Consistent deployment model

**Principle:** An STDIO MCP server entry MUST reference a script. This ensures:
- Code is version-controlled and centrally managed
- Dependencies are explicitly declared
- Deployment is consistent across runners
- No arbitrary command execution

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Referential Integrity** | Strict | Script must exist when creating STDIO MCP entry; script deletion blocked if referenced |
| **Script Path Resolution** | Runner-side via `${runner.scripts_dir}` | Runner owns the scripts directory and knows its filesystem |
| **Config Handling** | Same abstraction for HTTP and STDIO | `config` field transformed at executor: HTTP→headers, STDIO→env |
| **Script Sync Scope** | Out of scope | Current workaround (shared PROJECT_DIR volume) works |
| **Script Changes** | None | Scripts remain unchanged; MCP registry entry determines usage |
| **Circular Dependencies** | Not possible | One-directional: MCP entry → Script (script has no awareness) |

## Architecture

### Component Interaction

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AGENT COORDINATOR                                │
│                                                                          │
│  ┌─────────────────────┐        ┌─────────────────────┐                 │
│  │  MCP Server Registry │        │   Script Storage    │                 │
│  │                      │        │                     │                 │
│  │  ┌────────────────┐ │  ref   │  ┌───────────────┐  │                 │
│  │  │ STDIO Entry    │─┼────────┼─>│ MCP Script    │  │                 │
│  │  │ script: "x"    │ │        │  │ server.py     │  │                 │
│  │  └────────────────┘ │        │  └───────────────┘  │                 │
│  │                      │        │                     │                 │
│  │  ┌────────────────┐ │        │  ┌───────────────┐  │                 │
│  │  │ HTTP Entry     │ │        │  │ CLI Script    │  │                 │
│  │  │ url: "..."     │ │        │  │ process.py    │  │                 │
│  │  └────────────────┘ │        │  └───────────────┘  │                 │
│  └─────────────────────┘        └─────────────────────┘                 │
│                                                                          │
│  Referential Integrity:                                                  │
│  - STDIO entry creation validates script exists                          │
│  - Script deletion blocked if referenced by MCP entry                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                    │                         │
                    │ Blueprint               │ Script Sync
                    │ (${runner.*} preserved) │ (existing mechanism)
                    ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           AGENT RUNNER                                   │
│                                                                          │
│  Resolves ${runner.scripts_dir} placeholder                              │
│  (Runner knows its filesystem layout)                                    │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    EXECUTOR                                        │  │
│  │                                                                    │  │
│  │  Transforms config based on type:                                  │  │
│  │  - HTTP:  config → headers                                         │  │
│  │  - STDIO: config → env                                             │  │
│  │                                                                    │  │
│  │  Claude SDK spawns MCP server as subprocess                        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Resolution Flow (Complete)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          COORDINATOR                                     │
│                                                                          │
│  1. Agent ref: {"ref": "my-stdio", "config": {"debug": "true"}}         │
│                                                                          │
│  2. Registry lookup: MCPServerRegistryEntry                              │
│     - type: "stdio"                                                      │
│     - script: "file-processor"                                           │
│     - default_config: {"working_dir": "${runtime.project_dir}"}          │
│                                                                          │
│  3. Merge configs + resolve Coordinator placeholders                     │
│     config: {"working_dir": "/project", "debug": "true"}                 │
│                                                                          │
│  4. Build resolved blueprint (keep ${runner.*} unresolved):              │
│     {                                                                    │
│       "type": "stdio",                                                   │
│       "command": "uv",                                                   │
│       "args": ["run", "--script",                                        │
│                "${runner.scripts_dir}/file-processor/server.py"],        │
│       "config": {"working_dir": "/project", "debug": "true"}             │
│     }                                                                    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            RUNNER                                        │
│                                                                          │
│  5. Resolve ${runner.scripts_dir} → /app/project/scripts                 │
│     {                                                                    │
│       "type": "stdio",                                                   │
│       "command": "uv",                                                   │
│       "args": ["run", "--script",                                        │
│                "/app/project/scripts/file-processor/server.py"],         │
│       "config": {"working_dir": "/project", "debug": "true"}             │
│     }                                                                    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           EXECUTOR                                       │
│                                                                          │
│  6. transform_mcp_servers_for_claude_code():                             │
│     - HTTP:  config → headers                                            │
│     - STDIO: config → env                                                │
│                                                                          │
│     {                                                                    │
│       "type": "stdio",                                                   │
│       "command": "uv",                                                   │
│       "args": ["run", "--script",                                        │
│                "/app/project/scripts/file-processor/server.py"],         │
│       "env": {"working_dir": "/project", "debug": "true"}                │
│     }                                                                    │
│                                                                          │
│  7. Claude SDK spawns subprocess with env vars                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Model

### Extended MCPServerRegistryEntry

The registry entry model is extended to support both HTTP and STDIO types:

```python
class MCPServerRegistryEntry(BaseModel):
    """MCP server definition in the registry."""

    # Common fields
    id: str                                    # Unique identifier
    name: str                                  # Human-readable name
    description: Optional[str] = None          # Description
    type: Literal["http", "stdio"] = "http"   # Transport type

    # HTTP-specific (required when type="http")
    url: Optional[str] = None                  # HTTP endpoint URL

    # STDIO-specific (required when type="stdio")
    script: Optional[str] = None               # Script reference (name)

    # Common configuration (works for both types)
    config_schema: Optional[MCPServerConfigSchema] = None
    default_config: Optional[dict[str, Any]] = None

    # Metadata
    created_at: str
    updated_at: str
```

### Validation Rules

| Type | Required Fields | Forbidden Fields |
|------|-----------------|------------------|
| `http` | `url` | `script` |
| `stdio` | `script` | `url` |

```python
@model_validator(mode='after')
def validate_type_fields(self) -> 'MCPServerRegistryEntry':
    if self.type == "http":
        if not self.url:
            raise ValueError("HTTP MCP servers require 'url' field")
        if self.script:
            raise ValueError("HTTP MCP servers cannot have 'script' field")
    elif self.type == "stdio":
        if not self.script:
            raise ValueError("STDIO MCP servers require 'script' field")
        if self.url:
            raise ValueError("STDIO MCP servers cannot have 'url' field")
    return self
```

### Referential Integrity

**On STDIO MCP entry creation/update:**

```python
async def create_mcp_server(entry: MCPServerRegistryEntry):
    if entry.type == "stdio":
        script = script_storage.get_script(entry.script)
        if script is None:
            raise ScriptNotFoundError(f"Script '{entry.script}' not found")
```

**On script deletion:**

```python
async def delete_script(script_name: str):
    refs = mcp_server_storage.get_references_to_script(script_name)
    if refs:
        raise ScriptInUseError(
            f"Script '{script_name}' is referenced by MCP servers: {refs}"
        )
    # Proceed with deletion
```

## The `config` Abstraction

The `config` field provides a **unified abstraction** for MCP server configuration that works for both HTTP and STDIO transports. The transformation happens at the executor level.

### Config Flow

```
Registry default_config  →  Ref config override  →  Placeholder resolution  →  Executor transform
        │                          │                        │                         │
        │                          │                        │                         │
  {"key": "default"}         {"key": "value"}         {"key": "resolved"}      HTTP: headers
                                                                                STDIO: env
```

### HTTP: config → headers

For HTTP MCP servers, `config` values become HTTP headers:

```python
# Input (from resolved blueprint)
{"type": "http", "url": "...", "config": {"X-Context-Id": "123"}}

# Output (to Claude SDK)
{"type": "http", "url": "...", "headers": {"X-Context-Id": "123"}}
```

### STDIO: config → env

For STDIO MCP servers, `config` values become environment variables:

```python
# Input (from resolved blueprint)
{"type": "stdio", "command": "uv", "args": [...], "config": {"working_dir": "/data"}}

# Output (to Claude SDK)
{"type": "stdio", "command": "uv", "args": [...], "env": {"working_dir": "/data"}}
```

**Note:** Config keys are used directly as environment variable names (no prefix transformation). This keeps the abstraction clean and allows scripts to read predictable env var names.

## Persistence

### File Format

STDIO entries are stored in the same directory structure as HTTP entries:

```
config/mcp-servers/
├── context-store/              # HTTP example
│   └── mcp-server.json
└── local-file-processor/       # STDIO example
    └── mcp-server.json
```

**HTTP Entry (existing):**
```json
{
  "id": "context-store",
  "name": "Context Store",
  "type": "http",
  "url": "http://localhost:9501/mcp",
  "config_schema": {
    "X-Context-Id": {
      "type": "string",
      "description": "Context ID for isolation",
      "required": true
    }
  },
  "default_config": {
    "X-Context-Id": "${runtime.session_id}"
  }
}
```

**STDIO Entry (new):**
```json
{
  "id": "local-file-processor",
  "name": "Local File Processor",
  "type": "stdio",
  "script": "file-processor-mcp",
  "config_schema": {
    "working_dir": {
      "type": "string",
      "description": "Directory to process files in",
      "required": false
    }
  },
  "default_config": {
    "working_dir": "${runtime.project_dir}"
  }
}
```

### Backward Compatibility

Existing entries without `type` field default to `"http"`:

```python
def load_mcp_server(path: Path) -> MCPServerRegistryEntry:
    data = json.loads(path.read_text())
    # Default type for backward compatibility
    if "type" not in data:
        data["type"] = "http"
    return MCPServerRegistryEntry(**data)
```

## Runner Placeholder: `${runner.scripts_dir}`

A new runner-level placeholder is introduced for STDIO MCP servers.

### Why Runner Resolves

The script path cannot be resolved at the Coordinator because:
- Only the Runner knows its filesystem layout
- `PROJECT_DIR` varies per runner deployment
- Consistent with existing `${runner.orchestrator_mcp_url}` pattern

### Placeholder Resolution

**In `executor.py` (alongside existing `${runner.orchestrator_mcp_url}`):**

```python
def _resolve_runner_placeholders(self, blueprint: dict) -> dict:
    """Resolve ${runner.*} placeholders in blueprint."""
    RUNNER_PLACEHOLDER = re.compile(r'\$\{runner\.([^}]+)\}')

    def resolve_string(s: str) -> str:
        def replace_match(match: re.Match) -> str:
            key = match.group(1)
            if key == 'orchestrator_mcp_url':
                return self.mcp_server_url or match.group(0)
            if key == 'scripts_dir':
                return str(self.scripts_dir)  # NEW
            return match.group(0)
        return RUNNER_PLACEHOLDER.sub(replace_match, s)

    return self._resolve_in_dict(blueprint, resolve_string)
```

### Scripts Directory

```python
@property
def scripts_dir(self) -> Path:
    """Scripts directory path."""
    project_dir = os.environ.get("PROJECT_DIR", os.getcwd())
    return Path(project_dir) / "scripts"
```

## Blueprint Resolution

### Coordinator Resolution

When resolving STDIO MCP server references, the Coordinator:

1. Looks up the registry entry
2. Validates script exists (referential integrity)
3. Builds command/args with `${runner.scripts_dir}` placeholder
4. Merges config (registry defaults + ref config)
5. Resolves Coordinator-level placeholders (but NOT `${runner.*}`)

**Input (agent config):**
```json
{
  "mcpServers": {
    "processor": {
      "ref": "local-processor",
      "config": {
        "output_format": "json"
      }
    }
  }
}
```

**Output (resolved blueprint):**
```json
{
  "mcp_servers": {
    "processor": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--script", "${runner.scripts_dir}/file-processor-mcp/server.py"],
      "config": {
        "working_dir": "/project",
        "output_format": "json"
      }
    }
  }
}
```

### Script File Resolution

The Coordinator needs to know the script's `script_file` to build the full path:

```python
def resolve_stdio_mcp_ref(entry: MCPServerRegistryEntry, provided_config: dict) -> dict:
    """Resolve STDIO MCP server reference."""
    # Get script metadata for script_file
    script = script_storage.get_script(entry.script)
    script_path = f"${{runner.scripts_dir}}/{entry.script}/{script.script_file}"

    # Merge configs
    merged_config = {}
    if entry.default_config:
        merged_config.update(entry.default_config)
    if provided_config:
        merged_config.update(provided_config)

    return {
        "type": "stdio",
        "command": "uv",
        "args": ["run", "--script", script_path],
        "config": merged_config,
    }
```

## Executor Transformation

### Updated `transform_mcp_servers_for_claude_code()`

The executor transformation is extended to handle both HTTP and STDIO:

```python
def transform_mcp_servers_for_claude_code(mcp_servers: dict) -> dict:
    """Transform MCP servers from coordinator format to Claude Code format.

    The coordinator resolves MCP server refs and produces:
        HTTP:  {"url": "...", "config": {...}}
        STDIO: {"command": "...", "args": [...], "config": {...}}

    Claude Code expects:
        HTTP:  {"type": "http", "url": "...", "headers": {...}}
        STDIO: {"type": "stdio", "command": "...", "args": [...], "env": {...}}

    This transformation:
    - HTTP:  Renames 'config' to 'headers'
    - STDIO: Renames 'config' to 'env'
    """
    transformed = {}

    for server_name, server_config in mcp_servers.items():
        server_type = server_config.get("type", "http")

        if server_type == "http":
            # Existing HTTP transformation
            transformed[server_name] = {
                "type": "http",
                "url": server_config.get("url", ""),
                "headers": server_config.get("config", {}),
            }
        elif server_type == "stdio":
            # NEW: STDIO transformation
            transformed[server_name] = {
                "type": "stdio",
                "command": server_config["command"],
                "args": server_config.get("args", []),
                "env": server_config.get("config", {}),
            }

    return transformed
```

## API Changes

### Create/Update MCP Server

The existing API accepts the new `type` and `script` fields:

```
POST /mcp-servers
```

**Request (STDIO):**
```json
{
  "id": "local-processor",
  "name": "Local File Processor",
  "type": "stdio",
  "script": "file-processor-mcp",
  "config_schema": {
    "working_dir": {
      "type": "string",
      "description": "Working directory",
      "required": false
    }
  },
  "default_config": {
    "working_dir": "${runtime.project_dir}"
  }
}
```

### Validation Errors

```json
{
  "error": "validation_error",
  "message": "STDIO MCP servers require 'script' field",
  "field": "script"
}
```

```json
{
  "error": "script_not_found",
  "message": "Script 'file-processor-mcp' not found",
  "script": "file-processor-mcp"
}
```

### List MCP Servers

Response includes type information:

```json
[
  {
    "id": "context-store",
    "name": "Context Store",
    "type": "http",
    "url": "http://localhost:9501/mcp"
  },
  {
    "id": "local-processor",
    "name": "Local File Processor",
    "type": "stdio",
    "script": "file-processor-mcp"
  }
]
```

## Script Requirements

### No Changes to Scripts

Scripts used as STDIO MCP servers are **standard scripts** with no special modifications:
- Same `script.json` format
- Same PEP 723 inline dependencies
- Same sync mechanism

A script doesn't "know" if it's used as an MCP server. The MCP registry entry is what designates a script as an MCP server.

**Note:** Complex MCP servers with multiple modules (like Context Store MCP) require consolidation into a single file for the current script system. See [Packaging Challenge](./packaging-challenge.md) for details and future enhancement options.

### Example MCP Server Script

**script.json:**
```json
{
  "name": "file-processor-mcp",
  "description": "MCP server for local file processing",
  "script_file": "server.py",
  "parameters_schema": {},
  "demands": {
    "tags": ["uv", "python3"]
  }
}
```

**server.py:**
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.0.0"]
# ///
"""Local file processor MCP server."""

import os
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("file-processor")

@server.list_tools()
async def list_tools():
    return [
        {
            "name": "process_file",
            "description": "Process a local file",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        }
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "process_file":
        # Config values are available as env vars
        working_dir = os.environ.get("working_dir", ".")
        path = os.path.join(working_dir, arguments["path"])
        # ... process file ...
        return {"status": "processed", "path": path}

if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(server))
```

## Deployment

### Script Availability

Scripts are available to executors through the existing script sync mechanism:
- Procedural runners sync scripts from Coordinator
- Autonomous runners share the same `PROJECT_DIR` volume

**Current workaround (no changes needed):**
```yaml
services:
  autonomous-runner:
    volumes:
      - project_data:/app/project
    environment:
      - PROJECT_DIR=/app/project

  procedural-runner:
    volumes:
      - project_data:/app/project
    environment:
      - PROJECT_DIR=/app/project
```

Scripts synced by the procedural runner are available to the autonomous runner via shared volume.

### Runner Requirements

Runners that execute STDIO MCP servers need:
- Access to scripts directory (`{PROJECT_DIR}/scripts/`)
- `uv` installed for script execution
- Python 3.11+ environment

## Error Handling

### Creation Errors

| Error | When | Message |
|-------|------|---------|
| `script_not_found` | STDIO entry references non-existent script | "Script 'X' not found" |
| `missing_script_field` | STDIO entry without script | "STDIO MCP servers require 'script' field" |
| `conflicting_fields` | STDIO entry with url | "STDIO MCP servers cannot have 'url' field" |

### Deletion Errors

| Error | When | Message |
|-------|------|---------|
| `script_in_use` | Delete script referenced by MCP entry | "Script 'X' is referenced by MCP servers: [Y, Z]" |

### Runtime Errors

| Error | When | Message |
|-------|------|---------|
| `script_not_synced` | Script not found on runner at execution | "Script 'X' not found at {path}" |

## Dashboard Integration

### MCP Servers List

Display type column:

| Name | Type | URL / Script | Config Fields |
|------|------|--------------|---------------|
| Context Store | HTTP | http://localhost:9501/mcp | 2 |
| File Processor | STDIO | file-processor-mcp | 1 |

### Create/Edit Form

Type selector determines visible fields:

```
Type: [HTTP ▼] / [STDIO]

--- If HTTP ---
URL: [http://localhost:9501/mcp    ]

--- If STDIO ---
Script: [file-processor-mcp ▼]     <- Dropdown of available scripts
```

### Script Dropdown

Populated from `/scripts` API:

```typescript
const scripts = await fetch('/api/scripts').then(r => r.json());
const scriptOptions = scripts.map(s => ({
  value: s.name,
  label: `${s.name} - ${s.description}`
}));
```

## Implementation Phases

### Phase 1: Model & Persistence
- Extend `MCPServerRegistryEntry` model with `type` and `script` fields
- Add model validation rules
- Update persistence layer for new fields
- Backward compatibility for existing entries (default `type: "http"`)

### Phase 2: Referential Integrity
- Add script existence validation on STDIO entry creation
- Add script-in-use check on script deletion
- API error responses for validation failures

### Phase 3: Blueprint Resolution
- Extend `resolve_mcp_server_refs()` for STDIO type
- Build command/args with `${runner.scripts_dir}` placeholder
- Resolve script's `script_file` for full path

### Phase 4: Runner Placeholder
- Add `scripts_dir` to runner placeholder resolution
- Test alongside existing `orchestrator_mcp_url`

### Phase 5: Executor Transformation
- Extend `transform_mcp_servers_for_claude_code()` for STDIO
- Config → env transformation
- Test with Claude SDK STDIO support

### Phase 6: Dashboard
- Type selector in create/edit form
- Script dropdown for STDIO entries
- List view with type column
- Validation feedback

## References

- [MCP Server Registry](../../features/mcp-server-registry.md)
- [Centralized Script Management](../../features/centralized-script-management.md)
- [ADR-019: MCP Server Registry](../../adr/ADR-019-mcp-server-registry.md)
- [Architecture: MCP Runner Integration](../../architecture/mcp-runner-integration.md)
- [Placeholder Reference](../../reference/placeholder-reference.md)
