# Work Package: Run Persistence to SQLite

**Status:** Planned
**Created:** 2025-12-29
**Supersedes:** ADR-001 Option D (in-memory only runs)

## Overview

Migrate agent runs from in-memory storage to SQLite database persistence while maintaining fast polling performance through a write-through cache strategy.

### Current State

- **Runs**: Stored in-memory only (`RunQueue._runs` dict with `threading.Lock`)
- **Sessions**: Already persisted in SQLite (`sessions` and `events` tables)
- **Problem**: Runs are lost on coordinator restart, no historical run data

### Target State

- **Runs**: Persisted in SQLite with foreign key to sessions
- **Cache**: In-memory cache for fast polling (write-through strategy)
- **Benefit**: Runs survive restarts, historical queries, session-run correlation

## Architecture Decision

We chose **Write-Through Cache** over pure database access:

```
┌─────────────────────────────────────────────────────────┐
│                      RunQueue                            │
├─────────────────────────────────────────────────────────┤
│  _runs: dict[str, Run]  ←── Fast reads (polling)        │
│  _lock: threading.Lock  ←── Thread safety               │
│                                                         │
│  All writes: DB first → then cache                      │
│  Startup: Load active runs from DB → populate cache     │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    SQLite Database                       │
├─────────────────────────────────────────────────────────┤
│  runs table (persistent)                                │
│  - run_id, session_id (FK), status, demands, etc.      │
└─────────────────────────────────────────────────────────┘
```

**Why not pure database?**
- Runner polling requires sub-millisecond atomic claim operations
- SQLite queries are 1000x slower than in-memory dict access
- See ADR-001 for detailed performance analysis

## Implementation Phases

| Phase | Document | Description |
|-------|----------|-------------|
| 1 | [phase-1-database-schema.md](./phase-1-database-schema.md) | Add `runs` table to database schema |
| 2 | [phase-2-database-functions.md](./phase-2-database-functions.md) | CRUD functions in `database.py` |
| 3 | [phase-3-run-queue-refactor.md](./phase-3-run-queue-refactor.md) | Refactor `RunQueue` to use DB + cache |
| 4 | [phase-4-integration.md](./phase-4-integration.md) | Update all access points in `main.py` |
| 5 | [phase-5-startup-recovery.md](./phase-5-startup-recovery.md) | Handle restart recovery and cleanup |

## Files Affected

### Primary Changes

| File | Change |
|------|--------|
| `servers/agent-coordinator/database.py` | Add runs table schema + CRUD functions |
| `servers/agent-coordinator/services/run_queue.py` | Refactor to write-through cache |
| `servers/agent-coordinator/main.py` | Update initialization + minor API tweaks |

### Secondary Changes

| File | Change |
|------|--------|
| `servers/agent-coordinator/services/callback_processor.py` | Uses `run_queue.add_run()` - no changes needed |
| `docs/agent-coordinator/DATABASE_SCHEMA.md` | Document new `runs` table |
| `docs/adr/ADR-001-run-session-separation.md` | Update to reflect persistence |

## Current Run Access Points

All locations in code where runs are accessed (must work with new implementation):

### Create Operations
| Location | Method | Context |
|----------|--------|---------|
| `main.py:1195` | `add_run()` | POST /runs endpoint |
| `callback_processor.py:243` | `add_run()` | Create resume run for parent |

### Read Operations
| Location | Method | Context |
|----------|--------|---------|
| `main.py:921` | `claim_run()` | Runner polls for work |
| `main.py:951` | `get_run()` | Report started - lookup |
| `main.py:1266` | `get_all_runs()` | GET /runs endpoint |
| `main.py:1273` | `get_run()` | GET /runs/{run_id} endpoint |
| `main.py:243` | `get_run_by_session_id()` | Link run to session parent |
| `main.py:446` | `get_run_by_session_id()` | Find run to stop |

### Update Operations
| Location | Method | Context |
|----------|--------|---------|
| `main.py:1245` | `set_run_demands()` | Set demands after creation |
| `main.py:956` | `update_run_status(RUNNING)` | Report started |
| `main.py:981` | `update_run_status(COMPLETED)` | Report completion |
| `main.py:1020` | `update_run_status(FAILED)` | Report failure |
| `main.py:1058` | `update_run_status(STOPPED)` | Report stopped |
| `main.py:366` | `update_run_status(STOPPED)` | Cancel pending run |
| `main.py:395` | `update_run_status(STOPPING)` | Mark as stopping |
| `main.py:106` | `fail_timed_out_runs()` | Background timeout task |

## Database Schema Preview

```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    type TEXT NOT NULL,                    -- START_SESSION, RESUME_SESSION
    agent_name TEXT,
    prompt TEXT NOT NULL,
    project_dir TEXT,
    parent_session_id TEXT,
    execution_mode TEXT NOT NULL,          -- sync, async_poll, async_callback
    demands TEXT,                          -- JSON blob
    status TEXT NOT NULL,                  -- pending, claimed, running, etc.
    runner_id TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    claimed_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    timeout_at TEXT
);

CREATE INDEX idx_runs_session_id ON runs(session_id);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_runner_id ON runs(runner_id);
```

## Migration Strategy

**No migration required.**

The database will be dropped and recreated fresh. This is acceptable because:
1. Runs are currently in-memory only (already lost on restart)
2. Sessions/events can be recreated from new runs
3. Development phase - no production data to preserve

## Testing Strategy

Each phase includes specific test cases:

1. **Phase 1**: Verify schema creation via `init_db()`
2. **Phase 2**: Unit tests for database CRUD functions
3. **Phase 3**: Unit tests for `RunQueue` with persistence
4. **Phase 4**: Integration tests via existing `/tests` framework
5. **Phase 5**: Startup recovery tests (simulate restart scenarios)

## Success Criteria

- [ ] Runs survive coordinator restart
- [ ] Polling performance remains sub-millisecond
- [ ] All existing integration tests pass
- [ ] Historical runs queryable via GET /runs
- [ ] Session-run relationship queryable
