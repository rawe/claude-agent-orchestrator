# Phase 5: Startup Recovery

**Objective:** Handle edge cases when the coordinator restarts with runs in non-terminal states.

## Prerequisites

- Phase 1-4 completed
- Basic persistence working

## Context

When the coordinator restarts, it loads active runs from the database. However, some runs may be in inconsistent states:

- **CLAIMED runs**: A runner had claimed this, but the runner may no longer exist
- **RUNNING runs**: A runner was executing this, but the execution may have crashed
- **STOPPING runs**: A stop command was issued but never completed

This phase handles these edge cases to ensure the system recovers gracefully.

## Recovery Strategies

| State | Problem | Strategy |
|-------|---------|----------|
| `pending` | Normal - waiting for runner | Keep as-is |
| `claimed` | Runner may have died | Reset to `pending` or mark `failed` |
| `running` | Execution may have crashed | Mark as `failed` with recovery error |
| `stopping` | Stop never completed | Mark as `stopped` |

## Files to Modify

| File | Action |
|------|--------|
| `servers/agent-coordinator/services/run_queue.py` | Add recovery logic |
| `servers/agent-coordinator/database.py` | Add recovery queries |

## Implementation Steps

### Step 1: Add Database Recovery Functions

In `database.py`, add functions to handle recovery:

```python
def recover_stale_runs(stale_threshold_seconds: int = 300) -> dict:
    """
    Recover runs that were in non-terminal states when coordinator restarted.

    This handles:
    - CLAIMED runs: Reset to PENDING (runner may have died)
    - RUNNING runs: Mark as FAILED (execution crashed)
    - STOPPING runs: Mark as STOPPED (stop never completed)

    Args:
        stale_threshold_seconds: Consider runs stale if claimed/started more than
                                 this many seconds ago (default 5 minutes)

    Returns:
        dict with counts: {"reset_to_pending": N, "marked_failed": N, "marked_stopped": N}
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"

    # Calculate threshold time
    threshold = (
        datetime.utcnow() - timedelta(seconds=stale_threshold_seconds)
    ).isoformat() + "Z"

    results = {"reset_to_pending": 0, "marked_failed": 0, "marked_stopped": 0}

    # Reset CLAIMED runs to PENDING
    # These were claimed but never started - runner likely died
    cursor.execute(
        """
        UPDATE runs
        SET status = 'pending',
            runner_id = NULL,
            claimed_at = NULL
        WHERE status = 'claimed'
        AND (claimed_at IS NULL OR claimed_at < ?)
        """,
        (threshold,)
    )
    results["reset_to_pending"] = cursor.rowcount

    # Mark RUNNING runs as FAILED
    # These were executing but coordinator restarted - execution state is unknown
    cursor.execute(
        """
        UPDATE runs
        SET status = 'failed',
            error = 'Coordinator restarted during execution',
            completed_at = ?
        WHERE status = 'running'
        AND (started_at IS NULL OR started_at < ?)
        """,
        (now, threshold)
    )
    results["marked_failed"] = cursor.rowcount

    # Mark STOPPING runs as STOPPED
    # Stop command was issued but never completed - consider it stopped
    cursor.execute(
        """
        UPDATE runs
        SET status = 'stopped',
            completed_at = ?
        WHERE status = 'stopping'
        """,
        (now,)
    )
    results["marked_stopped"] = cursor.rowcount

    conn.commit()
    return results
```

### Step 2: Add Aggressive Recovery Option

For cases where you want to recover all non-pending runs regardless of time:

