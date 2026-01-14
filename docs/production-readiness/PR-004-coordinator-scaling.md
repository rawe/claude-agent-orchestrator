# PR-004: Coordinator Horizontal Scaling

**Priority**: P2 (Medium)
**Status**: Pending
**Effort**: High

## Problem

Single coordinator instance is a single point of failure and scalability limit.

## Current State

- Single FastAPI process
- **Database-backed**: runs, sessions, events in SQLite
- **In-memory only**: SSE connections, runner registry, run queue cache (if PR-002 not implemented)
- SQLite file lock prevents multiple instances

## Why Address

1. **Availability**: Coordinator down = entire system down
2. **Scalability ceiling**: Single process limits throughput
3. **Zero-downtime deploys**: Can't restart without interruption

## Why NOT Address (Counter-argument)

- FastAPI async handles high concurrency on single instance
- Complexity of distributed state management
- Current load likely doesn't justify
- Can scale vertically first (bigger instance)

## Recommendation

**Defer until load requires it.** Single instance with PostgreSQL handles significant load. Horizontal scaling is complex and may not be needed.

## Prerequisites

- PR-001 (PostgreSQL) - Shared database required for multiple instances
- PR-002 (Run queue simplification) - Removes in-memory cache, simplifies scaling

## Architecture Changes Required

### Run Queue

After PR-002 (database-only queue):
- Runs already in shared database
- Claim operations use atomic DB updates (already implemented)
- **Only needed**: Verify claim atomicity works across instances (row-level locking)

Without PR-002:
- Each instance would have separate cache
- Cache invalidation across instances needed
- More complex - do PR-002 first

### SSE Connections

- Each instance manages own connections (in-memory, no persistence)
- Problem: Events created on instance A must reach clients on instance B
- Options:
  - Redis pub/sub for cross-instance event broadcast
  - Sticky sessions (client stays on same instance)
  - Database polling for events (simple but adds latency)

### Runner Registry

- **Currently in-memory only** (`runner_registry.py:96`)
- Registration and heartbeat stored in in-memory dictionary
- **For horizontal scaling**: Must persist runner state to shared database or Redis
- Note: Runners re-register on startup, so full persistence may not be required

## Acceptance Criteria

- [ ] Multiple coordinator instances can run concurrently
- [ ] Run claims are atomic across instances (verify with PostgreSQL)
- [ ] SSE events reach correct clients (cross-instance broadcast)
- [ ] Zero-downtime deployment possible
