import sqlite3
from pathlib import Path
import json

DB_PATH = Path(".agent-orchestrator/observability.db")


class SessionAlreadyExistsError(Exception):
    """Raised when attempting to create a session that already exists."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session '{session_id}' already exists")

def init_db():
    """Initialize database with schema"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # Enable foreign key support (SQLite requires this per-connection)
    conn.execute("PRAGMA foreign_keys = ON")

    # Sessions table - Phase 3 (ADR-010) schema
    # session_id is coordinator-generated at run creation
    # executor_session_id stores the framework's ID (e.g., Claude SDK UUID)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            project_dir TEXT,
            agent_name TEXT,
            last_resumed_at TEXT,
            parent_session_id TEXT REFERENCES sessions(session_id) ON DELETE SET NULL,
            executor_session_id TEXT,
            executor_profile TEXT,
            hostname TEXT
        )
    """)

    # Create indexes for affinity lookups
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_executor_session_id
        ON sessions(executor_session_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_hostname
        ON sessions(hostname)
    """)

    # Runs table - work items for distribution
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            type TEXT NOT NULL,
            agent_name TEXT,
            parameters TEXT NOT NULL,
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

    # Indexes for runs table
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_session_id
        ON runs(session_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_status
        ON runs(status)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_runner_id
        ON runs(runner_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_status_created
        ON runs(status, created_at)
    """)

    # Events table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            tool_name TEXT,
            tool_input TEXT,
            tool_output TEXT,
            error TEXT,
            exit_code INTEGER,
            reason TEXT,
            role TEXT,
            content TEXT,
            result_text TEXT,
            result_data TEXT
        )
    """)

    # Index for performance
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_session
        ON events(session_id, timestamp DESC)
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully")

def insert_session(session_id: str, timestamp: str):
    """Insert or update session - used when session starts running"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        INSERT INTO sessions (session_id, status, created_at)
        VALUES (?, 'running', ?)
        ON CONFLICT(session_id) DO UPDATE SET status = 'running'
    """, (session_id, timestamp))
    conn.commit()
    conn.close()

def update_session_status(session_id: str, status: str):
    """Update session status (e.g., 'running' -> 'finished')"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        UPDATE sessions
        SET status = ?
        WHERE session_id = ?
    """, (status, session_id))
    conn.commit()
    conn.close()

def update_session_metadata(
    session_id: str,
    project_dir: str = None,
    agent_name: str = None,
    last_resumed_at: str = None,
    executor_session_id: str = None,
    executor_profile: str = None,
    hostname: str = None
):
    """Update session metadata fields"""
    conn = sqlite3.connect(DB_PATH)

    updates = []
    params = []

    if project_dir is not None:
        updates.append("project_dir = ?")
        params.append(project_dir)

    if agent_name is not None:
        updates.append("agent_name = ?")
        params.append(agent_name)

    if last_resumed_at is not None:
        updates.append("last_resumed_at = ?")
        params.append(last_resumed_at)

    if executor_session_id is not None:
        updates.append("executor_session_id = ?")
        params.append(executor_session_id)

    if executor_profile is not None:
        updates.append("executor_profile = ?")
        params.append(executor_profile)

    if hostname is not None:
        updates.append("hostname = ?")
        params.append(hostname)

    if not updates:
        conn.close()
        return

    params.append(session_id)
    query = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?"

    conn.execute(query, params)
    conn.commit()
    conn.close()

def insert_event(event):
    """Insert event"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        INSERT INTO events
        (session_id, event_type, timestamp, tool_name, tool_input, tool_output, error, exit_code, reason, role, content, result_text, result_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event.session_id,
        event.event_type,
        event.timestamp,
        event.tool_name,
        json.dumps(event.tool_input) if event.tool_input else None,
        json.dumps(event.tool_output) if event.tool_output else None,
        event.error,
        event.exit_code,
        event.reason,
        event.role,
        json.dumps(event.content) if event.content else None,
        event.result_text,
        json.dumps(event.result_data) if event.result_data else None
    ))
    conn.commit()
    conn.close()

def get_sessions():
    """Get all sessions"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT * FROM sessions
        ORDER BY created_at DESC
    """)
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sessions

def get_events(session_id: str, limit: int = 100):
    """Get events for a session"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT * FROM events
        WHERE session_id = ?
        ORDER BY timestamp ASC
        LIMIT ?
    """, (session_id, limit))

    events = []
    for row in cursor.fetchall():
        event = dict(row)
        if event['tool_input']:
            event['tool_input'] = json.loads(event['tool_input'])
        if event['tool_output']:
            event['tool_output'] = json.loads(event['tool_output'])
        if event['content']:
            event['content'] = json.loads(event['content'])
        if event.get('result_data'):
            event['result_data'] = json.loads(event['result_data'])
        events.append(event)

    conn.close()
    return events

def delete_session(session_id: str) -> dict | None:
    """
    Delete session and all associated events and runs.
    Events and runs are deleted automatically via CASCADE.

    Returns:
        dict with deletion stats if session exists, None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Count events before deleting (for response)
    cursor.execute(
        "SELECT COUNT(*) FROM events WHERE session_id = ?",
        (session_id,)
    )
    events_count = cursor.fetchone()[0]

    # Count runs before deleting (for response)
    cursor.execute(
        "SELECT COUNT(*) FROM runs WHERE session_id = ?",
        (session_id,)
    )
    runs_count = cursor.fetchone()[0]

    # Check if session exists
    cursor.execute(
        "SELECT COUNT(*) FROM sessions WHERE session_id = ?",
        (session_id,)
    )
    session_exists = cursor.fetchone()[0] > 0

    if not session_exists:
        conn.close()
        return None

    # Delete session (events and runs deleted via CASCADE)
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    conn.commit()
    conn.close()

    return {
        "session": True,
        "events_count": events_count,
        "runs_count": runs_count
    }


