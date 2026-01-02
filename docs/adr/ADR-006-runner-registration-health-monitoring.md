# ADR-006: Runner Registration with Health Monitoring

**Status:** Superseded
**Date:** 2025-12-12
**Decision Makers:** Architecture Review
**Superseded By:** [ADR-012: Runner Identity and Registration](./ADR-012-runner-identity-and-registration.md)

> **Supersession Notice (2025-12-18):**
> This ADR has been superseded by ADR-012, which introduces:
> - Deterministic runner ID derivation from (hostname, project_dir, executor_type)
> - Automatic reconnection recognition
> - Simplified lifecycle (online → stale → removed)
>
> The heartbeat-based health monitoring concept is retained in ADR-012.

## Context

The system needs to:
1. Track which runners are available
2. Detect runner failures
3. Coordinate graceful shutdown

## Decision

**Heartbeat-based health monitoring.**

### Protocol

1. **Registration**: `POST /runner/register` → `runner_id`
2. **Heartbeat**: `POST /runner/heartbeat` every 60s
3. **Timeout**: 120s before marking runner stale
4. **Deregistration**: Runner receives `{ "deregistered": true }` on next poll

### Storage

In-memory registry (ephemeral by design).

## Rationale

### Why Heartbeat vs Alternatives?

**Poll-based detection**: Can't distinguish "no runs" from "healthy"
**Run tracking**: Only detects failures during execution
**Heartbeat**: Explicit health signal independent of work

### Why 60s Interval?

- Network efficiency (1 request/minute)
- 120s timeout balances responsiveness vs false positives

## Consequences

### Positive
- Coordinator knows which runners are active
- Crashed runners detected within 120s
- Graceful shutdown support

### Negative
- False positives possible (>120s network issues)
- No persistence (restart = re-register)

## References

- [agent-callback-architecture.md](../features/agent-callback-architecture.md)
- [RUNS_API.md](../components/agent-coordinator/RUNS_API.md)