```python
def recover_all_active_runs() -> dict:
    """
    Aggressively recover all non-terminal runs.

    Use this when:
    - Coordinator was down for a long time
    - You want to clean slate all active runs

    Returns:
        dict with counts of recovered runs by original status
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"

    results = {}

    # Count runs in each state before recovery
    for status in ['claimed', 'running', 'stopping']:
        cursor.execute(
            "SELECT COUNT(*) FROM runs WHERE status = ?",
            (status,)
        )
        results[status] = cursor.fetchone()[0]

    # Reset all CLAIMED to PENDING
    cursor.execute(
        """
        UPDATE runs
        SET status = 'pending', runner_id = NULL, claimed_at = NULL
        WHERE status = 'claimed'
        """
    )

    # Mark all RUNNING as FAILED
    cursor.execute(
        """
        UPDATE runs
        SET status = 'failed',
            error = 'Coordinator restarted - execution state unknown',
            completed_at = ?
        WHERE status = 'running'
        """,
        (now,)
    )

    # Mark all STOPPING as STOPPED
    cursor.execute(
        """
        UPDATE runs
        SET status = 'stopped', completed_at = ?
        WHERE status = 'stopping'
        """,
        (now,)
    )

    conn.commit()
    return results
```

### Step 3: Integrate Recovery into RunQueue Initialization

Update `run_queue.py` to run recovery before loading:

```python
class RunQueue:
    def __init__(self, recovery_mode: str = "stale"):
        """
        Initialize RunQueue with optional recovery.

        Args:
            recovery_mode: How to handle non-terminal runs from previous session
                - "none": Load as-is (may have stale claimed/running runs)
                - "stale": Recover runs older than 5 minutes (default)
                - "all": Aggressively recover all non-terminal runs
        """
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

        # Run recovery before loading
        self._run_recovery(recovery_mode)

        # Load active runs
        self._load_active_runs()

    def _run_recovery(self, mode: str) -> None:
        """Handle recovery of stale runs from previous coordinator session."""
        if mode == "none":
            return

        if mode == "all":
            from database import recover_all_active_runs
            results = recover_all_active_runs()
            if any(results.values()):
                print(f"[RunQueue] Recovery (all): {results}")
            return

        # Default: stale recovery
        from database import recover_stale_runs
        results = recover_stale_runs(stale_threshold_seconds=300)
        if any(results.values()):
            print(f"[RunQueue] Recovery (stale): {results}")
```

### Step 4: Add Recovery Configuration

In `main.py`, allow configuration of recovery mode:

```python
import os

# Configuration
RUN_RECOVERY_MODE = os.environ.get("RUN_RECOVERY_MODE", "stale")

# When creating RunQueue
run_queue = RunQueue(recovery_mode=RUN_RECOVERY_MODE)
```

Environment variable options:
- `RUN_RECOVERY_MODE=none` - Don't recover (dangerous)
- `RUN_RECOVERY_MODE=stale` - Recover runs > 5 minutes old (default)
- `RUN_RECOVERY_MODE=all` - Recover all non-terminal runs (aggressive)

### Step 5: Add Recovery Endpoint (Optional)

Add an admin endpoint to trigger manual recovery:

```python
@app.post("/admin/recover-runs")
async def admin_recover_runs(mode: str = "stale"):
    """
    Manually trigger run recovery.

    Args:
        mode: "stale" or "all"
    """
    if mode == "all":
        from database import recover_all_active_runs
        results = recover_all_active_runs()
    else:
        from database import recover_stale_runs
        results = recover_stale_runs()

    # Reload the cache
    run_queue._load_active_runs()

    return {"recovered": results}
```

### Step 6: Handle Session Status Consistency

When runs are marked as failed during recovery, ensure corresponding sessions are updated:

