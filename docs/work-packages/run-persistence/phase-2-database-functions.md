# Phase 2: Database Functions

**Objective:** Add CRUD functions for the `runs` table in `database.py`.

## Prerequisites

- Phase 1 completed (runs table schema exists)

## Context

Add database functions following the same patterns used for sessions. These functions will be called by the refactored `RunQueue` in Phase 3.

## Files to Modify

| File | Action |
|------|--------|
| `servers/agent-coordinator/database.py` | Add run CRUD functions |

## Implementation Steps

### Step 1: Add Import for Run Model

At the top of `database.py`, ensure the Run model is imported:

```python
from services.run_queue import Run, RunStatus, RunType
```

Or define a minimal dataclass for the database layer if you want to avoid circular imports:

```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class RunStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class RunType(str, Enum):
    START_SESSION = "START_SESSION"
    RESUME_SESSION = "RESUME_SESSION"
```

### Step 2: Add Create Function

```python
def create_run(
    run_id: str,
    session_id: str,
    run_type: str,
    prompt: str,
    created_at: str,
    agent_name: Optional[str] = None,
    project_dir: Optional[str] = None,
    parent_session_id: Optional[str] = None,
    execution_mode: str = "sync",
    demands: Optional[str] = None,  # JSON string
    status: str = "pending",
    timeout_at: Optional[str] = None,
) -> None:
    """Create a new run in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO runs (
            run_id, session_id, type, prompt, created_at,
            agent_name, project_dir, parent_session_id,
            execution_mode, demands, status, timeout_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id, session_id, run_type, prompt, created_at,
            agent_name, project_dir, parent_session_id,
            execution_mode, demands, status, timeout_at
        )
    )
    conn.commit()
```

### Step 3: Add Read Functions

```python
def get_run_by_id(run_id: str) -> Optional[dict]:
    """Get a run by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    if row:
        return _row_to_run_dict(row, cursor.description)
    return None


def get_run_by_session_id(session_id: str, active_only: bool = True) -> Optional[dict]:
    """Get run by session ID. If active_only, only returns non-terminal runs."""
    conn = get_connection()
    cursor = conn.cursor()

    if active_only:
        cursor.execute(
            """
            SELECT * FROM runs
            WHERE session_id = ?
            AND status IN ('pending', 'claimed', 'running', 'stopping')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_id,)
        )
    else:
        cursor.execute(
            """
            SELECT * FROM runs
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_id,)
        )

    row = cursor.fetchone()
    if row:
        return _row_to_run_dict(row, cursor.description)
    return None


def get_all_runs(status_filter: Optional[list[str]] = None) -> list[dict]:
    """Get all runs, optionally filtered by status."""
    conn = get_connection()
    cursor = conn.cursor()

    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        cursor.execute(
            f"SELECT * FROM runs WHERE status IN ({placeholders}) ORDER BY created_at DESC",
            status_filter
        )
    else:
        cursor.execute("SELECT * FROM runs ORDER BY created_at DESC")

    rows = cursor.fetchall()
    return [_row_to_run_dict(row, cursor.description) for row in rows]


def get_pending_runs() -> list[dict]:
    """Get all pending runs ordered by creation time."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM runs WHERE status = 'pending' ORDER BY created_at ASC"
    )
    rows = cursor.fetchall()
    return [_row_to_run_dict(row, cursor.description) for row in rows]


def get_active_runs() -> list[dict]:
    """Get all active (non-terminal) runs for cache loading on startup."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM runs
        WHERE status IN ('pending', 'claimed', 'running', 'stopping')
        ORDER BY created_at ASC
        """
    )
    rows = cursor.fetchall()
    return [_row_to_run_dict(row, cursor.description) for row in rows]
```

### Step 4: Add Update Functions

