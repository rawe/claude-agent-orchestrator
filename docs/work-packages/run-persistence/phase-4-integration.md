# Phase 4: Integration

**Objective:** Update `main.py` and related files to work with the refactored `RunQueue`.

## Prerequisites

- Phase 1 completed (runs table schema exists)
- Phase 2 completed (database CRUD functions exist)
- Phase 3 completed (RunQueue refactored with persistence)

## Context

The refactored `RunQueue` maintains the same public API, so most changes in `main.py` are minimal. The main updates are:

1. Ensure database is initialized before RunQueue
2. Update GET /runs to optionally include historical runs
3. Verify all existing access points work correctly

## Files to Modify

| File | Action |
|------|--------|
| `servers/agent-coordinator/main.py` | Minor updates for initialization and GET /runs |
| `servers/agent-coordinator/services/callback_processor.py` | Verify compatibility (likely no changes) |

## Implementation Steps

### Step 1: Verify Initialization Order in main.py

The `RunQueue` now loads from database on init, so ensure `init_db()` is called first.

Locate the initialization section in `main.py` and verify order:

```python
# This should already be the case, but verify:
from database import init_db

# Initialize database FIRST
init_db()

# Then create run queue (which loads from DB)
from services.run_queue import RunQueue
run_queue = RunQueue()
```

### Step 2: Update GET /runs Endpoint

The current GET /runs returns only active runs from cache. Add option to include historical runs:

**Current endpoint (around line 1266):**
```python
@app.get("/runs")
async def get_runs():
    runs = run_queue.get_all_runs()
    return {"runs": [run.model_dump() for run in runs]}
```

**Updated endpoint:**
```python
@app.get("/runs")
async def get_runs(
    include_completed: bool = False,
    status: Optional[str] = None,
):
    """
    Get runs.

    Args:
        include_completed: If True, query database for all runs including completed.
                          If False (default), return only active runs from cache.
        status: Optional status filter (e.g., "completed", "failed", "pending")
    """
    if include_completed:
        status_filter = [status] if status else None
        runs = run_queue.get_all_runs_from_db(status_filter)
    else:
        runs = run_queue.get_all_runs()
        if status:
            runs = [r for r in runs if r.status.value == status]

    return {"runs": [run.model_dump() for run in runs]}
```

### Step 3: Update GET /runs/{run_id} Endpoint

Allow fetching completed runs from database:

**Current endpoint (around line 1273):**
```python
@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = run_queue.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run.model_dump()
```

**Updated endpoint:**
```python
@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a specific run by ID. Checks cache first, then database."""
    # Try cache first (fast path for active runs)
    run = run_queue.get_run(run_id)
    if run:
        return run.model_dump()

    # Try database for completed runs
    from database import get_run_by_id as db_get_run
    run_dict = db_get_run(run_id)
    if run_dict:
        # Convert to Run model for consistent response
        run = run_queue._dict_to_run(run_dict)
        return run.model_dump()

    raise HTTPException(status_code=404, detail="Run not found")
```

**Alternative approach** - Add a public method to RunQueue:

In `run_queue.py`:
```python
def get_run_with_fallback(self, run_id: str) -> Optional[Run]:
    """Get run from cache, falling back to database for completed runs."""
    with self._lock:
        run = self._runs.get(run_id)
        if run:
            return run

    # Check database for completed runs
    run_dict = db_get_run(run_id)
    if run_dict:
        return self._dict_to_run(run_dict)

    return None
```

Then in `main.py`:
```python
@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = run_queue.get_run_with_fallback(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run.model_dump()
```

### Step 4: Verify callback_processor.py

The callback processor uses `run_queue.add_run()` which hasn't changed its signature. Verify no changes needed:

**Location:** `servers/agent-coordinator/services/callback_processor.py`

The relevant code (around line 243):
```python
# This should work unchanged:
new_run = run_queue.add_run(RunCreate(
    type=RunType.RESUME_SESSION,
    session_id=parent_session_id,
    prompt=callback_prompt,
    execution_mode=ExecutionMode.SYNC,
))
```

No changes needed if the `add_run()` signature is preserved.

### Step 5: Verify All Access Points

Go through each access point and verify compatibility:

