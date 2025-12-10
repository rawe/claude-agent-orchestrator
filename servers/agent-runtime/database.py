import sqlite3
from pathlib import Path
import json

DB_PATH = Path(".agent-orchestrator/observability.db")

def init_db():
    """Initialize database with schema"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # Sessions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            session_name TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            project_dir TEXT,
            agent_name TEXT,
            last_resumed_at TEXT,
            parent_session_name TEXT
        )
    """)

    # Add last_resumed_at column if it doesn't exist (migration for existing databases)
    try:
        conn.execute("ALTER TABLE sessions ADD COLUMN last_resumed_at TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add parent_session_name column if it doesn't exist (migration for callback support)
    try:
        conn.execute("ALTER TABLE sessions ADD COLUMN parent_session_name TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Events table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
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
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
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

def insert_session(session_id: str, session_name: str, timestamp: str):
    """Insert or update session"""
    conn = sqlite3.connect(DB_PATH)
    # Use INSERT ... ON CONFLICT to preserve project_dir when resuming sessions
    # Only update status to 'running', don't replace entire row
    conn.execute("""
        INSERT INTO sessions (session_id, session_name, status, created_at)
        VALUES (?, ?, 'running', ?)
        ON CONFLICT(session_id) DO UPDATE SET status = 'running'
    """, (session_id, session_name, timestamp))
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

def update_session_metadata(session_id: str, session_name: str = None, project_dir: str = None, agent_name: str = None, last_resumed_at: str = None):
    """Update session metadata fields"""
    conn = sqlite3.connect(DB_PATH)

    updates = []
    params = []

    if session_name is not None:
        updates.append("session_name = ?")
        params.append(session_name)

    if project_dir is not None:
        updates.append("project_dir = ?")
        params.append(project_dir)

    if agent_name is not None:
        updates.append("agent_name = ?")
        params.append(agent_name)

    if last_resumed_at is not None:
        updates.append("last_resumed_at = ?")
        params.append(last_resumed_at)

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

    Returns:
        dict with deletion stats if session exists, None if not found
    """
    conn = sqlite3.connect(DB_PATH)
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

    # Delete events first (foreign key constraint)
    cursor.execute("DELETE FROM events WHERE session_id = ?", (session_id,))

    # Delete session
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    conn.commit()
    conn.close()

    return {
        "session": True,
        "events_count": events_count
    }


def create_session(session_id: str, session_name: str, timestamp: str, project_dir: str = None, agent_name: str = None, parent_session_name: str = None) -> dict:
    """Create a new session with full metadata at creation time"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO sessions (session_id, session_name, status, created_at, project_dir, agent_name, parent_session_name)
        VALUES (?, ?, 'running', ?, ?, ?, ?)
    """, (session_id, session_name, timestamp, project_dir, agent_name, parent_session_name))
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


def get_session_by_name(session_name: str) -> dict | None:
    """Get a session by its session_name"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT * FROM sessions WHERE session_name = ?
    """, (session_name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_session_parent(session_id: str, parent_session_name: str) -> None:
    """Update the parent_session_name of a session.

    Used when resuming a session - the parent may be different from the original.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE sessions SET parent_session_name = ? WHERE session_id = ?",
        (parent_session_name, session_id)
    )
    conn.commit()
    conn.close()