```python
def update_run_status(
    run_id: str,
    status: str,
    error: Optional[str] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
) -> bool:
    """Update run status and related timestamps. Returns True if updated."""
    conn = get_connection()
    cursor = conn.cursor()

    # Build dynamic update
    updates = ["status = ?"]
    params = [status]

    if error is not None:
        updates.append("error = ?")
        params.append(error)

    if started_at is not None:
        updates.append("started_at = ?")
        params.append(started_at)

    if completed_at is not None:
        updates.append("completed_at = ?")
        params.append(completed_at)

    params.append(run_id)

    cursor.execute(
        f"UPDATE runs SET {', '.join(updates)} WHERE run_id = ?",
        params
    )
    conn.commit()
    return cursor.rowcount > 0


def claim_run(run_id: str, runner_id: str, claimed_at: str) -> bool:
    """
    Atomically claim a pending run.
    Returns True if successfully claimed, False if already claimed or not pending.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE runs
        SET status = 'claimed', runner_id = ?, claimed_at = ?
        WHERE run_id = ? AND status = 'pending'
        """,
        (runner_id, claimed_at, run_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def update_run_demands(
    run_id: str,
    demands: Optional[str],  # JSON string
    timeout_at: Optional[str],
) -> bool:
    """Update run demands and timeout. Returns True if updated."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE runs SET demands = ?, timeout_at = ? WHERE run_id = ?",
        (demands, timeout_at, run_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def fail_timed_out_runs(current_time: str) -> list[str]:
    """
    Mark pending runs past their timeout as failed.
    Returns list of run_ids that were failed.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # First, get the runs that will be failed
    cursor.execute(
        """
        SELECT run_id FROM runs
        WHERE status = 'pending'
        AND timeout_at IS NOT NULL
        AND timeout_at < ?
        """,
        (current_time,)
    )
    run_ids = [row[0] for row in cursor.fetchall()]

    if run_ids:
        # Update them all
        cursor.execute(
            """
            UPDATE runs
            SET status = 'failed',
                error = 'No matching runner available within timeout',
                completed_at = ?
            WHERE status = 'pending'
            AND timeout_at IS NOT NULL
            AND timeout_at < ?
            """,
            (current_time, current_time)
        )
        conn.commit()

    return run_ids
```

### Step 5: Add Helper Function

```python
def _row_to_run_dict(row, description) -> dict:
    """Convert a database row to a dictionary."""
    columns = [col[0] for col in description]
    return dict(zip(columns, row))
```

### Step 6: Add Optional Cleanup Function

```python
def delete_old_runs(older_than: str) -> int:
    """
    Delete completed/failed/stopped runs older than the given timestamp.
    Returns count of deleted runs.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM runs
        WHERE status IN ('completed', 'failed', 'stopped')
        AND completed_at < ?
        """,
        (older_than,)
    )
    conn.commit()
    return cursor.rowcount
```

## Function Summary

| Function | Purpose | Returns |
|----------|---------|---------|
| `create_run()` | Insert new run | None |
| `get_run_by_id()` | Lookup by run_id | dict or None |
| `get_run_by_session_id()` | Lookup by session_id | dict or None |
| `get_all_runs()` | List all runs | list[dict] |
| `get_pending_runs()` | List pending runs | list[dict] |
| `get_active_runs()` | List non-terminal runs | list[dict] |
| `update_run_status()` | Update status + timestamps | bool |
| `claim_run()` | Atomically claim pending run | bool |
| `update_run_demands()` | Set demands + timeout | bool |
| `fail_timed_out_runs()` | Timeout expired pending runs | list[str] |
| `delete_old_runs()` | Cleanup old terminal runs | int |

## Testing

Create a simple test script to verify all functions work:

```python
# tests/test_run_database.py
import sys
sys.path.insert(0, 'servers/agent-coordinator')

from database import (
    init_db, create_run, get_run_by_id, get_all_runs,
    update_run_status, claim_run, create_session
)
from datetime import datetime

# Initialize fresh database
init_db()

# Create a session first (FK requirement)
session_id = "ses_test123456"
create_session(
    session_id=session_id,
    status="pending",
    created_at=datetime.utcnow().isoformat() + "Z",
    execution_mode="sync"
)

# Create a run
run_id = "run_test123456"
create_run(
    run_id=run_id,
    session_id=session_id,
    run_type="START_SESSION",
    prompt="Test prompt",
    created_at=datetime.utcnow().isoformat() + "Z",
    agent_name="test-agent",
    status="pending"
)

# Verify it was created
run = get_run_by_id(run_id)
assert run is not None
assert run["status"] == "pending"
print(f"Created run: {run}")

# Claim it
success = claim_run(run_id, "runner_abc", datetime.utcnow().isoformat() + "Z")
assert success
run = get_run_by_id(run_id)
assert run["status"] == "claimed"
print(f"Claimed run: {run}")

# Update to running
update_run_status(run_id, "running", started_at=datetime.utcnow().isoformat() + "Z")
run = get_run_by_id(run_id)
assert run["status"] == "running"
print(f"Running run: {run}")

# Complete it
update_run_status(run_id, "completed", completed_at=datetime.utcnow().isoformat() + "Z")
run = get_run_by_id(run_id)
assert run["status"] == "completed"
print(f"Completed run: {run}")

# List all
all_runs = get_all_runs()
print(f"All runs: {len(all_runs)}")

print("\nAll tests passed!")
```

Run with:
```bash
uv run python tests/test_run_database.py
```

## Notes

- All functions use the existing `get_connection()` pattern from the sessions code
- The `claim_run()` function uses WHERE clause to ensure atomicity
- JSON demands are stored as strings - parsing happens in the application layer
- Foreign key constraints ensure referential integrity with sessions

## Next Phase

After this phase is complete, proceed to [Phase 3: RunQueue Refactor](./phase-3-run-queue-refactor.md).
