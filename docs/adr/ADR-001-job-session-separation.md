# ADR-001: Job and Session Separation

**Status:** Accepted
**Date:** 2025-12-12
**Decision Makers:** Architecture Review

## Context

The Agent Orchestrator system needs to:
1. Accept requests to start/resume agent sessions via an API
2. Distribute work to Agent Launchers running on host machines
3. Track execution state and store results persistently
4. Support long-polling communication for efficient job distribution

An initial analysis questioned whether the introduction of "jobs" as a separate concept from "sessions" was over-engineered, given that each job maps 1:1 to a session.

## Decision

**Keep jobs and sessions as separate entities** with distinct data models and storage mechanisms.

### Jobs
- **Purpose:** Work distribution and execution coordination
- **Storage:** In-memory (thread-safe dictionary)
- **Lifecycle:** Ephemeral (created → claimed → running → completed/failed)
- **Identity:** `job_id` (e.g., `job_abc123def456`)

### Sessions
- **Purpose:** Persistent execution records and event logging
- **Storage:** SQLite database
- **Lifecycle:** Permanent (running → finished)
- **Identity:** `session_id` (UUID)

### Linking
- Jobs and sessions are linked via `session_name` (not by ID)
- 1:1 mapping: each job creates exactly one session
- `job_queue.get_job_by_session_name()` resolves the link

## Rationale

### Why Not Merge Into a Single Entity?

Four alternatives were analyzed:

#### Option A: Add "pending" status to Sessions
Remove jobs entirely, use sessions with status `pending | running | finished`.

**Rejected because:**
- Long-polling requires microsecond-level atomic claim operations
- SQLite queries are too slow for 500ms poll cycles
- Session model semantics would be confused (pending = no events yet)

#### Option B: Use session_id Instead of job_id
Eliminate job_id, generate session_id upfront.

**Rejected because:**
- Sessions are created WHEN the executor runs, not before
- Resume operations reuse session_name but may need different handling
- Would break the clean lifecycle: job precedes session

#### Option C: Store Jobs in SQLite
Keep job concept but persist to database.

**Rejected because:**
- SQLite is not designed as a work queue
- Atomic "claim" operation needs `threading.Lock` semantics
- Race conditions between SELECT and UPDATE without read locks
- Performance degradation for launcher polling

#### Option D: Current Design (Accepted)
Keep in-memory jobs + SQLite sessions.

**Accepted because:**
- In-memory job queue with `threading.Lock` enables fast atomic claims
- SQLite sessions provide reliable persistence for results/events
- Clean separation: jobs = work items, sessions = execution records
- Supports distributed launchers with efficient long-polling

### Data Field Analysis

| Field | Job | Session | Purpose |
|-------|-----|---------|---------|
| `session_name` | Yes | Yes | **Linking key** |
| `agent_name` | Yes | Yes | Copied for persistence |
| `project_dir` | Yes | Yes | Copied for persistence |
| `parent_session_name` | Yes | Yes | Callback support |
| `prompt` | Yes | No | Job-only (execution input) |
| `launcher_id` | Yes | No | Job-only (distribution tracking) |
| `status` | Yes | Yes | Different values/meanings |
| `error` | Yes | No | Job-only (failure tracking) |

**~40% field overlap is intentional:** Jobs carry execution context, sessions copy relevant fields for persistence.

### Performance Characteristics

```
Job Claim Operation (In-Memory):
┌─────────────────────────────────────┐
│ with self._lock:                    │  ← ~1 microsecond
│     for job in self._jobs.values(): │
│         if job.status == PENDING:   │
│             job.status = CLAIMED    │
│             return job              │
└─────────────────────────────────────┘

vs.

Session Query (SQLite):
┌─────────────────────────────────────┐
│ SELECT * FROM sessions              │  ← ~1-10 milliseconds
│ WHERE status = 'pending'            │
│ LIMIT 1                             │
│                                     │
│ UPDATE sessions SET status='claimed'│  ← Another query
│ WHERE session_id = ?                │
└─────────────────────────────────────┘
```

Long-polling with 500ms check intervals requires sub-millisecond claim operations. In-memory is 1000x faster.

## Consequences

### Positive
- Fast job distribution via long-polling
- Clean separation of concerns
- Distributed launcher support
- Sessions remain clean execution records
- Jobs can be lost on restart without data loss (sessions persist)

### Negative
- Two data models to maintain
- ~40% field duplication
- Requires `session_name` lookup to correlate job ↔ session
- Jobs lost on Agent Coordinator restart (acceptable trade-off)

### Neutral
- Developers must understand both concepts
- Documentation required to explain the separation

## Future Considerations

### Optional Enhancement: Job Persistence
For production deployments, consider backing the job queue with persistent storage while keeping the in-memory index for fast polling:

```python
class PersistentJobQueue:
    def __init__(self):
        self._jobs: dict[str, Job] = {}  # In-memory index
        self._db = SQLite("jobs.db")     # Persistence layer
```

This would survive Agent Coordinator restarts without sacrificing polling performance.

## References

- [JOBS_API.md](../agent-coordinator/JOBS_API.md) - Jobs API documentation
- [JOB_EXECUTION_FLOW.md](../agent-coordinator/JOB_EXECUTION_FLOW.md) - Execution sequence diagrams
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- Git commit `3b98e8f` - Introduction of Jobs API (2025-12-08)