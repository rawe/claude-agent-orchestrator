# ADR-005: Parent Session Context Propagation

**Status:** Accepted (Updated 2025-12-20)
**Date:** 2025-12-12
**Decision Makers:** Architecture Review

## Context

Child agents need to know their parent's identity for:
1. **Hierarchy tracking**: Building parent-child session trees
2. **Callback delivery**: Resuming parent when child completes (if mode is ASYNC_CALLBACK)

Two execution modes need different propagation mechanisms:
1. **stdio-based**: MCP servers as subprocesses
2. **HTTP-based**: MCP servers as separate services

## Decision

**Two-mechanism approach:**

1. **Environment Variable** (`AGENT_SESSION_ID`): For stdio execution
2. **HTTP Header** (`X-Agent-Session-Id`): For HTTP MCP servers
3. **Placeholder** (`${AGENT_SESSION_ID}`): Template pattern in config

### Flow

**stdio**: Runner sets env var → subprocess inherits → MCP reads it

**HTTP**: Config has placeholder → MCP replaces → Claude sends header → child MCP extracts

### Always Propagate Parent Context

Parent session ID is **always** propagated to child sessions, regardless of execution mode:

| Execution Mode | parent_session_id | Callback Triggered |
|----------------|-------------------|-------------------|
| SYNC | Set | No |
| ASYNC_POLL | Set | No |
| ASYNC_CALLBACK | Set | Yes |

This ensures complete hierarchy tracking. The `execution_mode` field (not `parent_session_id`) determines callback behavior.

## Rationale

### Why Two Mechanisms?

- Environment variables alone insufficient for HTTP MCP servers
- HTTP headers alone insufficient for stdio MCP servers
- Transparent to agents (no explicit parameter passing)

### Why Always Propagate?

Previously, parent context was only propagated when `callback=true`. This conflated hierarchy tracking with callback behavior, causing sync-spawned children to appear as orphans.

Now parent context is always propagated for hierarchy, and `execution_mode` controls callbacks separately.

## Affected Components

| Component | Responsibility |
|-----------|---------------|
| **Agent Runner** | Sets `AGENT_SESSION_ID` env var |
| **MCP Server** | Reads env/header, always passes `parent_session_id` to coordinator |
| **MCP Servers (stdio)** | Propagates env to child subprocess |
| **MCP Servers (HTTP)** | Extracts header, sets env for subprocess |
| **Sessions API** | Stores `parent_session_id` and `execution_mode` |

## Consequences

### Positive
- Transparent to agents
- Works for both execution modes
- Declarative config
- Complete hierarchy tracking (no orphan children)

### Negative
- Two propagation paths to understand
- Magic strings require documentation

## References

- [ADR-003: Callback-Based Async](./ADR-003-callback-based-async.md)
- [ADR-010: Session Identity and Executor Abstraction](./ADR-010-session-identity-and-executor-abstraction.md)
