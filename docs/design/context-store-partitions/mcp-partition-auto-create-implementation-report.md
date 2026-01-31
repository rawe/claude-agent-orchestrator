# MCP Partition Auto-Create Implementation Report

**Status:** Completed
**Date:** 2026-01-31

## Summary

Implemented opt-in auto-create behavior for partitions in the MCP server. When enabled, partitions are automatically created if they don't exist. Default behavior remains strict (fail if partition doesn't exist).

## Configuration Options

### stdio Mode (Environment Variable)

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTEXT_STORE_PARTITION_AUTO_CREATE` | Set to `true` to auto-create partition if missing | `false` |

### HTTP Mode (Header)

| Header | Description | Default |
|--------|-------------|---------|
| `X-Context-Store-Partition-Auto-Create` | Set to `true` to auto-create partition if missing | `false` |

## Behavior Matrix

| Partition Set | Auto-Create | Partition Exists | Behavior |
|---------------|-------------|------------------|----------|
| No | - | - | Use global endpoints (no partition check) |
| Yes | No (default) | Yes | Use partition endpoints |
| Yes | No (default) | No | **Fail with PartitionNotFoundError** |
| Yes | Yes | Yes | Use partition endpoints |
| Yes | Yes | No | **Create partition, then use** |

## Files Changed

### Code Changes

| File | Changes |
|------|---------|
| `mcps/context-store/lib/exceptions.py` | Added `PartitionNotFoundError` exception class |
| `mcps/context-store/lib/http_client.py` | Added `ensure_partition_exists()` method |
| `mcps/context-store/lib/config.py` | Added `HEADER_CONTEXT_STORE_PARTITION_AUTO_CREATE` constant, `partition_auto_create` config property, `get_partition_auto_create_from_context()` function |
| `mcps/context-store/lib/tools.py` | Added `_ensured_partitions` tracking set and `_ensure_partition_if_needed()` function; called at start of each tool |
| `mcps/context-store/context-store-mcp.py` | Updated docstring with new `CONTEXT_STORE_PARTITION_AUTO_CREATE` env var |

### Config Updates

| File | Changes |
|------|---------|
| `config/mcp-servers/context-store/mcp-server.json` | Added `X-Context-Store-Partition-Auto-Create` to `config_schema` and `default_config` |
| `mcps/context-store/.mcp-context-store.json` | Added `CONTEXT_STORE_PARTITION_AUTO_CREATE` env var for testing |
| `mcps/context-store/.mcp-context-store-http.json` | Added `X-Context-Store-Partition-Auto-Create` header for testing |

### Documentation

| File | Changes |
|------|---------|
| `docs/design/context-store-partitions/doc-todo.md` | Added new configuration options to documentation update checklist |
| `docs/design/context-store-partitions/mcp-partition-auto-create.md` | Updated status to Implemented |

## Implementation Details

### Partition Existence Check

The implementation uses a tracking set `_ensured_partitions` to avoid repeated API calls:

1. On first tool call for a partition, check if partition exists
2. In strict mode (default): List partitions and verify existence, raise `PartitionNotFoundError` if missing
3. In auto-create mode: Call `ensure_partition_exists()` which creates the partition if it doesn't exist (handles 409 gracefully)
4. Add partition to tracking set to skip future checks

### Auto-Create Flow

```
Tool call
    |
    v
_ensure_partition_if_needed()
    |
    v
Partition in _ensured_partitions? --Yes--> Continue with tool operation
    |
    No
    v
Get auto_create setting from context
    |
    v
auto_create=true?
    |           |
   Yes         No (strict mode)
    |           |
    v           v
ensure_partition_exists()    list_partitions()
    |                            |
    v                            v
Create if needed,         Partition exists?
handle 409 gracefully          |       |
    |                        Yes      No
    v                         |        |
Add to _ensured_partitions    v        v
    |                    Continue   Raise PartitionNotFoundError
    v
Continue with tool operation
```

## Testing Recommendations

### Manual Testing

1. **Start Context Store server:**
   ```bash
   ./scripts/start-context-store.sh
   ```

2. **Test strict mode (default):**
   ```bash
   # Should fail - partition doesn't exist
   CONTEXT_STORE_PARTITION=nonexistent uv run --script mcps/context-store/context-store-mcp.py
   # Try doc_query - should error with "Partition 'nonexistent' does not exist"
   ```

3. **Test auto-create mode:**
   ```bash
   CONTEXT_STORE_PARTITION=auto-test CONTEXT_STORE_PARTITION_AUTO_CREATE=true \
     uv run --script mcps/context-store/context-store-mcp.py
   # Try doc_create - should work (partition auto-created)
   ```

4. **Verify partition was created:**
   ```bash
   curl http://localhost:8766/partitions | jq .
   # Should show "auto-test" partition
   ```

5. **Test idempotency:**
   - Run again with same partition + auto-create
   - Should succeed without error (partition already exists)

### HTTP Mode Testing

1. **Start MCP server in HTTP mode:**
   ```bash
   uv run --script mcps/context-store/context-store-mcp.py --http-mode
   ```

2. **Test with headers:**
   ```bash
   # Strict mode (should fail)
   curl -X POST http://localhost:9501/mcp/tools/doc_query \
     -H "X-Context-Store-Partition: nonexistent" \
     -H "Content-Type: application/json" \
     -d '{}'

   # Auto-create mode (should succeed)
   curl -X POST http://localhost:9501/mcp/tools/doc_create \
     -H "X-Context-Store-Partition: auto-http-test" \
     -H "X-Context-Store-Partition-Auto-Create: true" \
     -H "Content-Type: application/json" \
     -d '{"filename": "test.md"}'
   ```

## References

- Design document: `docs/design/context-store-partitions/mcp-partition-auto-create.md`
- MCP Server Partition Support: `docs/design/context-store-partitions/mcp-server-partition-support.md`
