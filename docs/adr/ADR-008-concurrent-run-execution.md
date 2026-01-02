# ADR-008: Concurrent Run Execution in Agent Runner

**Status:** Accepted
**Date:** 2025-12-12
**Decision Makers:** Architecture Review
**Affected Components:** Agent Runner

## Context

Orchestration scenarios require:
1. Spawning multiple child agents in parallel
2. Multiple children completing simultaneously
3. Parent continuing while children execute

Single-run execution would defeat async patterns.

## Decision

**Multi-threaded architecture** with separate poll, execution, and supervision threads.

### Components

| Component | Responsibility |
|-----------|---------------|
| **Poll Thread** | Long-polls for runs, spawns subprocesses |
| **Running Runs Registry** | Thread-safe tracking of active runs |
| **Supervisor Thread** | Monitors completion, reports status |
| **Heartbeat Thread** | Maintains runner registration |

### Concurrency

**POC**: No hard limit (~10-20 practical based on resources)
**Future**: Configurable `max_concurrent_runs`

## Rationale

### Why Multi-Threaded?

- Non-blocking poll loop
- Parallel subprocess management
- Efficient monitoring without blocking execution

### Why Not Process Pool?

- Adds complexity (IPC, serialization)
- `subprocess.Popen` provides sufficient isolation
- Thread-safe dict simpler for POC

## Consequences

### Positive
- Enables parallel agent orchestration
- Callbacks work seamlessly
- Simple implementation using standard library

### Negative
- Requires thread-safe code
- Resource consumption scales with concurrent runs

## References

- [agent-callback-architecture.md](../features/agent-callback-architecture.md)
- [RUN_EXECUTION_FLOW.md](../components/agent-coordinator/RUN_EXECUTION_FLOW.md)
