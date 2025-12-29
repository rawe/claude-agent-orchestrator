# Phase 3: RunQueue Refactor

**Objective:** Refactor `RunQueue` to use write-through caching with SQLite persistence.

## Prerequisites

- Phase 1 completed (runs table schema exists)
- Phase 2 completed (database CRUD functions exist)

## Context

The current `RunQueue` stores runs only in memory. We'll refactor it to:

1. Write all changes to the database first
2. Update the in-memory cache after successful DB write
3. Load active runs from DB on startup

This maintains fast polling while ensuring persistence.

## Files to Modify

| File | Action |
|------|--------|
| `servers/agent-coordinator/services/run_queue.py` | Major refactor |

## Current Implementation Analysis

The current `RunQueue` class (simplified):

```python
class RunQueue:
    def __init__(self):
        self._runs: dict[str, Run] = {}  # In-memory only
        self._lock = threading.Lock()

    def add_run(self, run_create: RunCreate) -> Run:
        # Generate IDs, create Run, store in _runs
        pass

    def claim_run(self, runner: RunnerInfo) -> Optional[Run]:
        # Find first pending run matching demands, update status
        pass

    def update_run_status(self, run_id: str, status: RunStatus, error: str = None) -> Optional[Run]:
        # Update run status in _runs
        pass
    # ... other methods
```

## Implementation Steps

### Step 1: Add Database Imports

At the top of `run_queue.py`, add imports for the database functions:

```python
import json
from database import (
    create_run as db_create_run,
    get_run_by_id as db_get_run,
    get_run_by_session_id as db_get_run_by_session,
    get_all_runs as db_get_all_runs,
    get_active_runs as db_get_active_runs,
    update_run_status as db_update_run_status,
    claim_run as db_claim_run,
    update_run_demands as db_update_run_demands,
    fail_timed_out_runs as db_fail_timed_out_runs,
)
```

### Step 2: Add Cache Loading on Init

Modify the `__init__` method to load active runs from the database:

```python
class RunQueue:
    def __init__(self):
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()
        self._load_active_runs()

    def _load_active_runs(self) -> None:
        """Load non-terminal runs from database into cache on startup."""
        active_runs = db_get_active_runs()
        for run_dict in active_runs:
            run = self._dict_to_run(run_dict)
            self._runs[run.run_id] = run

    def _dict_to_run(self, d: dict) -> Run:
        """Convert database dict to Run model."""
        return Run(
            run_id=d["run_id"],
            session_id=d["session_id"],
            type=RunType(d["type"]),
            agent_name=d.get("agent_name"),
            prompt=d["prompt"],
            project_dir=d.get("project_dir"),
            parent_session_id=d.get("parent_session_id"),
            execution_mode=ExecutionMode(d.get("execution_mode", "sync")),
            demands=json.loads(d["demands"]) if d.get("demands") else None,
            status=RunStatus(d["status"]),
            runner_id=d.get("runner_id"),
            error=d.get("error"),
            created_at=d["created_at"],
            claimed_at=d.get("claimed_at"),
            started_at=d.get("started_at"),
            completed_at=d.get("completed_at"),
            timeout_at=d.get("timeout_at"),
        )
```

### Step 3: Refactor add_run()

Write to database first, then update cache:

```python
def add_run(self, run_create: RunCreate) -> Run:
    """Create a new run. Persists to database, then updates cache."""
    with self._lock:
        # Generate IDs
        run_id = f"run_{secrets.token_hex(6)}"
        session_id = run_create.session_id or f"ses_{secrets.token_hex(6)}"
        created_at = datetime.utcnow().isoformat() + "Z"

        # For RESUME_SESSION, enrich from existing session
        agent_name = run_create.agent_name
        project_dir = run_create.project_dir
        if run_create.type == RunType.RESUME_SESSION and session_id:
            existing_session = get_session_by_id(session_id)
            if existing_session:
                agent_name = agent_name or existing_session.get("agent_name")
                project_dir = project_dir or existing_session.get("project_dir")

        # Write to database first
        db_create_run(
            run_id=run_id,
            session_id=session_id,
            run_type=run_create.type.value,
            prompt=run_create.prompt,
            created_at=created_at,
            agent_name=agent_name,
            project_dir=project_dir,
            parent_session_id=run_create.parent_session_id,
            execution_mode=run_create.execution_mode.value,
            status=RunStatus.PENDING.value,
        )

        # Create Run model for cache
        run = Run(
            run_id=run_id,
            session_id=session_id,
            type=run_create.type,
            agent_name=agent_name,
            prompt=run_create.prompt,
            project_dir=project_dir,
            parent_session_id=run_create.parent_session_id,
            execution_mode=run_create.execution_mode,
            status=RunStatus.PENDING,
            created_at=created_at,
        )

        # Update cache
        self._runs[run_id] = run
        return run
```

