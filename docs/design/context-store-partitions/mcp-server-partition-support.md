# MCP Server Partition Support

**Status:** Implemented
**Date:** 2026-01-31

## Overview

Add partition routing to the Context Store MCP server. The partition determines which document space the LLM agent operates in, but is completely invisible to the agent itself.

**Key Principle:** The LLM agent MUST NOT know about partitions. Partition selection is an orchestration concern, not an agent concern.

## Configuration

### stdio Mode

Partition is set via environment variable at MCP server startup:

```bash
# Set partition for the session
export CONTEXT_STORE_PARTITION=my-project

# Start MCP server (partition is fixed for session lifetime)
uv run context-store-mcp.py
```

| Variable | Description |
|----------|-------------|
| `CONTEXT_STORE_PARTITION` | Partition name for all operations. If not set or empty, uses global partition endpoints. |

The partition is read once at startup and applies to all tool calls for the session lifetime.

### HTTP Mode

Partition is set via HTTP header on each MCP request:

```http
POST /mcp HTTP/1.1
Host: localhost:9501
X-Context-Store-Partition: my-project
Content-Type: application/json

{"method": "tools/call", "params": {...}}
```

| Header | Description |
|--------|-------------|
| `X-Context-Store-Partition` | Partition name for this request. If not present, uses global partition endpoints. |

Each request can specify a different partition (though typically all requests from a session use the same partition).

## Behavior

### Partition Resolution

| Mode | Source | Missing/Empty |
|------|--------|---------------|
| stdio | `CONTEXT_STORE_PARTITION` env var | Uses global partition endpoints |
| HTTP | `X-Context-Store-Partition` header | Uses global partition endpoints |

**No fallback between modes.** In HTTP mode, the env var is ignored. This prevents confusion about which partition is active.

### Global Partition Handling

When partition is not specified:
- The MCP server passes `partition=None` to the HTTP client
- The HTTP client routes to global endpoints (`/documents/...` instead of `/partitions/{p}/documents/...`)
- The MCP server does NOT know about the internal `_global` partition name

This maintains separation of concerns:
- Context Store server: Knows about `_global` partition
- HTTP client: Routes based on `partition` parameter (None = global endpoints)
- MCP server: Just passes through partition from config, no knowledge of internal naming

## Architecture

### stdio Mode Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                     Orchestrator                                  │
│  Sets: CONTEXT_STORE_PARTITION=my-project                        │
│  Spawns: MCP Server process                                       │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     MCP Server (stdio)                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Config                                                      │  │
│  │   partition = os.getenv("CONTEXT_STORE_PARTITION")         │  │
│  │   # Read once at startup, immutable                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Tool Handler (e.g., doc_create)                             │  │
│  │   # LLM calls: doc_create(filename="notes.md")              │  │
│  │   # Handler adds partition from config                      │  │
│  │   result = client.create_document(                          │  │
│  │       filename="notes.md",                                  │  │
│  │       partition=config.partition  # "my-project"            │  │
│  │   )                                                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ HTTP Client                                                 │  │
│  │   POST /partitions/my-project/documents                     │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Context Store Server                            │
│  Creates document in "my-project" partition                       │
└──────────────────────────────────────────────────────────────────┘
```

### HTTP Mode Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                     MCP Client                                    │
│  Sends request with header:                                       │
│  X-Context-Store-Partition: my-project                           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   MCP Server (HTTP mode)                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Request Handler                                             │  │
│  │   partition = request.headers.get("X-Context-Store-Partition")│
│  │   # Extracted per-request                                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Tool Handler (e.g., doc_create)                             │  │
│  │   # Receives partition from request context                 │  │
│  │   result = client.create_document(                          │  │
│  │       filename="notes.md",                                  │  │
│  │       partition=partition  # "my-project" from header       │  │
│  │   )                                                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ HTTP Client                                                 │  │
│  │   POST /partitions/my-project/documents                     │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Context Store Server                            │
│  Creates document in "my-project" partition                       │
└──────────────────────────────────────────────────────────────────┘
```

## Implementation

### Files to Modify

| File | Changes |
|------|---------|
| `mcps/context-store/lib/config.py` | Add `partition` property from `CONTEXT_STORE_PARTITION` env var |
| `mcps/context-store/lib/tools.py` | Pass `partition` to all client method calls |
| `mcps/context-store/context-store-mcp.py` | HTTP mode: extract partition header, pass to tool context |

### Config Changes

```python
# lib/config.py

class Config:
    """Configuration for Context Store client."""

    # ... existing code ...

    def __init__(self, ...):
        # ... existing code ...
        self.partition = os.getenv("CONTEXT_STORE_PARTITION") or None
```

### Tool Changes

Tools must pass partition to client methods. The partition comes from:
- stdio mode: `config.partition` (set at startup)
- HTTP mode: request context (per-request)

```python
# lib/tools.py (conceptual - actual implementation depends on FastMCP context handling)

@mcp.tool()
async def doc_create(
    filename: str,
    tags: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """Create a placeholder document in the Context Store.
    ...
    """  # Note: NO mention of partition in docstring
    try:
        tags_list = [t.strip() for t in tags.split(",")] if tags else None
        result = await client.create_document(
            filename=filename,
            tags=tags_list,
            description=description,
            partition=get_current_partition(),  # From config or request context
        )
        return json.dumps(result)
    except ContextStoreError as e:
        return f"Error: {e}"
```

### HTTP Mode Context

FastMCP may provide request context access. The implementation needs to:
1. Extract `X-Context-Store-Partition` header from incoming request
2. Make it available to tool handlers

This may require FastMCP middleware or request hooks. Research FastMCP documentation for per-request context handling.

## LLM Transparency

**Critical:** Tool docstrings MUST NOT mention partitions.

The LLM sees tool descriptions via FastMCP. If partition is mentioned, the LLM might:
- Try to specify a partition (which it can't)
- Ask about partitions (confusing)
- Make assumptions about document visibility

Current docstrings are correct - they describe document operations without partition details.

## Testing

### stdio Mode

```bash
# Test with partition
export CONTEXT_STORE_PARTITION=test-partition
uv run context-store-mcp.py &

# Create document (should go to test-partition)
# Verify via Context Store API:
curl http://localhost:8766/partitions/test-partition/documents

# Test without partition (global)
unset CONTEXT_STORE_PARTITION
uv run context-store-mcp.py &
# Documents should go to global partition
```

### HTTP Mode

```bash
# Start HTTP mode
uv run context-store-mcp.py --http-mode &

# Request with partition header
curl -X POST http://localhost:9501/mcp \
  -H "X-Context-Store-Partition: test-partition" \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "doc_create", "arguments": {"filename": "test.md"}}}'

# Request without header (global partition)
curl -X POST http://localhost:9501/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "doc_create", "arguments": {"filename": "test.md"}}}'
```

## References

- [Context Store Partitions Design](context-store-partitions.md)
- [Implementation Report](implementation-report.md)
- [FastMCP Documentation](https://gofastmcp.com/)
