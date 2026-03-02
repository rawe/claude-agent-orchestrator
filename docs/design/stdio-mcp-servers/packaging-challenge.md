# Packaging Challenge: Multi-File MCP Servers

**Status:** Out of Scope (for initial STDIO MCP implementation)
**Related:** [STDIO MCP Server Support](./README.md)

## Context

The Scripts feature currently supports **single-file scripts** with PEP 723 inline dependencies. This works well for simple MCP servers but presents challenges for complex, multi-module MCP servers.

## The Problem

### Simple MCP Server (Fits Single File)

A simple MCP server can be self-contained in a single Python file:

```
scripts/file-processor-mcp/
├── script.json
└── server.py          # All code in one file, deps via PEP 723
```

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.0.0"]
# ///

from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("file-processor")

@server.list_tools()
async def list_tools():
    return [{"name": "process_file", ...}]

# ... all code in one file
```

This approach works with the current script system.

### Complex MCP Server: Context Store

The **Context Store MCP** is a real-world example of a complex MCP server that doesn't fit the single-file model:

```
mcps/context-store/
├── context-store-mcp.py    # Entry point (FastMCP server setup)
├── pyproject.toml          # Dependencies
└── lib/
    ├── __init__.py
    ├── tools.py            # 12 tool definitions (~400 lines)
    ├── http_client.py      # Async HTTP client for Context Store API (~200 lines)
    └── config.py           # Configuration handling
```

**Why it's multi-file:**
- **Separation of concerns:** Tools, HTTP client, and server setup are logically separate
- **Maintainability:** 600+ lines in one file becomes unwieldy
- **Testability:** Separate modules can be unit tested independently
- **Reusability:** `http_client.py` could be used elsewhere

### The Context Store MCP Tools

For reference, the Context Store MCP provides these tools that require filesystem access:

| Tool | Purpose | Why STDIO Matters |
|------|---------|-------------------|
| `doc_push` | Upload local file to Context Store | Reads file from agent's filesystem |
| `doc_pull` | Download document to local file | Writes file to agent's filesystem |
| `doc_create` | Create document placeholder | - |
| `doc_write` | Write content to document | - |
| `doc_edit` | Edit document (replace/offset) | - |
| `doc_query` | Query by filename/tags | - |
| `doc_search` | Semantic search | - |
| `doc_read` | Read document content | - |
| `doc_info` | Get document metadata | - |
| `doc_delete` | Delete document | - |
| `doc_link` | Manage document relations | - |

The `doc_push` and `doc_pull` operations are why STDIO transport is essential - they operate on local file paths.

## Approaches

### Option A: Single-File Consolidation

Merge all modules into one file:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.0.0", "httpx>=0.27.0"]
# ///

# === HTTP Client ===
class ContextStoreClient:
    # ... 200 lines from http_client.py

# === Tools ===
async def doc_push(...):
    # ... tool implementations

# === Server Setup ===
server = Server("context-store")
# ... register all tools

if __name__ == "__main__":
    asyncio.run(stdio_server(server))
```

| Pros | Cons |
|------|------|
| Works with current script system | 600+ line file |
| No infrastructure changes | Maintenance nightmare |
| Can implement immediately | Code duplication if shared |
| | Harder to test |
| | IDE support degraded |

### Option B: Extend Scripts to Support Directories

Modify the script system to support multi-file scripts:

```json
{
  "name": "context-store-mcp",
  "description": "Context Store MCP server",
  "script_file": "server.py",
  "script_type": "directory"
}
```

```
scripts/context-store-mcp/
├── script.json
├── server.py           # Entry point
├── pyproject.toml      # Or PEP 723 in server.py
└── lib/
    ├── tools.py
    └── http_client.py
```

**Changes required:**
1. Script sync uploads entire directory (tar.gz already supports this)
2. Script metadata includes `script_type: "directory"` or similar
3. Entry point resolution remains the same (`script_file`)

| Pros | Cons |
|------|------|
| Clean code structure | Requires script system changes |
| Standard Python patterns | Sync mechanism may need adjustment |
| Maintainable | Dashboard upload complexity |
| Testable modules | |

### Option C: Package as Installable Dependency

Package the MCP server as an installable Python package:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["context-store-mcp>=1.0.0"]
# ///

from context_store_mcp import create_server
import asyncio
from mcp.server.stdio import stdio_server

if __name__ == "__main__":
    server = create_server()
    asyncio.run(stdio_server(server))
```

The script becomes a thin wrapper that imports the packaged MCP server.

| Pros | Cons |
|------|------|
| Standard Python packaging | Must publish package (PyPI or private) |
| Version management | Additional infrastructure |
| Very thin script | Dependency on external registry |
| Reusable across projects | |

### Option D: Hybrid - Local Package Reference

Use `uv`'s ability to install from local paths:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.0.0"]
# [tool.uv]
# find-links = ["${runner.scripts_dir}/context-store-mcp/dist"]
# ///
```

This requires pre-building wheels and syncing them - adds complexity.

## Recommendation

### For Initial STDIO MCP Implementation

Use **Option A (Single-File Consolidation)** for the Context Store MCP:
- Enables immediate use of STDIO MCP feature
- No script system changes required
- Accept the maintenance trade-off for now

### For Future Enhancement

Consider **Option B (Directory Support)** as a follow-up:
- Most natural fit for Python projects
- Minimal conceptual change (scripts already sync as tar.gz)
- Preserves standard project structure

## Implementation Notes for Single-File Consolidation

If consolidating Context Store MCP to a single file:

1. **Preserve logical sections** with clear comments:
   ```python
   # === Configuration ===
   # === HTTP Client ===
   # === Tool Implementations ===
   # === Server Setup ===
   ```

2. **Use PEP 723 for all dependencies:**
   ```python
   # /// script
   # dependencies = [
   #     "mcp>=1.0.0",
   #     "httpx>=0.27.0",
   #     "pydantic>=2.0.0",
   # ]
   # ///
   ```

3. **Consider code generation** for future maintenance:
   - Keep the multi-file version as source of truth
   - Generate single-file version for deployment
   - Document the generation process

## References

- [STDIO MCP Server Support](./README.md) - Main design document
- [Centralized Script Management](../../features/centralized-script-management.md) - Script system documentation
- [Context Store MCP](../../../mcps/context-store/README.md) - Current Context Store MCP implementation
