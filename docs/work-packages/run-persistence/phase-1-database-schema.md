# Phase 1: Database Schema

**Objective:** Add the `runs` table to the SQLite database schema.

## Context

The `runs` table will store all agent runs with a foreign key reference to the `sessions` table. This establishes the session-run relationship in the database.

## Files to Modify

| File | Action |
|------|--------|
| `servers/agent-coordinator/database.py` | Add runs table in `init_db()` |

## Implementation Steps

### Step 1: Add Runs Table Schema

In `database.py`, locate the `init_db()` function and add the `runs` table creation after the `sessions` table.

**Add this SQL in `init_db()`:**

```python
# Runs table - work items for distribution
cursor.execute("""
    CREATE TABLE IF NOT EXISTS runs (
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
    )
""")
```

### Step 2: Add Indexes

Add indexes for common query patterns:

```python
# Indexes for runs table
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_runs_session_id
    ON runs(session_id)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_runs_status
    ON runs(status)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_runs_runner_id
    ON runs(runner_id)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_runs_status_created
    ON runs(status, created_at)
""")
```

## Schema Details

### Column Definitions

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `run_id` | TEXT | NO | - | Primary key (format: `run_{12-hex}`) |
| `session_id` | TEXT | NO | - | FK to sessions.session_id |
| `type` | TEXT | NO | - | `START_SESSION` or `RESUME_SESSION` |
| `agent_name` | TEXT | YES | NULL | Agent blueprint name |
| `prompt` | TEXT | NO | - | The prompt/task for the agent |
| `project_dir` | TEXT | YES | NULL | Project directory path |
| `parent_session_id` | TEXT | YES | NULL | For callback mode (parent's session) |
| `execution_mode` | TEXT | NO | `sync` | `sync`, `async_poll`, `async_callback` |
| `demands` | TEXT | YES | NULL | JSON blob of merged demands |
| `status` | TEXT | NO | `pending` | Run status (see below) |
| `runner_id` | TEXT | YES | NULL | ID of runner that claimed this run |
| `error` | TEXT | YES | NULL | Error message if failed |
| `created_at` | TEXT | NO | - | ISO 8601 timestamp |
| `claimed_at` | TEXT | YES | NULL | When run was claimed |
| `started_at` | TEXT | YES | NULL | When execution started |
| `completed_at` | TEXT | YES | NULL | When run reached terminal state |
| `timeout_at` | TEXT | YES | NULL | Demand matching timeout |

### Status Values

| Status | Description |
|--------|-------------|
| `pending` | Waiting to be claimed by a runner |
| `claimed` | Claimed by runner, not yet started |
| `running` | Actively executing |
| `stopping` | Stop command issued, waiting for runner to stop |
| `completed` | Successfully finished |
| `failed` | Failed (error or timeout) |
| `stopped` | Stopped via stop command |

### Demands JSON Structure

The `demands` column stores a JSON object:

```json
{
    "hostname": "machine-1",
    "project_dir": "/path/to/project",
    "executor_type": "claude-code",
    "tags": ["gpu", "high-memory"]
}
```

All fields are optional. Only specified fields are matched.

## Verification

After implementation, verify the schema:

```bash
# Start the coordinator to trigger init_db()
uv run --script servers/agent-coordinator/main.py

# In another terminal, inspect the database
sqlite3 servers/agent-coordinator/.agent-orchestrator/observability.db ".schema runs"
```

Expected output should show the runs table with all columns and indexes.

## Testing

1. Delete existing database (fresh start):
   ```bash
   rm -f servers/agent-coordinator/.agent-orchestrator/observability.db
   ```

2. Start coordinator - should create database with new schema

3. Verify table exists:
   ```bash
   sqlite3 servers/agent-coordinator/.agent-orchestrator/observability.db "SELECT name FROM sqlite_master WHERE type='table' AND name='runs'"
   ```

4. Verify foreign key constraint works:
   ```bash
   # This should fail (no matching session)
   sqlite3 servers/agent-coordinator/.agent-orchestrator/observability.db \
     "INSERT INTO runs (run_id, session_id, type, prompt, status, created_at) VALUES ('run_test', 'ses_nonexistent', 'START_SESSION', 'test', 'pending', '2025-01-01T00:00:00Z')"
   ```

## Notes

- The `ON DELETE CASCADE` ensures runs are deleted when their session is deleted
- The `demands` column uses JSON for flexibility (runner capabilities may evolve)
- Indexes are chosen based on common query patterns (claim by status, lookup by session)

## Next Phase

After this phase is complete, proceed to [Phase 2: Database Functions](./phase-2-database-functions.md).