### Step 4: Refactor claim_run()

Use database for atomic claim, then update cache:

```python
def claim_run(self, runner: RunnerInfo) -> Optional[Run]:
    """
    Claim the first pending run matching runner's capabilities.
    Uses database for atomic claim to prevent race conditions.
    """
    with self._lock:
        claimed_at = datetime.utcnow().isoformat() + "Z"

        # Find first pending run in cache that matches demands
        for run in self._runs.values():
            if run.status != RunStatus.PENDING:
                continue
            if not capabilities_satisfy_demands(runner, run.demands):
                continue

            # Try to claim in database (atomic)
            if db_claim_run(run.run_id, runner.runner_id, claimed_at):
                # Success - update cache
                run.status = RunStatus.CLAIMED
                run.runner_id = runner.runner_id
                run.claimed_at = claimed_at
                return run
            else:
                # Someone else claimed it - remove from cache (stale)
                # This shouldn't happen with single coordinator, but be safe
                del self._runs[run.run_id]

        return None
```

### Step 5: Refactor update_run_status()

Write to database first, then update cache:

```python
def update_run_status(
    self,
    run_id: str,
    status: RunStatus,
    error: Optional[str] = None,
) -> Optional[Run]:
    """Update run status. Persists to database, then updates cache."""
    with self._lock:
        run = self._runs.get(run_id)
        if not run:
            return None

        # Determine timestamps based on status transition
        started_at = None
        completed_at = None
        now = datetime.utcnow().isoformat() + "Z"

        if status == RunStatus.RUNNING:
            started_at = now
        elif status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.STOPPED):
            completed_at = now

        # Write to database first
        success = db_update_run_status(
            run_id=run_id,
            status=status.value,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
        )

        if not success:
            return None

        # Update cache
        run.status = status
        if error:
            run.error = error
        if started_at:
            run.started_at = started_at
        if completed_at:
            run.completed_at = completed_at

        # Remove from cache if terminal (keep memory clean)
        if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.STOPPED):
            del self._runs[run_id]

        return run
```

### Step 6: Refactor set_run_demands()

```python
def set_run_demands(
    self,
    run_id: str,
    demands: Optional[dict],
    timeout_seconds: int = 300,
) -> Optional[Run]:
    """Set run demands and timeout. Persists to database, then updates cache."""
    with self._lock:
        run = self._runs.get(run_id)
        if not run:
            return None

        # Calculate timeout
        timeout_at = None
        if demands:
            timeout_at = (
                datetime.utcnow() + timedelta(seconds=timeout_seconds)
            ).isoformat() + "Z"

        # Write to database first
        demands_json = json.dumps(demands) if demands else None
        success = db_update_run_demands(run_id, demands_json, timeout_at)

        if not success:
            return None

        # Update cache
        run.demands = demands
        run.timeout_at = timeout_at

        return run
```

### Step 7: Refactor fail_timed_out_runs()

```python
def fail_timed_out_runs(self) -> list[Run]:
    """Check for and fail any pending runs past their timeout."""
    with self._lock:
        current_time = datetime.utcnow().isoformat() + "Z"

        # Use database to find and fail timed out runs
        failed_run_ids = db_fail_timed_out_runs(current_time)

        # Update cache for failed runs
        failed_runs = []
        for run_id in failed_run_ids:
            run = self._runs.get(run_id)
            if run:
                run.status = RunStatus.FAILED
                run.error = "No matching runner available within timeout"
                run.completed_at = current_time
                failed_runs.append(run)
                # Remove from cache (terminal state)
                del self._runs[run_id]

        return failed_runs
```

### Step 8: Keep Read Methods Simple (Cache-First)

These methods just read from cache - fast path for polling:

```python
def get_run(self, run_id: str) -> Optional[Run]:
    """Get a run by ID. Reads from cache for speed."""
    with self._lock:
        return self._runs.get(run_id)

def get_pending_runs(self) -> list[Run]:
    """Get all pending runs. Reads from cache."""
    with self._lock:
        return [r for r in self._runs.values() if r.status == RunStatus.PENDING]

def get_all_runs(self) -> list[Run]:
    """Get all runs in cache (active runs only)."""
    with self._lock:
        return list(self._runs.values())

def get_run_by_session_id(self, session_id: str) -> Optional[Run]:
    """Find active run by session ID. Reads from cache."""
    with self._lock:
        for run in self._runs.values():
            if run.session_id == session_id:
                return run
        return None
```

### Step 9: Add Method for Historical Queries

Add a new method to query all runs (including completed) from database:

```python
def get_all_runs_from_db(self, status_filter: Optional[list[str]] = None) -> list[Run]:
    """Get all runs from database (including completed). For historical queries."""
    run_dicts = db_get_all_runs(status_filter)
    return [self._dict_to_run(d) for d in run_dicts]
```

