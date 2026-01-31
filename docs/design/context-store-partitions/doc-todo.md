# Documentation Update TODO

**Status:** Pending
**Date:** 2026-01-31

## Overview

The MCP server partition support implementation added new configuration options that need to be documented in the existing documentation files.

## Files to Update

### 1. `docs/components/context-store/MCP.md`

**Section: Environment Variables** (line ~209)

Add new row to the environment variables table:

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTEXT_STORE_PARTITION` | Partition name for stdio mode | (global) |

**Section: Operation Modes > stdio Mode** (line ~77)

Add partition configuration example:

```bash
# With partition (documents isolated to my-project)
CONTEXT_STORE_PARTITION=my-project uv run --script context-store-mcp.py
```

**Section: Operation Modes > HTTP Mode** (line ~89)

Add partition header documentation:

```
Partition Routing (HTTP Mode):
  Clients specify partition via X-Context-Store-Partition header per-request.
  If header is not provided, requests use the global partition.
```

**New Section: Partition Routing** (after Operation Modes)

Add new section explaining:
- stdio mode: `CONTEXT_STORE_PARTITION` env var (set at startup, immutable for session)
- HTTP mode: `X-Context-Store-Partition` header (per-request)
- No fallback between modes
- LLM transparency (agents don't see partitions)

### 2. `mcps/context-store/README.md`

**Section: Environment Variables** (line ~49)

Add new row to the environment variables table:

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTEXT_STORE_PARTITION` | Partition name for stdio mode | (global) |

**Section: Usage > stdio Mode** (line ~12)

Add partition example:

```bash
# With partition
CONTEXT_STORE_PARTITION=my-project uv run --script context-store-mcp.py
```

**Section: Usage > HTTP Mode** (line ~21)

Add partition header note:

```
Note: In HTTP mode, partition is specified via X-Context-Store-Partition header.
```

**New Section: Partition Routing** (after Configuration)

Add section explaining partition routing for both modes.

## Approach

1. **Update environment variable tables** - Add `CONTEXT_STORE_PARTITION` to existing tables
2. **Update usage examples** - Show how to set partition in both modes
3. **Add partition routing section** - Explain the two modes and header/env var usage
4. **Keep LLM transparency** - Document that partition is an orchestration concern, not visible to agents

## Notes

- The partition is transparent to the LLM agent - it cannot see or control partitions
- HTTP mode uses header `X-Context-Store-Partition` (per-request)
- stdio mode uses env var `CONTEXT_STORE_PARTITION` (session-wide)
- No fallback between modes - HTTP mode ignores env var
- Missing partition = global partition (no special handling needed)

## References

- Implementation: `mcps/context-store/lib/config.py`
- Design: `docs/design/context-store-partitions/mcp-server-partition-support.md`
- Implementation report: `docs/design/context-store-partitions/mcp-server-partition-implementation-report.md`
