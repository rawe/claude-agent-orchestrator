# External Service Authentication and Scoping

**Status:** Draft
**Date:** 2026-01-12

## Problem

When agents interact with external services (Context Store, Knowledge Graph, etc.), we need to solve two problems:

1. **Data Scoping** - Partition data by namespace and scope filters so agents only see documents relevant to their project/workflow
2. **Access Control** - Ensure only authorized requests (from valid runs via the Coordinator) can access these services

## Solution

The Coordinator issues signed JWT tokens that carry both authorization and scope information. External services validate these tokens and extract the scope to filter data access.

```
┌──────────────────┐     ┌──────────────┐     ┌──────────────────┐
│ Agent Coordinator│────►│  MCP Server  │────►│ External Service │
│  (issues token)  │     │(passes token)│     │(validates token, │
│                  │     │              │     │ extracts scope)  │
└──────────────────┘     └──────────────┘     └──────────────────┘
        │                                              │
        │  Token contains:                             │
        │  - namespace: "project-alpha"                │
        │  - scope_filters: {root_session_id: "..."}   │
        │  - signature (RS256)                         │
        └──────────────────────────────────────────────┘
```

**Key properties:**
- Coordinator signs tokens with private key, services validate with public key
- LLM cannot manipulate scope - it's embedded in the token, not in tool parameters
- Pattern is generic - works for Context Store, Knowledge Graph, or any future service
- Independent of user authentication (Auth0) - this is server-to-server trust

## Documents

Read in this order:

| # | Document | Purpose |
|---|----------|---------|
| 1 | [External Service Token Architecture](./external-service-token-architecture-with-scoping.md) | **Start here.** Foundational pattern for token-based access and scoping. Generic design applicable to any external service. |
| 2 | [Context Store Token-Based Scoping](./context-store-token-based-scoping.md) | Context Store specific implementation details. How tokens flow through MCP Server and CLI to the Context Store Server. |
| 3 | [Context Store Integration Flow](./context-store-integration-flow.md) | Sequence diagram visualizing the complete flow from run creation to document storage. Useful for understanding component interactions. |

## Related

- [Context Store Scoping](../context-store-scoping/context-store-scoping.md) - Alternative approach using explicit API parameters without token auth. Can be implemented independently.