```python
def recover_stale_runs_with_sessions(stale_threshold_seconds: int = 300) -> dict:
    """
    Recover runs and update corresponding session status.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    threshold = (
        datetime.utcnow() - timedelta(seconds=stale_threshold_seconds)
    ).isoformat() + "Z"

    results = {"reset_to_pending": 0, "marked_failed": 0, "marked_stopped": 0}

    # Get RUNNING runs that will be marked failed
    cursor.execute(
        """
        SELECT session_id FROM runs
        WHERE status = 'running'
        AND (started_at IS NULL OR started_at < ?)
        """,
        (threshold,)
    )
    running_session_ids = [row[0] for row in cursor.fetchall()]

    # Get STOPPING runs that will be marked stopped
    cursor.execute("SELECT session_id FROM runs WHERE status = 'stopping'")
    stopping_session_ids = [row[0] for row in cursor.fetchall()]

    # Reset CLAIMED runs to PENDING
    cursor.execute(
        """
        UPDATE runs
        SET status = 'pending', runner_id = NULL, claimed_at = NULL
        WHERE status = 'claimed'
        AND (claimed_at IS NULL OR claimed_at < ?)
        """,
        (threshold,)
    )
    results["reset_to_pending"] = cursor.rowcount

    # Mark RUNNING runs as FAILED
    cursor.execute(
        """
        UPDATE runs
        SET status = 'failed',
            error = 'Coordinator restarted during execution',
            completed_at = ?
        WHERE status = 'running'
        AND (started_at IS NULL OR started_at < ?)
        """,
        (now, threshold)
    )
    results["marked_failed"] = cursor.rowcount

    # Update corresponding sessions to 'finished' with error indicator
    if running_session_ids:
        placeholders = ",".join("?" * len(running_session_ids))
        cursor.execute(
            f"""
            UPDATE sessions
            SET status = 'finished'
            WHERE session_id IN ({placeholders})
            AND status = 'running'
            """,
            running_session_ids
        )

    # Mark STOPPING runs as STOPPED
    cursor.execute(
        """
        UPDATE runs
        SET status = 'stopped', completed_at = ?
        WHERE status = 'stopping'
        """,
        (now,)
    )
    results["marked_stopped"] = cursor.rowcount

    # Update corresponding sessions to 'stopped'
    if stopping_session_ids:
        placeholders = ",".join("?" * len(stopping_session_ids))
        cursor.execute(
            f"""
            UPDATE sessions
            SET status = 'stopped'
            WHERE session_id IN ({placeholders})
            AND status IN ('running', 'stopping')
            """,
            stopping_session_ids
        )

    conn.commit()
    return results
```

## Recovery Decision Tree

```
Coordinator Starts
        │
        ▼
┌───────────────────┐
│ Load runs from DB │
└───────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│ For each run in CLAIMED/RUNNING/STOPPING status: │
└───────────────────────────────────────────────────┘
        │
        ├── CLAIMED ──────────────────────────────────┐
        │   Was the runner still alive?               │
        │   (Check runner_registry for runner_id)     │
        │                                             │
        │   YES → Keep as CLAIMED                     │
        │   NO  → Reset to PENDING                    │
        │                                             │
        ├── RUNNING ──────────────────────────────────┤
        │   Can we determine execution status?        │
        │   (Usually NO after restart)                │
        │                                             │
        │   Unknown → Mark as FAILED                  │
        │   "Coordinator restarted during execution"  │
        │                                             │
        └── STOPPING ─────────────────────────────────┤
            Stop command was in progress              │
            Runner never confirmed stop               │
                                                      │
            Mark as STOPPED                           │
            (Stop intent was clear)                   │
                                                      │
        ┌─────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│ Load remaining PENDING runs   │
│ into cache for claiming       │
└───────────────────────────────┘
```

## Testing Recovery

### Test Script

