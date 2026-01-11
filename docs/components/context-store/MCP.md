# Context Store MCP Server

The MCP Server provides a [Model Context Protocol](https://modelcontextprotocol.io/) interface to the Context Store, enabling AI clients like Claude Desktop and Agent Runners to interact with documents through standardized MCP tools.

## Overview

The MCP Server acts as a bridge between MCP-compatible AI clients and the Context Store system. It wraps CLI commands as MCP tools, translating tool calls into command invocations that communicate with the Context Store Server via HTTP.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MCP Server Architecture                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│   │  Claude Desktop │     │  Agent Runner   │     │  Other MCP      │   │
│   │                 │     │                 │     │  Clients        │   │
│   └────────┬────────┘     └────────┬────────┘     └────────┬────────┘   │
│            │                       │                       │            │
│            │ MCP Protocol          │ MCP Protocol          │            │
│            ▼                       ▼                       ▼            │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                      MCP Server (FastMCP)                        │   │
│   │   ┌─────────────────────────────────────────────────────────┐   │   │
│   │   │  doc_create │ doc_write │ doc_push │ doc_query │ ...    │   │   │
│   │   │                     MCP Tools                            │   │   │
│   │   └─────────────────────────────────────────────────────────┘   │   │
│   │                              │                                    │   │
│   │                              │ Subprocess (uv run)               │   │
│   │                              ▼                                    │   │
│   │   ┌─────────────────────────────────────────────────────────┐   │   │
│   │   │  doc-create │ doc-write │ doc-push │ doc-query │ ...    │   │   │
│   │   │                    CLI Commands                          │   │   │
│   │   └─────────────────────────────────────────────────────────┘   │   │
│   └──────────────────────────────────┬──────────────────────────────┘   │
│                                      │                                   │
│                                      │ HTTP                             │
│                                      ▼                                   │
│                         ┌────────────────────────┐                       │
│                         │  Context Store Server  │                       │
│                         │       (:8766)          │                       │
│                         └────────────────────────┘                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Architecture

### Tool Wrapping Pattern

The MCP server uses [FastMCP](https://github.com/jlowin/fastmcp) to expose Python functions as MCP tools. Each tool function:

1. Receives parameters from the MCP client
2. Constructs CLI command arguments
3. Executes the corresponding `doc-*` command via subprocess
4. Returns the command output to the client

```python
@mcp.tool()
async def doc_query(name: str, tags: str, ...) -> str:
    args = []
    if name:
        args.extend(["--name", name])
    if tags:
        args.extend(["--tags", tags])

    stdout, stderr, code = await run_command("doc-query", args)
    return format_response(stdout, stderr, code)
```

### Auto-Discovery

On startup, the MCP server automatically discovers the CLI commands directory:

1. Checks `CONTEXT_STORE_COMMAND_PATH` environment variable
2. Falls back to relative path from script location: `plugins/context-store/skills/context-store/commands/`

This allows the server to work both when spawned by clients (stdio mode) and when run as a standalone service (HTTP mode).

## Operation Modes

### stdio Mode (Default)

In stdio mode, the MCP server communicates via standard input/output. The client spawns the server process and exchanges JSON-RPC messages through the process streams.

**Use case:** Claude Desktop and similar applications that manage MCP server lifecycle.

```bash
uv run --script context-store-mcp.py
```

**Lifecycle:** The client spawns a new process for each session. The server runs for the duration of the session and terminates when the client disconnects.

### HTTP Mode

In HTTP mode, the MCP server runs as a persistent HTTP service using Streamable HTTP transport. Multiple clients can connect to the same server instance.

**Use case:** Shared access across multiple agents, remote access, or when you want a long-running server.

```bash
# Default (localhost:9501)
uv run --script context-store-mcp.py --http-mode

# Network accessible
uv run --script context-store-mcp.py --http-mode --host 0.0.0.0 --port 9501
```

**Lifecycle:** The server runs until manually stopped. Clients connect to `http://host:port/mcp`.

### SSE Mode (Legacy)

Server-Sent Events transport for backward compatibility with older MCP clients.

```bash
uv run --script context-store-mcp.py --sse-mode --port 9501
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `doc_create` | Create a placeholder document with metadata. Returns document ID for later content write. |
| `doc_write` | Write content to an existing document (full replacement). |
| `doc_edit` | Surgical document editing via string replacement or offset-based operations. |
| `doc_push` | Upload a local file to the Context Store with tags and metadata. |
| `doc_query` | Query documents by filename pattern and/or tags (AND logic). |
| `doc_search` | Semantic search using natural language queries. Requires semantic search enabled. |
| `doc_info` | Get document metadata and relations without content. |
| `doc_read` | Read document content. Supports partial reads with offset/limit. |
| `doc_pull` | Download a document to the local filesystem. |
| `doc_delete` | Delete a document permanently. Cascades to children. |
| `doc_link` | Manage document relations (parent-child, peer links). |

### Two-Phase Document Creation

For AI-generated content, use the two-phase approach to reserve document IDs before content generation:

```
1. doc_create(filename="architecture.md", tags="design,mvp")
   -> Returns: {"id": "doc_abc123", ...}

2. doc_write(document_id="doc_abc123", content="# Architecture\n...")
   -> Returns: {"id": "doc_abc123", "size_bytes": 1234, ...}
```

## Client Integration

### Claude Desktop - stdio Mode

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "context-store": {
      "command": "uv",
      "args": ["run", "--script", "/path/to/mcps/context-store/context-store-mcp.py"]
    }
  }
}
```

Claude Desktop spawns the MCP server when starting a conversation and manages its lifecycle.

### Claude Desktop - HTTP Mode

First start the server:
```bash
uv run --script context-store-mcp.py --http-mode --port 9501
```

Then configure Claude Desktop:
```json
{
  "mcpServers": {
    "context-store": {
      "type": "http",
      "url": "http://localhost:9501/mcp"
    }
  }
}
```

### Agent Runners

Agent Runners connect to the MCP server via their MCP capability configuration. The connection can be either:

- **stdio:** Runner spawns the MCP server process
- **HTTP:** Runner connects to a running MCP server instance

See agent configuration documentation for MCP capability setup.

## Key Files

| File | Description |
|------|-------------|
| `mcps/context-store/context-store-mcp.py` | MCP server implementation with all tool definitions |
| `mcps/context-store/README.md` | Configuration reference and usage examples |
| `plugins/context-store/skills/context-store/commands/` | CLI commands invoked by MCP tools |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTEXT_STORE_COMMAND_PATH` | Path to CLI commands directory | Auto-discovered |
| `CONTEXT_STORE_MCP_PORT` | HTTP mode port (Makefile) | 9501 |
| `CONTEXT_STORE_MCP_HOST` | HTTP mode host (Makefile) | 127.0.0.1 |

## Related Documentation

### Architecture (this directory)
- [Context Store Overview](./README.md) - System architecture
- [Server Architecture](./SERVER.md) - REST API and storage layer
- [CLI Architecture](./CLI.md) - CLI commands and skill integration

### Detailed References (MCP README)
- [Usage Modes](../../../mcps/context-store/README.md#usage) - stdio, HTTP, and Makefile usage
- [Configuration](../../../mcps/context-store/README.md#configuration) - Environment variables and .env setup
- [MCP Tools](../../../mcps/context-store/README.md#mcp-tools) - Tool descriptions and two-phase creation
- [Client Configuration](../../../mcps/context-store/README.md#client-configuration) - Claude Desktop setup examples

### Implementation
- [CLI Commands](../../../plugins/context-store/skills/context-store/commands/) - Command implementations invoked by MCP tools
