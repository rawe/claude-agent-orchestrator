# ADR-003: Callback-Based Async for Agent Orchestration

**Status:** Accepted (Updated 2025-12-20)
**Date:** 2025-12-12
**Decision Makers:** Architecture Review

## Context

The Agent Orchestrator supports three execution modes for child agents:
1. **Sync**: Parent waits for child completion, receives result directly
2. **Async Poll**: Parent continues immediately, polls for child status/result
3. **Async Callback**: Parent continues immediately, coordinator auto-resumes parent when child completes

The first two modes have limitations: blocking or constant polling overhead.

## Decision

**Introduce callback-based async execution** where child agents notify the orchestrator upon completion.

### Execution Mode Enum

```python
class ExecutionMode(str, Enum):
    SYNC = "sync"              # Parent waits for result
    ASYNC_POLL = "async_poll"  # Parent polls for status
    ASYNC_CALLBACK = "async_callback"  # Coordinator resumes parent
```

### Key Mechanism

1. Orchestrator spawns child with `mode=async_callback`
2. Child completes, triggers `run_completed` event
3. Agent Coordinator checks `execution_mode` and parent idle status:
   - **If mode is ASYNC_CALLBACK and parent idle**: Resumes immediately with callback
   - **If mode is ASYNC_CALLBACK and parent busy**: Queues notification for later delivery
   - **If mode is SYNC or ASYNC_POLL**: No callback triggered

### Separation of Concerns

**Important**: `parent_session_id` and `execution_mode` serve different purposes:

| Field | Purpose | When Set |
|-------|---------|----------|
| `parent_session_id` | Hierarchy tracking (parent-child relationship) | ALWAYS for child sessions |
| `execution_mode` | Controls callback behavior | Always (defaults to SYNC) |

The callback is triggered based on `execution_mode == ASYNC_CALLBACK`, NOT based on `parent_session_id` presence.

### Affected Components

| Component | Responsibility |
|-----------|---------------|
| **MCP Server** | Accepts `mode` enum, always propagates parent context via `AGENT_SESSION_ID` |
| **Sessions API** | Tracks `parent_session_id` for hierarchy, `execution_mode` for behavior |
| **Callback Processor** | Monitors completion, creates resume runs when `execution_mode == ASYNC_CALLBACK` |
| **Agent Runner** | Executes resume runs |

## Rationale

### Why Callback-Based Async?

- **Resource efficiency**: Parent can fully idle without polling
- **Natural coordination**: Multiple children run in parallel
- **Scalable**: Enables fork/join parallelism, pipelines

### Why Separate execution_mode from parent_session_id?

Previously, `parent_session_id` was only set when `callback=true`, conflating two concerns:
1. Parent-child relationship tracking
2. Callback behavior control

This caused sync-spawned children to appear as orphans (no parent link).
Now `parent_session_id` is always set for hierarchy, and `execution_mode` controls callbacks.

### Constraints

Callbacks only work when parent is started by the framework (Dashboard → Run API → Runner).

## Consequences

### Positive
- Orchestrators can truly idle
- Enables sophisticated multi-agent coordination
- Clean separation: callback is infrastructure, not agent logic
- Complete hierarchy: all child sessions linked to parent
- Single enum vs two booleans: clearer intent, impossible invalid states

### Negative
- Adds complexity to session management
- Requires parent session context propagation
- Only works when framework controls parent lifecycle

## References

- [ADR-005: Parent Session Context Propagation](./ADR-005-parent-session-context-propagation.md)
- [ADR-010: Session Identity and Executor Abstraction](./ADR-010-session-identity-and-executor-abstraction.md)