def create_session(
    session_id: str,
    timestamp: str,
    status: str = "pending",
    project_dir: str = None,
    agent_name: str = None,
    parent_session_id: str = None,
) -> dict:
    """Create a new session with full metadata at creation time.

    Session is created with status='pending' by default (before executor binds).
    Status changes to 'running' when executor binds.

    Note: execution_mode is stored on runs, not sessions. Callback behavior
    is determined by the run's execution_mode (ADR-003).

    Raises:
        SessionAlreadyExistsError: If session_id already exists.
    """
    # Check if session already exists before attempting insert
    if get_session_by_id(session_id) is not None:
        raise SessionAlreadyExistsError(session_id)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        INSERT INTO sessions (session_id, status, created_at, project_dir, agent_name, parent_session_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, status, timestamp, project_dir, agent_name, parent_session_id))
    conn.commit()
    conn.close()
    return get_session_by_id(session_id)


def bind_session_executor(
    session_id: str,
    executor_session_id: str,
    hostname: str,
    executor_profile: str,
    project_dir: str = None
) -> dict | None:
    """Bind executor information to a session after framework starts.

    Called by executor after it gets the framework's session ID.
    Updates session status to 'running'.

    Args:
        session_id: Our coordinator-generated session ID
        executor_session_id: Framework's session ID (e.g., Claude SDK UUID)
        hostname: Machine where session is running
        executor_profile: Profile used by executor (e.g., "coding")
        project_dir: Optional project directory override

    Returns:
        Updated session dict, or None if session not found
    """
    conn = sqlite3.connect(DB_PATH)

    # Check if session exists
    cursor = conn.execute(
        "SELECT session_id FROM sessions WHERE session_id = ?",
        (session_id,)
    )
    if not cursor.fetchone():
        conn.close()
        return None

    # Build update query
    updates = [
        "executor_session_id = ?",
        "hostname = ?",
        "executor_profile = ?",
        "status = 'running'"
    ]
    params = [executor_session_id, hostname, executor_profile]

    if project_dir is not None:
        updates.append("project_dir = ?")
        params.append(project_dir)

    params.append(session_id)
    query = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?"

    conn.execute(query, params)
    conn.commit()
    conn.close()

    return get_session_by_id(session_id)