```python
# tests/test_recovery.py
import sys
sys.path.insert(0, 'servers/agent-coordinator')

from database import (
    init_db, create_run, create_session, get_run_by_id,
    recover_stale_runs
)
from datetime import datetime, timedelta
import os

# Fresh database
db_path = 'servers/agent-coordinator/.agent-orchestrator/observability.db'
if os.path.exists(db_path):
    os.remove(db_path)
init_db()

# Create test data with various states
now = datetime.utcnow()
old_time = (now - timedelta(minutes=10)).isoformat() + "Z"
now_str = now.isoformat() + "Z"

# Create sessions first
for i in range(4):
    create_session(
        session_id=f"ses_test{i}",
        status="running",
        created_at=old_time,
        execution_mode="sync"
    )

# Create runs in different states
from database import get_connection

conn = get_connection()
cursor = conn.cursor()

# PENDING run (should stay pending)
cursor.execute("""
    INSERT INTO runs (run_id, session_id, type, prompt, status, created_at)
    VALUES ('run_pending', 'ses_test0', 'START_SESSION', 'test', 'pending', ?)
""", (old_time,))

# CLAIMED run (old, should reset to pending)
cursor.execute("""
    INSERT INTO runs (run_id, session_id, type, prompt, status, runner_id, claimed_at, created_at)
    VALUES ('run_claimed', 'ses_test1', 'START_SESSION', 'test', 'claimed', 'runner_dead', ?, ?)
""", (old_time, old_time))

# RUNNING run (old, should mark failed)
cursor.execute("""
    INSERT INTO runs (run_id, session_id, type, prompt, status, runner_id, started_at, created_at)
    VALUES ('run_running', 'ses_test2', 'START_SESSION', 'test', 'running', 'runner_dead', ?, ?)
""", (old_time, old_time))

# STOPPING run (should mark stopped)
cursor.execute("""
    INSERT INTO runs (run_id, session_id, type, prompt, status, runner_id, created_at)
    VALUES ('run_stopping', 'ses_test3', 'START_SESSION', 'test', 'stopping', 'runner_dead', ?)
""", (old_time,))

conn.commit()

print("Before recovery:")
for run_id in ['run_pending', 'run_claimed', 'run_running', 'run_stopping']:
    run = get_run_by_id(run_id)
    print(f"  {run_id}: {run['status']}")

# Run recovery
results = recover_stale_runs(stale_threshold_seconds=300)
print(f"\nRecovery results: {results}")

print("\nAfter recovery:")
for run_id in ['run_pending', 'run_claimed', 'run_running', 'run_stopping']:
    run = get_run_by_id(run_id)
    print(f"  {run_id}: {run['status']}, error: {run.get('error')}")

# Verify expectations
run = get_run_by_id('run_pending')
assert run['status'] == 'pending', "Pending should stay pending"

run = get_run_by_id('run_claimed')
assert run['status'] == 'pending', "Old claimed should reset to pending"

run = get_run_by_id('run_running')
assert run['status'] == 'failed', "Old running should be failed"

run = get_run_by_id('run_stopping')
assert run['status'] == 'stopped', "Stopping should be stopped"

print("\nAll recovery tests passed!")
```

Run with:
```bash
uv run python tests/test_recovery.py
```

## Configuration Options

| Env Variable | Values | Default | Description |
|--------------|--------|---------|-------------|
| `RUN_RECOVERY_MODE` | `none`, `stale`, `all` | `stale` | Recovery mode on startup |
| `RUN_RECOVERY_THRESHOLD` | seconds | `300` | Stale threshold for recovery |

## Logging

Add logging to track recovery actions:

```python
import logging

logger = logging.getLogger(__name__)

def _run_recovery(self, mode: str) -> None:
    if mode == "none":
        logger.info("Run recovery disabled")
        return

    if mode == "all":
        results = recover_all_active_runs()
        logger.warning(f"Aggressive recovery completed: {results}")
        return

    results = recover_stale_runs()
    if any(results.values()):
        logger.info(f"Stale run recovery completed: {results}")
    else:
        logger.debug("No stale runs to recover")
```

## Success Criteria

- [ ] CLAIMED runs older than threshold reset to PENDING
- [ ] RUNNING runs older than threshold marked FAILED with error message
- [ ] STOPPING runs marked STOPPED
- [ ] Session status updated consistently with run status
- [ ] Recovery runs automatically on coordinator startup
- [ ] Recovery can be triggered manually via admin endpoint
- [ ] All existing tests still pass
- [ ] Logging provides visibility into recovery actions

## Notes

- Recovery is conservative - it assumes the worst case (runner died)
- The threshold (5 minutes) can be tuned based on expected runner heartbeat intervals
- For production, consider adding metrics for recovered runs
- The "all" recovery mode is useful for development/debugging

## Completion

After this phase, the run persistence feature is complete:

- [x] Phase 1: Database schema
- [x] Phase 2: Database functions
- [x] Phase 3: RunQueue refactor
- [x] Phase 4: Integration
- [x] Phase 5: Startup recovery

The system now:
- Persists all runs to SQLite
- Survives coordinator restarts
- Handles stale runs gracefully
- Maintains fast polling through write-through cache
- Provides historical run queries
