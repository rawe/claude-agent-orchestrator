# MCP Partition Auto-Create

**Status:** Implemented
**Date:** 2026-01-31

## Problem

When an MCP server is configured with a partition (e.g., `X-Context-Store-Partition: project-alpha`), the partition might not exist in the Context Store. Without the partition existing, all document operations fail with 404.

Two use cases require different behavior:

| Use Case | Desired Behavior |
|----------|------------------|
| Production / Controlled | Fail if partition doesn't exist (typo protection) |
| Development / Dynamic | Create partition automatically if missing |

## Solution

Add opt-in auto-create behavior via a second configuration option.

### Configuration

| Mode | Setting | Value |
|------|---------|-------|
| stdio | Environment variable | `CONTEXT_STORE_PARTITION_AUTO_CREATE=true` |
| HTTP | HTTP header | `X-Context-Store-Partition-Auto-Create: true` |

**Default behavior:** Strict mode (no auto-create). Operations fail if partition doesn't exist.

### Behavior Matrix

| Partition Set | Auto-Create | Partition Exists | Behavior |
|---------------|-------------|------------------|----------|
| No | - | - | Use global endpoints (no partition check) |
| Yes | No (default) | Yes | Use partition endpoints |
| Yes | No (default) | No | **Fail on first operation** |
| Yes | Yes | Yes | Use partition endpoints |
| Yes | Yes | No | **Create partition, then use** |

## Implementation

### HTTP Client Changes

Add method to check/create partition:

```python
# lib/http_client.py

async def ensure_partition_exists(self, partition: str) -> bool:
    """Ensure partition exists, creating it if auto-create is enabled.

    Uses create with 409 handling (more efficient than check-then-create).

    Returns:
        True if partition exists or was created

    Raises:
        PartitionNotFoundError: If partition doesn't exist and auto-create disabled
    """
    try:
        await self.create_partition(partition)
        return True  # Created
    except ContextStoreError as e:
        if "already exists" in str(e):
            return True  # Already existed
        raise
```

### Config Changes

```python
# lib/config.py

HEADER_CONTEXT_STORE_PARTITION_AUTO_CREATE = "X-Context-Store-Partition-Auto-Create"

class Config:
    def __init__(self, ...):
        # ...existing...
        self.partition_auto_create = (
            os.getenv("CONTEXT_STORE_PARTITION_AUTO_CREATE", "").lower() == "true"
        )

def get_partition_auto_create_from_context(config: Config) -> bool:
    """Get auto-create setting from HTTP headers or config."""
    try:
        from fastmcp.server.dependencies import get_http_headers
        headers = get_http_headers()
        if headers is not None:
            value = headers.get(HEADER_CONTEXT_STORE_PARTITION_AUTO_CREATE.lower(), "")
            return value.lower() == "true"
    except Exception:
        pass
    return config.partition_auto_create
```

### Tools Changes

Ensure partition exists on first tool call per session:

```python
# lib/tools.py

# Track ensured partitions (per-process for stdio, would need per-request for HTTP)
_ensured_partitions: set[str] = set()

async def _ensure_partition_if_needed(partition: str | None, auto_create: bool) -> None:
    """Ensure partition exists if configured and not already checked."""
    if partition is None:
        return  # Global partition, no check needed

    if partition in _ensured_partitions:
        return  # Already ensured this session

    if auto_create:
        await client.ensure_partition_exists(partition)
        _ensured_partitions.add(partition)
    else:
        # Strict mode: verify partition exists
        partitions = await client.list_partitions()
        if not any(p["name"] == partition for p in partitions):
            raise ContextStoreError(f"Partition '{partition}' does not exist")
        _ensured_partitions.add(partition)
```

### Initialization Strategy

**stdio mode:** Check/create once at startup or on first tool call.

**HTTP mode:** Check/create on first tool call per partition per request (since partition can vary per request via header).

## MCP Server Registry Config

Update `config/mcp-servers/context-store/mcp-server.json`:

```json
{
  "id": "context-store",
  "name": "Context Store",
  "description": "Stores and retrieves agent context data",
  "url": "http://localhost:9501/mcp",
  "config_schema": {
    "X-Context-Store-Partition": {
      "type": "string",
      "description": "Partition name for document isolation",
      "required": false,
      "sensitive": false
    },
    "X-Context-Store-Partition-Auto-Create": {
      "type": "string",
      "description": "Set to 'true' to auto-create partition if it doesn't exist",
      "required": false,
      "sensitive": false
    }
  },
  "default_config": {
    "X-Context-Store-Partition": "${scope.partition}",
    "X-Context-Store-Partition-Auto-Create": "${scope.partition_auto_create}"
  }
}
```

## Test Config Updates

### stdio mode (`.mcp-context-store.json`)

```json
{
  "mcpServers": {
    "context-store": {
      "command": "uv",
      "args": ["run", "--script", "..."],
      "env": {
        "CONTEXT_STORE_PARTITION": "test-partition",
        "CONTEXT_STORE_PARTITION_AUTO_CREATE": "true"
      }
    }
  }
}
```

### HTTP mode (`.mcp-context-store-http.json`)

```json
{
  "mcpServers": {
    "context-store-http": {
      "type": "http",
      "url": "http://localhost:9501/mcp",
      "headers": {
        "X-Context-Store-Partition": "test-partition",
        "X-Context-Store-Partition-Auto-Create": "true"
      }
    }
  }
}
```

## Implementation TODO

1. **HTTP Client**
   - [x] Add `ensure_partition_exists()` method
   - [x] Add `partition_exists()` method (optional, for strict check)

2. **Config**
   - [x] Add `CONTEXT_STORE_PARTITION_AUTO_CREATE` env var support
   - [x] Add `HEADER_CONTEXT_STORE_PARTITION_AUTO_CREATE` constant
   - [x] Add `get_partition_auto_create_from_context()` function

3. **Tools**
   - [x] Add partition existence check/create logic
   - [x] Track ensured partitions to avoid repeated checks
   - [x] Handle strict mode (fail if partition doesn't exist)

4. **MCP Server Registry**
   - [x] Update `config/mcp-servers/context-store/mcp-server.json` with new config field

5. **Test Configs**
   - [x] Update `.mcp-context-store.json` with auto-create env var
   - [x] Update `.mcp-context-store-http.json` with auto-create header

6. **Documentation**
   - [x] Update `doc-todo.md` with new configuration option

See [Implementation Report](mcp-partition-auto-create-implementation-report.md) for details.

## References

- [MCP Server Partition Support](mcp-server-partition-support.md)
- [MCP Server Partition Implementation Report](mcp-server-partition-implementation-report.md)
