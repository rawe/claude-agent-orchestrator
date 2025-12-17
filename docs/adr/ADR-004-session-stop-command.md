# ADR-004: Session Stop Command with Event Signaling

**Status:** Accepted
**Date:** 2025-12-12
**Decision Makers:** Architecture Review

## Context

Once a session is claimed by a launcher, there's no way to stop it. Users need to:
- Cancel long-running tasks
- Stop stuck sessions
- Free launcher capacity

The challenge: launchers use long-polling (30s timeout), creating latency for stop commands.

## Decision

**Use asyncio event signaling** to interrupt long-polls immediately.

### Architecture

- **StopCommandQueue**: Per-launcher stop command queues with `asyncio.Event`
- **New statuses**: `STOPPING` (requested), `STOPPED` (terminated)
- **Graceful shutdown**: SIGTERM (5s) → SIGKILL

### Communication Flow

```
POST /sessions/{id}/stop → StopCommandQueue.add_stop()
                         → event.set() (wake poll)
                         → Launcher receives stop_runs
                         → SIGTERM → SIGKILL
                         → POST /runs/{id}/stopped
```

## Rationale

### Why Event Signaling vs Polling?

**Polling-only**: 250ms average delay, 30s worst case
**Event-driven**: <10ms latency

### Why Not WebSockets?

Long-polling with event signaling provides similar responsiveness with simpler semantics.

## Consequences

### Positive
- Immediate stop propagation (<10ms)
- No polling overhead
- Graceful shutdown opportunity

### Negative
- New StopCommandQueue service
- Event loop coupling
- Edge cases (race conditions)

## References

- [session-stop-command.md](../features/session-stop-command.md)
