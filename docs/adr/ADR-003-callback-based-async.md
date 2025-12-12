# ADR-003: Callback-Based Async for Agent Orchestration

**Status:** Accepted
**Date:** 2025-12-12
**Decision Makers:** Architecture Review

## Context

The Agent Orchestrator supports two execution patterns:
1. **Synchronous**: Parent waits for child completion
2. **Async with polling**: Parent polls for results

Both have limitations: blocking or constant polling overhead.

## Decision

**Introduce callback-based async execution** where child agents notify the orchestrator upon completion.

### Key Mechanism

1. Orchestrator spawns child with `callback=true`
2. Child completes, triggers `session_stop` event
3. Agent Runtime checks parent idle status:
   - **If idle**: Resumes immediately with callback
   - **If busy**: Queues notification for later delivery

### Affected Components

| Component | Responsibility |
|-----------|---------------|
| **MCP Server** | Propagates `AGENT_SESSION_NAME` when `callback=true` |
| **Sessions API** | Tracks `parent_session_name` for parent-child relationships |
| **Callback Processor** | Monitors completion, creates resume jobs |
| **Agent Launcher** | Executes resume jobs |

## Rationale

### Why Callback-Based Async?

- **Resource efficiency**: Parent can fully idle without polling
- **Natural coordination**: Multiple children run in parallel
- **Scalable**: Enables fork/join parallelism, pipelines

### Constraints

Callbacks only work when parent is started by the framework (Dashboard → Job API → Launcher).

## Consequences

### Positive
- Orchestrators can truly idle
- Enables sophisticated multi-agent coordination
- Clean separation: callback is infrastructure, not agent logic

### Negative
- Adds complexity to session management
- Requires parent session context propagation
- Only works when framework controls parent lifecycle

## References

- [agent-callback-architecture.md](../features/agent-callback-architecture.md)
