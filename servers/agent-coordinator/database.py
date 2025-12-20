import sqlite3
from pathlib import Path
import json

DB_PATH = Path(".agent-orchestrator/observability.db")

def init_db():
    """Initialize database with schema"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # Enable foreign key support (SQLite requires this per-connection)
    conn.execute("PRAGMA foreign_keys = ON")

    # Sessions table - Phase 3 (ADR-010) schema
    # session_id is coordinator-generated at run creation
    # executor_session_id stores the framework's ID (e.g., Claude SDK UUID)
    # execution_mode controls callback behavior per ADR-003
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            project_dir TEXT,
            agent_name TEXT,
            last_resumed_at TEXT,
            parent_session_id TEXT REFERENCES sessions(session_id) ON DELETE SET NULL,
            execution_mode TEXT DEFAULT 'sync',
            executor_session_id TEXT,
            executor_type TEXT,
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
            content TEXT
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
    executor_type: str = None,
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

    if executor_type is not None:
        updates.append("executor_type = ?")
        params.append(executor_type)

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
        (session_id, event_type, timestamp, tool_name, tool_input, tool_output, error, exit_code, reason, role, content)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        json.dumps(event.content) if event.content else None
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
        events.append(event)

    conn.close()
    return events

def delete_session(session_id: str) -> dict | None:
    """
    Delete session and all associated events.
    Events are deleted automatically via CASCADE.

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

    # Check if session exists
    cursor.execute(
        "SELECT COUNT(*) FROM sessions WHERE session_id = ?",
        (session_id,)
    )
    session_exists = cursor.fetchone()[0] > 0

    if not session_exists:
        conn.close()
        return None

    # Delete session (events deleted via CASCADE)
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    conn.commit()
    conn.close()

    return {
        "session": True,
        "events_count": events_count
    }


def create_session(
    session_id: str,
    timestamp: str,
    status: str = "pending",
    project_dir: str = None,
    agent_name: str = None,
    parent_session_id: str = None,
    execution_mode: str = "sync"
) -> dict:
    """Create a new session with full metadata at creation time.

    Session is created with status='pending' by default (before executor binds).
    Status changes to 'running' when executor binds.
    execution_mode controls callback behavior per ADR-003.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        INSERT INTO sessions (session_id, status, created_at, project_dir, agent_name, parent_session_id, execution_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, status, timestamp, project_dir, agent_name, parent_session_id, execution_mode))
    conn.commit()
    conn.close()
    return get_session_by_id(session_id)


def bind_session_executor(
    session_id: str,
    executor_session_id: str,
    hostname: str,
    executor_type: str,
    project_dir: str = None
) -> dict | None:
    """Bind executor information to a session after framework starts.

    Called by executor after it gets the framework's session ID.
    Updates session status to 'running'.

    Args:
        session_id: Our coordinator-generated session ID
        executor_session_id: Framework's session ID (e.g., Claude SDK UUID)
        hostname: Machine where session is running
        executor_type: Type of executor (e.g., "claude-code")
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
        "executor_type = ?",
        "status = 'running'"
    ]
    params = [executor_session_id, hostname, executor_type]

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


def get_session_result(session_id: str) -> str | None:
    """Extract result from the last assistant message event"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT content FROM events
        WHERE session_id = ? AND event_type = 'message' AND role = 'assistant'
        ORDER BY timestamp DESC LIMIT 1
    """, (session_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row['content']:
        return None

    content = json.loads(row['content'])
    if content and len(content) > 0 and 'text' in content[0]:
        return content[0]['text']
    return None


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

    Returns hostname, project_dir, executor_type needed to route
    resume requests to the correct runner.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT session_id, executor_session_id, hostname, project_dir, executor_type
        FROM sessions WHERE session_id = ?
    """, (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
