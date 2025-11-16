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
            created_at TEXT NOT NULL
        )
    """)

    # Events table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            tool_name TEXT,
            tool_input TEXT,
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
    conn.execute("""
        INSERT OR REPLACE INTO sessions
        (session_id, session_name, status, created_at)
        VALUES (?, ?, 'running', ?)
    """, (session_id, session_name, timestamp))
    conn.commit()
    conn.close()

def insert_event(event):
    """Insert event"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO events
        (session_id, event_type, timestamp, tool_name, tool_input)
        VALUES (?, ?, ?, ?, ?)
    """, (
        event.session_id,
        event.event_type,
        event.timestamp,
        event.tool_name,
        json.dumps(event.tool_input) if event.tool_input else None
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
        events.append(event)

    conn.close()
    return events
