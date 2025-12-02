# Context Store MCP Server

MCP server for interacting with the Context Store document management system.

## Requirements

- [uv](https://docs.astral.sh/uv/) installed
- Context Store server running (port 8766)

## Usage

```bash
uv run context-store-mcp.py
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `CONTEXT_STORE_COMMAND_PATH` | Path to doc-* commands | Auto-discovered |

## MCP Tools

| Tool | Description |
|------|-------------|
| `doc_push` | Upload a document with tags/metadata |
| `doc_query` | Query documents by name pattern and/or tags |
| `doc_search` | Semantic search by natural language |
| `doc_info` | Get document metadata |
| `doc_read` | Read document text content |
| `doc_pull` | Download document to filesystem |
| `doc_delete` | Delete a document |

## Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "context-store": {
      "command": "uv",
      "args": ["run", "/path/to/context-store-mcp.py"]
    }
  }
}
```
