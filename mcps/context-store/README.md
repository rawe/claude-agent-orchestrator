# Context Store MCP Server

MCP server for interacting with the Context Store document management system.

## Requirements

- [uv](https://docs.astral.sh/uv/) installed
- Context Store server running (port 8766)

## Usage

### stdio Mode (Default)

For use with Claude Code or Claude Desktop spawning the process:

```bash
uv run --script context-store-mcp.py
```

### HTTP Mode

For network-accessible server (recommended for shared/remote access):

```bash
# Default port 9501
uv run --script context-store-mcp.py --http-mode

# Custom port
uv run --script context-store-mcp.py --http-mode --port 9502

# Accessible from network
uv run --script context-store-mcp.py --http-mode --host 0.0.0.0 --port 9501
```

### Using Makefile (from project root)

```bash
# Start HTTP server (uses .env configuration)
make start-cs-mcp

# Stop server
make stop-cs-mcp
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTEXT_STORE_COMMAND_PATH` | Path to doc-* commands | Auto-discovered |
| `CONTEXT_STORE_MCP_PORT` | HTTP mode port (Makefile) | 9501 |
| `CONTEXT_STORE_MCP_HOST` | HTTP mode host (Makefile) | 127.0.0.1 |

### .env Configuration (for Makefile)

Copy `.env.template` to `.env` in the project root and configure:

```bash
# Context Store MCP Server (HTTP mode)
CONTEXT_STORE_MCP_PORT=9501
CONTEXT_STORE_MCP_HOST=127.0.0.1
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `doc_create` | Create placeholder document (returns ID, use with `doc_write`) |
| `doc_write` | Write content to existing document (full replacement) |
| `doc_push` | Upload a file with tags/metadata |
| `doc_query` | Query documents by name pattern and/or tags |
| `doc_search` | Semantic search by natural language |
| `doc_info` | Get document metadata and relations |
| `doc_read` | Read document text content (supports partial reads) |
| `doc_pull` | Download document to filesystem |
| `doc_delete` | Delete a document |
| `doc_link` | Manage document relations (parent-child, peer links) |

### Two-Phase Document Creation

For agent-generated content, use the two-phase approach:

```
doc_create(filename="doc.md", tags="design") → returns document ID
doc_write(document_id="doc_xxx", content="# Content...") → fills content
```

## Client Configuration

### Claude Desktop - stdio Mode

Add to `claude_desktop_config.json`:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "context-store": {
      "command": "uv",
      "args": ["run", "--script", "/path/to/context-store-mcp.py"]
    }
  }
}
```

### Claude Desktop - HTTP Mode

First, start the HTTP server:
```bash
make start-cs-mcp
# or
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

### Other MCP Clients

Use the provided config file:
```
.mcp-context-store-http.json
```

Or connect to: `http://localhost:9501/mcp`

## Endpoints

| Mode | Endpoint |
|------|----------|
| HTTP (Streamable) | `http://localhost:9501/mcp` |
| SSE (Legacy) | `http://localhost:9501/sse` |