| Location | Method | Status |
|----------|--------|--------|
| `main.py:1195` | `add_run()` | No change - signature preserved |
| `main.py:1245` | `set_run_demands()` | No change - signature preserved |
| `main.py:921` | `claim_run()` | No change - signature preserved |
| `main.py:951` | `get_run()` | No change - returns from cache |
| `main.py:956` | `update_run_status()` | No change - signature preserved |
| `main.py:981` | `update_run_status()` | No change - signature preserved |
| `main.py:1020` | `update_run_status()` | No change - signature preserved |
| `main.py:1058` | `update_run_status()` | No change - signature preserved |
| `main.py:366` | `update_run_status()` | No change - signature preserved |
| `main.py:395` | `update_run_status()` | No change - signature preserved |
| `main.py:1266` | `get_all_runs()` | Updated to support historical |
| `main.py:1273` | `get_run()` | Updated to fallback to DB |
| `main.py:243` | `get_run_by_session_id()` | No change - returns from cache |
| `main.py:446` | `get_run_by_session_id()` | No change - returns from cache |
| `main.py:106` | `fail_timed_out_runs()` | No change - signature preserved |
| `callback_processor.py:243` | `add_run()` | No change - signature preserved |

### Step 6: Update Documentation

Update `docs/agent-coordinator/DATABASE_SCHEMA.md` to include the runs table:

Add a new section after the Events Table:

```markdown
### Runs Table

Stores agent runs (work items for distribution).

\`\`\`sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    type TEXT NOT NULL,
    agent_name TEXT,
    prompt TEXT NOT NULL,
    project_dir TEXT,
    parent_session_id TEXT,
    execution_mode TEXT NOT NULL DEFAULT 'sync',
    demands TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    runner_id TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    claimed_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    timeout_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
\`\`\`

**Columns:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `run_id` | TEXT | NO | Primary key (format: `run_{12-hex}`) |
| `session_id` | TEXT | NO | Foreign key to sessions.session_id |
| `type` | TEXT | NO | `START_SESSION` or `RESUME_SESSION` |
| `agent_name` | TEXT | YES | Agent blueprint name |
| `prompt` | TEXT | NO | The prompt/task for the agent |
| ... | ... | ... | ... |

**Indexes:**
- Primary key index on `run_id`
- Index on `session_id` for session correlation
- Index on `status` for claim queries
- Composite index on `(status, created_at)` for ordered claim
```

## Testing

### Integration Test with Existing Test Framework

Use the existing test framework to verify everything works:

```bash
# Setup test environment
/tests:setup

# Run a test case
/tests:case basic-start-session

# Teardown
/tests:teardown
```

### Manual Verification Steps

1. **Start coordinator:**
   ```bash
   rm -f servers/agent-coordinator/.agent-orchestrator/observability.db
   uv run --script servers/agent-coordinator/main.py
   ```

2. **Create a run via API:**
   ```bash
   curl -X POST http://localhost:8000/runs \
     -H "Content-Type: application/json" \
     -d '{"type": "START_SESSION", "agent_name": "test", "prompt": "Hello"}'
   ```

3. **Verify run is in database:**
   ```bash
   sqlite3 servers/agent-coordinator/.agent-orchestrator/observability.db \
     "SELECT run_id, status FROM runs"
   ```

4. **Stop coordinator (Ctrl+C) and restart:**
   ```bash
   uv run --script servers/agent-coordinator/main.py
   ```

5. **Verify run survived restart:**
   ```bash
   curl http://localhost:8000/runs
   ```

6. **Test historical query:**
   ```bash
   # After completing some runs...
   curl "http://localhost:8000/runs?include_completed=true"
   ```

## Potential Issues and Solutions

### Issue: Circular Import

If importing database functions in `run_queue.py` causes circular imports:

**Solution:** Use late imports inside methods or create a separate `run_persistence.py` module.

### Issue: Database Connection in Thread Lock

The `run_queue` uses `threading.Lock`. Ensure database operations are safe:

**Solution:** SQLite connections are thread-local by default. The existing `get_connection()` pattern should handle this. If issues arise, consider using `check_same_thread=False` in the connection string.

### Issue: Run Model Mismatch

If the database dict doesn't match the Run model exactly:

**Solution:** The `_dict_to_run()` method should handle mapping with defaults for optional fields.

## Notes

- The public API of `RunQueue` is preserved - all existing code should work unchanged
- Only the GET /runs and GET /runs/{run_id} endpoints are enhanced
- Database initialization must happen before RunQueue instantiation
- SSE events continue to work - they're triggered by status updates which still happen

## Next Phase

After this phase is complete, proceed to [Phase 5: Startup Recovery](./phase-5-startup-recovery.md).
