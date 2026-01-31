# MCP Server Partition Support - Implementation Report

**Date:** 2026-01-31
**Design Document:** `mcp-server-partition-support.md`

## Summary

Implemented partition routing in the Context Store MCP server. All tool operations now route to the configured partition transparently, without exposing partition details to the LLM agent.

## Files Changed

| File | Changes |
|------|---------|
| `mcps/context-store/lib/config.py` | Added `HEADER_CONTEXT_STORE_PARTITION` constant, `partition` config property, `get_partition_from_context()` function |
| `mcps/context-store/lib/tools.py` | Updated `register_tools()` to accept config, added `_get_partition()` helper, added `partition=` parameter to all client method calls |
| `mcps/context-store/context-store-mcp.py` | Updated docstring with partition info, updated `register_tools()` call, added partition info to startup messages |

## Implementation Details

### Config (`lib/config.py`)

Added partition support with environment variable and HTTP header handling:

```python
# HTTP Header constant
HEADER_CONTEXT_STORE_PARTITION = "X-Context-Store-Partition"

class Config:
    def __init__(self, ...):
        # Reads CONTEXT_STORE_PARTITION env var
        self.partition = partition or os.getenv("CONTEXT_STORE_PARTITION") or None

def get_partition_from_context(config: Config) -> Optional[str]:
    """Get partition from HTTP headers (HTTP mode) or config (stdio mode)."""
    try:
        from fastmcp.server.dependencies import get_http_headers
        headers = get_http_headers()
        if headers is not None:
            return headers.get(HEADER_CONTEXT_STORE_PARTITION.lower())
    except Exception:
        pass
    return config.partition
```

### Tools (`lib/tools.py`)

Updated all 11 tools to pass partition to client methods:

| Tool | Client Method | Partition Added |
|------|---------------|-----------------|
| `doc_push` | `client.push_document()` | ✓ |
| `doc_create` | `client.create_document()` | ✓ |
| `doc_write` | `client.write_document_content()` | ✓ |
| `doc_edit` | `client.edit_document_content()` | ✓ |
| `doc_query` | `client.query_documents()` | ✓ |
| `doc_search` | `client.search_documents()` | ✓ |
| `doc_info` | `client.get_document_info()` | ✓ |
| `doc_read` | `client.read_document()` | ✓ |
| `doc_pull` | `client.pull_document()` | ✓ |
| `doc_delete` | `client.delete_document()` | ✓ |
| `doc_link` | `client.get_relation_definitions()`, `client.create_relation()`, `client.update_relation()`, `client.delete_relation()` | ✓ |

Each tool uses the `_get_partition()` helper:

```python
def _get_partition() -> Optional[str]:
    """Get current partition from HTTP headers or config."""
    return get_partition_from_context(config)
```

### Main Server (`context-store-mcp.py`)

Updated startup messages to show partition configuration:

- stdio mode: Shows `Partition: {name}` or `Partition: (global)`
- HTTP mode: Shows `Partition: via X-Context-Store-Partition header`

## Configuration

### stdio Mode

```bash
# Set partition for the session
export CONTEXT_STORE_PARTITION=my-project

# Start MCP server
uv run context-store-mcp.py
```

Output:
```
Context Store MCP Server
Context Store URL: http://localhost:8766
Transport: stdio
Partition: my-project
Running via stdio
```

### HTTP Mode

```bash
# Start in HTTP mode (partition via header per-request)
uv run context-store-mcp.py --http-mode
```

Output:
```
Context Store MCP Server
Context Store URL: http://localhost:8766
Transport: streamable-http
Partition: via X-Context-Store-Partition header
Running via HTTP at http://127.0.0.1:9501/mcp
```

## Behavior

| Mode | Partition Source | Missing/Empty |
|------|------------------|---------------|
| stdio | `CONTEXT_STORE_PARTITION` env var | Uses global partition |
| HTTP | `X-Context-Store-Partition` header | Uses global partition |

**No fallback between modes.** HTTP mode ignores the environment variable.

## LLM Transparency

Tool docstrings remain unchanged - they do not mention partitions. The LLM agent cannot:
- See partition configuration
- Select or change partitions
- Query partition information

This is by design - partition selection is an orchestration concern.

## Testing Recommendations

### stdio Mode Test

```bash
# Start Context Store server
./scripts/start-context-store.sh &

# Test with partition
export CONTEXT_STORE_PARTITION=test-partition
uv run mcps/context-store/context-store-mcp.py &

# Create a document via MCP (would need MCP client)
# Verify: curl http://localhost:8766/partitions/test-partition/documents
```

### HTTP Mode Test

```bash
# Start MCP server in HTTP mode
uv run mcps/context-store/context-store-mcp.py --http-mode &

# Send MCP request with partition header
curl -X POST http://localhost:9501/mcp \
  -H "X-Context-Store-Partition: test-partition" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "doc_create", "arguments": {"filename": "test.md"}}, "id": 1}'

# Verify document in partition
curl http://localhost:8766/partitions/test-partition/documents
```

## References

- Design document: `docs/design/context-store-partitions/mcp-server-partition-support.md`
- HTTP client partition support: `mcps/context-store/lib/http_client.py`
- FastMCP dependency injection: `fastmcp.server.dependencies.get_http_headers()`