## Complete Refactored Class Structure

```python
class RunQueue:
    """
    Thread-safe run queue with write-through cache to SQLite.

    Architecture:
    - All writes go to database first, then update in-memory cache
    - Reads come from cache for fast polling performance
    - Active runs loaded from database on startup
    - Terminal runs removed from cache (but remain in database)
    """

    def __init__(self):
        self._runs: dict[str, Run] = {}  # Cache for active runs
        self._lock = threading.Lock()
        self._load_active_runs()

    # Private helpers
    def _load_active_runs(self) -> None: ...
    def _dict_to_run(self, d: dict) -> Run: ...

    # Write operations (DB first, then cache)
    def add_run(self, run_create: RunCreate) -> Run: ...
    def claim_run(self, runner: RunnerInfo) -> Optional[Run]: ...
    def update_run_status(self, run_id: str, status: RunStatus, error: str = None) -> Optional[Run]: ...
    def set_run_demands(self, run_id: str, demands: dict, timeout_seconds: int = 300) -> Optional[Run]: ...
    def fail_timed_out_runs(self) -> list[Run]: ...

    # Read operations (cache only - fast)
    def get_run(self, run_id: str) -> Optional[Run]: ...
    def get_pending_runs(self) -> list[Run]: ...
    def get_all_runs(self) -> list[Run]: ...
    def get_run_by_session_id(self, session_id: str) -> Optional[Run]: ...

    # Historical queries (database)
    def get_all_runs_from_db(self, status_filter: list[str] = None) -> list[Run]: ...
```

## Testing

Test the refactored `RunQueue`:

```python
# tests/test_run_queue_persistence.py
import sys
sys.path.insert(0, 'servers/agent-coordinator')

from services.run_queue import RunQueue, RunCreate, RunType, ExecutionMode, RunStatus
from services.runner_registry import RunnerInfo
from database import init_db
import os

# Fresh database
db_path = 'servers/agent-coordinator/.agent-orchestrator/observability.db'
if os.path.exists(db_path):
    os.remove(db_path)
init_db()

# Create queue
queue = RunQueue()
print(f"Initial runs in cache: {len(queue.get_all_runs())}")

# Add a run
run = queue.add_run(RunCreate(
    type=RunType.START_SESSION,
    agent_name="test-agent",
    prompt="Test prompt",
    execution_mode=ExecutionMode.SYNC
))
print(f"Created run: {run.run_id}, session: {run.session_id}")

# Verify in cache
assert queue.get_run(run.run_id) is not None
print("Run in cache: OK")

# Simulate restart - create new queue instance
queue2 = RunQueue()
loaded_run = queue2.get_run(run.run_id)
assert loaded_run is not None
assert loaded_run.status == RunStatus.PENDING
print(f"Run survived restart: {loaded_run.run_id}")

# Claim it
runner = RunnerInfo(
    runner_id="test_runner",
    hostname="localhost",
    project_dir="/tmp",
    executor_type="claude-code",
    registered_at="2025-01-01T00:00:00Z",
    last_heartbeat="2025-01-01T00:00:00Z"
)
claimed = queue2.claim_run(runner)
assert claimed is not None
assert claimed.status == RunStatus.CLAIMED
print(f"Claimed run: {claimed.run_id}")

# Complete it
queue2.update_run_status(run.run_id, RunStatus.COMPLETED)

# Verify removed from cache (terminal state)
assert queue2.get_run(run.run_id) is None
print("Terminal run removed from cache: OK")

# But still in database
all_db_runs = queue2.get_all_runs_from_db()
assert any(r.run_id == run.run_id for r in all_db_runs)
print("Terminal run still in database: OK")

print("\nAll tests passed!")
```

## Key Design Decisions

1. **Write-Through Strategy**: All writes go to DB first. If DB write fails, operation fails. Cache is always consistent with DB.

2. **Terminal Run Eviction**: Completed/failed/stopped runs are removed from cache but remain in database. This keeps the cache small and focused on active work.

3. **Atomic Claims**: The database `claim_run()` uses a WHERE clause to ensure only one runner can claim a pending run, preventing race conditions.

4. **Cache-First Reads**: Polling reads from cache for sub-millisecond performance. Historical queries use `get_all_runs_from_db()`.

5. **Startup Recovery**: Active runs are loaded from database on startup, enabling restart recovery (Phase 5 will handle edge cases).

## Notes

- The lock scope remains the same - entire operations are atomic
- Error handling should propagate database errors appropriately
- Consider adding logging for debugging persistence issues

## Next Phase

After this phase is complete, proceed to [Phase 4: Integration](./phase-4-integration.md).
