# Context Store Partitions

This folder contains design documentation for partition-based isolation in the Context Store.

## Documents

| Document | Description |
|----------|-------------|
| [context-store-partitions.md](context-store-partitions.md) | Core design for partition-based document isolation |
| [implementation-report.md](implementation-report.md) | Server and HTTP client implementation report |
| [mcp-server-partition-support.md](mcp-server-partition-support.md) | MCP server partition routing design |
| [mcp-server-partition-implementation-report.md](mcp-server-partition-implementation-report.md) | MCP server implementation report |
| [doc-todo.md](doc-todo.md) | Documentation update checklist (pending) |

## Overview

Partitions provide isolated document spaces within the Context Store. Each partition is completely isolated - documents in one partition are invisible to queries in another.

```
┌─────────────────────────────────────────────────────────────┐
│                      Context Store                          │
├─────────────────────────────────────────────────────────────┤
│  Partition: "project-alpha"     Partition: "project-beta"   │
│  ┌─────────────────────┐        ┌─────────────────────┐     │
│  │  doc_a1b2...        │        │  doc_x9y8...        │     │
│  │  doc_c3d4...        │        │  doc_z7w6...        │     │
│  └─────────────────────┘        └─────────────────────┘     │
│                                                             │
│  Complete isolation: No cross-partition access              │
└─────────────────────────────────────────────────────────────┘
```

## Key Concepts

- **Partition**: Named isolated document space
- **Global partition**: Default partition for backward compatibility (accessed via legacy endpoints)
- **Complete isolation**: No cross-partition document visibility or relations

## Implementation Layers

1. **Context Store Server**: REST API with `/partitions/{partition}/...` endpoints
2. **HTTP Client**: Partition parameter on all document/relation/search methods
3. **MCP Server**: Partition routing via environment variable (stdio) or HTTP header (HTTP mode)

The partition is transparent to the LLM agent - it's configured by the orchestrator, not selected by the agent.