def get_session_by_id(session_id: str) -> dict | None:
    """Get a single session by ID"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT * FROM sessions WHERE session_id = ?
    """, (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_session_result(session_id: str) -> dict | None:
    """Get structured result from result event.

    Returns:
        dict with {result_text, result_data} or None if no result event exists.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT result_text, result_data FROM events
        WHERE session_id = ? AND event_type = 'result'
        ORDER BY timestamp DESC LIMIT 1
    """, (session_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "result_text": row["result_text"],
        "result_data": json.loads(row["result_data"]) if row["result_data"] else None
    }


def get_session_by_executor_session_id(executor_session_id: str) -> dict | None:
    """Get a session by the framework's executor_session_id.

    Useful for looking up sessions when only the framework's ID is known.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT * FROM sessions WHERE executor_session_id = ?
    """, (executor_session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_session_parent(session_id: str, parent_session_id: str) -> None:
    """Update the parent_session_id of a session.

    Used when resuming a session - the parent may be different from the original.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "UPDATE sessions SET parent_session_id = ? WHERE session_id = ?",
        (parent_session_id, session_id)
    )
    conn.commit()
    conn.close()


def get_session_affinity(session_id: str) -> dict | None:
    """Get session affinity information for resume routing.

    Returns hostname, project_dir, executor_profile needed to route
    resume requests to the correct runner.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT session_id, executor_session_id, hostname, project_dir, executor_profile
        FROM sessions WHERE session_id = ?
    """, (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================================
# Run CRUD Functions
# ============================================================================

def _row_to_run_dict(row, description) -> dict:
    """Convert a database row to a dictionary."""
    columns = [col[0] for col in description]
    return dict(zip(columns, row))


def create_run(
    run_id: str,
    session_id: str,
    run_type: str,
    parameters: str,  # JSON string of parameters dict
    created_at: str,
    agent_name: str = None,
    project_dir: str = None,
    parent_session_id: str = None,
    execution_mode: str = "sync",
    demands: str = None,  # JSON string
    status: str = "pending",
    timeout_at: str = None,
) -> None:
    """Create a new run in the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO runs (
            run_id, session_id, type, parameters, created_at,
            agent_name, project_dir, parent_session_id,
            execution_mode, demands, status, timeout_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id, session_id, run_type, parameters, created_at,
            agent_name, project_dir, parent_session_id,
            execution_mode, demands, status, timeout_at
        )
    )
    conn.commit()
    conn.close()


def get_run_by_id(run_id: str) -> dict | None:
    """Get a run by its ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    if row:
        result = _row_to_run_dict(row, cursor.description)
        conn.close()
        return result
    conn.close()
    return None


def get_run_by_session_id(session_id: str, active_only: bool = True) -> dict | None:
    """Get run by session ID. If active_only, only returns non-terminal runs."""
    conn = sqlite3.connect(DB_PATH)
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
        result = _row_to_run_dict(row, cursor.description)
        conn.close()
        return result
    conn.close()
    return None


def get_all_runs(status_filter: list[str] = None) -> list[dict]:
    """Get all runs, optionally filtered by status."""
    conn = sqlite3.connect(DB_PATH)
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
    result = [_row_to_run_dict(row, cursor.description) for row in rows]
    conn.close()
    return result


def get_pending_runs() -> list[dict]:
    """Get all pending runs ordered by creation time."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM runs WHERE status = 'pending' ORDER BY created_at ASC"
    )
    rows = cursor.fetchall()
    result = [_row_to_run_dict(row, cursor.description) for row in rows]
    conn.close()
    return result


def get_active_runs() -> list[dict]:
    """Get all active (non-terminal) runs for cache loading on startup."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM runs
        WHERE status IN ('pending', 'claimed', 'running', 'stopping')
        ORDER BY created_at ASC
        """
    )
    rows = cursor.fetchall()
    result = [_row_to_run_dict(row, cursor.description) for row in rows]
    conn.close()
    return result


def update_run_status(
    run_id: str,
    status: str,
    error: str = None,
    started_at: str = None,
    completed_at: str = None,
) -> bool:
    """Update run status and related timestamps. Returns True if updated."""
    conn = sqlite3.connect(DB_PATH)
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
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def claim_run(run_id: str, runner_id: str, claimed_at: str) -> bool:
    """
    Atomically claim a pending run.
    Returns True if successfully claimed, False if already claimed or not pending.
    """
    conn = sqlite3.connect(DB_PATH)
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
    claimed = cursor.rowcount > 0
    conn.close()
    return claimed


def update_run_demands(
    run_id: str,
    demands: str,  # JSON string
    timeout_at: str,
) -> bool:
    """Update run demands and timeout. Returns True if updated."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE runs SET demands = ?, timeout_at = ? WHERE run_id = ?",
        (demands, timeout_at, run_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def fail_timed_out_runs(current_time: str) -> list[str]:
    """
    Mark pending runs past their timeout as failed.
    Returns list of run_ids that were failed.
    """
    conn = sqlite3.connect(DB_PATH)
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

    conn.close()
    return run_ids


def delete_old_runs(older_than: str) -> int:
    """
    Delete completed/failed/stopped runs older than the given timestamp.
    Returns count of deleted runs.
    """
    conn = sqlite3.connect(DB_PATH)
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
    deleted_count = cursor.rowcount
    conn.close()
    return deleted_count


# ============================================================================
# Recovery Functions (Phase 5)
# ============================================================================

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
    from datetime import datetime, timedelta, timezone

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Calculate threshold time
    threshold = (
        datetime.now(timezone.utc) - timedelta(seconds=stale_threshold_seconds)
    ).isoformat()

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
    conn.close()
    return results


def recover_all_active_runs() -> dict:
    """
    Aggressively recover all non-terminal runs.

    Use this when:
    - Coordinator was down for a long time
    - You want to clean slate all active runs

    Returns:
        dict with counts of recovered runs by original status
    """
    from datetime import datetime, timezone

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    results = {"claimed": 0, "running": 0, "stopping": 0}

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
    conn.close()
    return results
