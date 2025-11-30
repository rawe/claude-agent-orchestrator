# Agent Orchestrator Observability Architecture

**Date**: 2025-11-16
**Author**: Architecture Design
**Status**: Recommendation

## Executive Summary

This document outlines the recommended architecture for adding real-time observability to the Agent Orchestrator Framework. The solution leverages **hook-based event streaming** combined with a **Python/FastAPI backend** and **WebSocket-based web UI** to provide live monitoring of 5-20 concurrent agent sessions.

**Key Design Decisions:**
- ✅ **Hook-based** event collection (more reliable than file watching)
- ✅ **FastAPI + WebSockets** for real-time communication
- ✅ **SQLite** for local storage and indexing
- ✅ **React-based** web UI with live updates
- ✅ **View-only** interface (control via hooks as future enhancement)

---

## 1. Requirements Summary

Based on user input:

| Requirement | Specification |
|------------|---------------|
| **Detail Level** | Full conversation messages, lifecycle events, all tool calls |
| **Concurrency** | 5-20 concurrent agents (medium scale) |
| **Mode** | Real-time monitoring during execution |
| **Control** | View-only (future: agent steering via hooks) |
| **Tech Stack** | Python + UV for backend, efficient real-time updates |

---

## 2. Architecture Overview

### 2.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Orchestrator                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  Agent 1   │  │  Agent 2   │  │  Agent N   │                │
│  │ (Claude    │  │ (Claude    │  │ (Claude    │                │
│  │  Session)  │  │  Session)  │  │  Session)  │                │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                │
│        │               │               │                         │
│        │ Hooks         │ Hooks         │ Hooks                  │
│        └───────────────┴───────────────┘                        │
│                        │                                         │
└────────────────────────┼─────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   Observability Hook Handler  │
         │   (Python script per hook)    │
         └──────────────┬────────────────┘
                        │
                        │ HTTP POST (Events)
                        ▼
         ┌───────────────────────────────┐
         │   Observability Backend       │
         │   (FastAPI + WebSockets)      │
         │                               │
         │   ┌─────────────┐             │
         │   │   SQLite    │             │
         │   │  Database   │             │
         │   └─────────────┘             │
         └──────────────┬────────────────┘
                        │
                        │ WebSocket (SSE alternative)
                        ▼
         ┌───────────────────────────────┐
         │      Web UI (React)           │
         │                               │
         │  ┌─────────────────────────┐  │
         │  │  Agent List View        │  │
         │  ├─────────────────────────┤  │
         │  │  Conversation Timeline  │  │
         │  ├─────────────────────────┤  │
         │  │  Tool Call Details      │  │
         │  └─────────────────────────┘  │
         └───────────────────────────────┘
```

---

## 3. Detailed Component Design

### 3.1 Hook Integration Layer

**Purpose**: Capture events from running agent sessions and forward to backend

#### Hook Configuration

Add to `.claude/settings.json` (or agent-specific settings):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run observability/hooks/session_start_hook.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "uv run observability/hooks/pre_tool_hook.py",
            "timeout": 3000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "uv run observability/hooks/post_tool_hook.py",
            "timeout": 3000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run observability/hooks/session_stop_hook.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run observability/hooks/subagent_stop_hook.py",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

#### Hook Scripts Structure

**File**: `observability/hooks/session_start_hook.py`

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///

import sys
import json
import httpx
import os

def main():
    # Read hook input from stdin
    hook_input = json.load(sys.stdin)

    # Extract relevant data
    event = {
        "event_type": "session_start",
        "session_id": hook_input.get("session_id"),
        "timestamp": hook_input.get("timestamp"),
        "cwd": hook_input.get("cwd"),
        "transcript_path": hook_input.get("transcript_path"),
        # Extract session name from environment or session metadata
        "session_name": os.environ.get("AGENT_SESSION_NAME", "unknown"),
    }

    # Send to observability backend
    backend_url = os.environ.get(
        "OBSERVABILITY_BACKEND_URL",
        "http://localhost:8765/events"
    )

    try:
        httpx.post(backend_url, json=event, timeout=2.0)
    except Exception as e:
        # Don't fail the hook if backend is down
        print(f"Warning: Failed to send event to observability backend: {e}",
              file=sys.stderr)

    # Always succeed to not block agent execution
    sys.exit(0)

if __name__ == "__main__":
    main()
```

**Similar structure for**:
- `pre_tool_hook.py` - captures tool_name, tool_input
- `post_tool_hook.py` - captures tool_result, execution time
- `session_stop_hook.py` - captures final state, result

#### Event Payload Schema

```json
{
  "event_type": "session_start|pre_tool|post_tool|session_stop|subagent_stop",
  "session_id": "abc-123-def",
  "session_name": "my-researcher",
  "timestamp": "2025-11-16T10:30:00Z",
  "data": {
    // Event-specific data
    "tool_name": "Read",
    "tool_input": {"file_path": "/path/to/file.py"},
    "tool_result": "...",
    "error": null
  }
}
```

---

### 3.2 Observability Backend

**Technology Stack**:
- **FastAPI**: Modern async Python web framework
- **WebSockets**: Real-time bidirectional communication
- **SQLite**: Lightweight local storage for indexing and history
- **UV**: Dependency management

#### Directory Structure

```
observability/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── models.py               # Pydantic models for events
│   ├── database.py             # SQLite operations
│   ├── websocket_manager.py    # WebSocket connection management
│   ├── event_processor.py      # Event ingestion and processing
│   └── api/
│       ├── events.py           # POST /events endpoint
│       ├── sessions.py         # GET /sessions endpoint
│       └── websocket.py        # WebSocket endpoint
├── hooks/
│   ├── session_start_hook.py
│   ├── pre_tool_hook.py
│   ├── post_tool_hook.py
│   └── session_stop_hook.py
├── pyproject.toml              # UV project configuration
└── README.md
```

#### Core Backend Implementation

**File**: `observability/backend/main.py`

```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from database import init_db
from websocket_manager import WebSocketManager
from api import events, sessions, websocket as ws_router

# Initialize WebSocket manager (singleton)
ws_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    await ws_manager.disconnect_all()

app = FastAPI(
    title="Agent Orchestrator Observability",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(ws_router.router, prefix="/ws")

# Expose ws_manager to routers
app.state.ws_manager = ws_manager

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8765,
        reload=True,
        log_level="info"
    )
```

**File**: `observability/backend/websocket_manager.py`

```python
from fastapi import WebSocket
from typing import Set
import json
import asyncio

class WebSocketManager:
    """Manages WebSocket connections and broadcasts events"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        if not self.active_connections:
            return

        message_str = json.dumps(message)
        disconnected = set()

        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_str)
                except Exception:
                    disconnected.add(connection)

            # Remove disconnected clients
            self.active_connections -= disconnected

    async def disconnect_all(self):
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.close()
                except Exception:
                    pass
            self.active_connections.clear()
```

**File**: `observability/backend/database.py`

```python
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
import json
from datetime import datetime

DB_PATH = Path(".agent-orchestrator/observability.db")

def init_db():
    """Initialize SQLite database with schema"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            session_name TEXT NOT NULL,
            status TEXT NOT NULL,  -- 'running', 'finished', 'error'
            created_at TEXT NOT NULL,
            finished_at TEXT,
            cwd TEXT,
            transcript_path TEXT
        )
    """)

    # Events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            data TEXT NOT NULL,  -- JSON blob
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)

    # Indexes for performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_session
        ON events(session_id, timestamp)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_status
        ON sessions(status)
    """)

    conn.commit()
    conn.close()

def insert_session(session_id: str, session_name: str, **kwargs):
    """Create or update session record"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO sessions
        (session_id, session_name, status, created_at, cwd, transcript_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        session_name,
        kwargs.get('status', 'running'),
        kwargs.get('created_at', datetime.utcnow().isoformat()),
        kwargs.get('cwd'),
        kwargs.get('transcript_path')
    ))

    conn.commit()
    conn.close()

def update_session_status(session_id: str, status: str):
    """Update session status"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    finished_at = datetime.utcnow().isoformat() if status == 'finished' else None

    cursor.execute("""
        UPDATE sessions
        SET status = ?, finished_at = ?
        WHERE session_id = ?
    """, (status, finished_at, session_id))

    conn.commit()
    conn.close()

def insert_event(session_id: str, event_type: str, data: dict):
    """Insert event record"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO events (session_id, event_type, timestamp, data)
        VALUES (?, ?, ?, ?)
    """, (
        session_id,
        event_type,
        datetime.utcnow().isoformat(),
        json.dumps(data)
    ))

    conn.commit()
    conn.close()

def get_active_sessions() -> List[Dict]:
    """Get all running sessions"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM sessions
        WHERE status = 'running'
        ORDER BY created_at DESC
    """)

    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sessions

def get_session_events(session_id: str, limit: int = 100) -> List[Dict]:
    """Get events for a session"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM events
        WHERE session_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (session_id, limit))

    events = []
    for row in cursor.fetchall():
        event = dict(row)
        event['data'] = json.loads(event['data'])
        events.append(event)

    conn.close()
    return events
```

**File**: `observability/backend/api/events.py`

```python
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from database import insert_session, insert_event, update_session_status

router = APIRouter()
logger = logging.getLogger(__name__)

class EventPayload(BaseModel):
    event_type: str
    session_id: str
    session_name: Optional[str] = None
    timestamp: str
    data: Optional[Dict[str, Any]] = {}

@router.post("/events")
async def receive_event(event: EventPayload, request: Request):
    """
    Receive events from hook scripts and broadcast to WebSocket clients
    """
    try:
        # Process different event types
        if event.event_type == "session_start":
            insert_session(
                session_id=event.session_id,
                session_name=event.session_name or "unknown",
                status="running",
                created_at=event.timestamp,
                **event.data
            )

        elif event.event_type == "session_stop":
            update_session_status(event.session_id, "finished")

        # Store event in database
        insert_event(
            session_id=event.session_id,
            event_type=event.event_type,
            data=event.data
        )

        # Broadcast to WebSocket clients
        ws_manager = request.app.state.ws_manager
        await ws_manager.broadcast({
            "type": "event",
            "payload": event.dict()
        })

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing event: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**File**: `observability/backend/api/sessions.py`

```python
from fastapi import APIRouter
from database import get_active_sessions, get_session_events

router = APIRouter()

@router.get("/sessions")
async def list_sessions():
    """Get list of all sessions"""
    sessions = get_active_sessions()
    return {"sessions": sessions}

@router.get("/sessions/{session_id}/events")
async def get_events(session_id: str, limit: int = 100):
    """Get events for a specific session"""
    events = get_session_events(session_id, limit)
    return {"events": events}
```

**File**: `observability/backend/api/websocket.py`

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from database import get_active_sessions
import json

router = APIRouter()

@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket, request: Request):
    """WebSocket endpoint for real-time updates"""
    ws_manager = request.app.state.ws_manager

    await ws_manager.connect(websocket)

    try:
        # Send initial state
        sessions = get_active_sessions()
        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "sessions": sessions
        }))

        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()
            # Client messages (if needed for future features)
            # For now, just echo or ignore

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
```

#### UV Project Configuration

**File**: `observability/pyproject.toml`

```toml
[project]
name = "agent-orchestrator-observability"
version = "1.0.0"
description = "Real-time observability for Agent Orchestrator"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "websockets>=12.0",
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

### 3.3 Web UI (Frontend)

**Technology Stack**:
- **React 18** with TypeScript
- **Vite** for build tooling
- **TailwindCSS** for styling
- **WebSocket API** for real-time updates

#### Directory Structure

```
observability/frontend/
├── src/
│   ├── App.tsx                 # Main app component
│   ├── hooks/
│   │   └── useWebSocket.ts     # WebSocket connection hook
│   ├── components/
│   │   ├── SessionList.tsx     # Left sidebar with agent list
│   │   ├── ConversationView.tsx # Main conversation timeline
│   │   ├── ToolCallCard.tsx    # Individual tool call display
│   │   └── StatusBar.tsx       # Connection status, stats
│   ├── types/
│   │   └── events.ts           # TypeScript types for events
│   └── main.tsx
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

#### Key Components

**File**: `observability/frontend/src/hooks/useWebSocket.ts`

```typescript
import { useEffect, useState, useCallback } from 'react';

interface Event {
  event_type: string;
  session_id: string;
  session_name?: string;
  timestamp: string;
  data: any;
}

interface Session {
  session_id: string;
  session_name: string;
  status: string;
  created_at: string;
}

export function useWebSocket(url: string) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [events, setEvents] = useState<Record<string, Event[]>>({});
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };

    ws.onmessage = (message) => {
      const data = JSON.parse(message.data);

      if (data.type === 'initial_state') {
        setSessions(data.sessions);
      } else if (data.type === 'event') {
        const event = data.payload as Event;

        // Update events for session
        setEvents((prev) => ({
          ...prev,
          [event.session_id]: [
            ...(prev[event.session_id] || []),
            event
          ]
        }));

        // Update session list if new session
        if (event.event_type === 'session_start') {
          setSessions((prev) => {
            const exists = prev.some(s => s.session_id === event.session_id);
            if (exists) return prev;

            return [...prev, {
              session_id: event.session_id,
              session_name: event.session_name || 'unknown',
              status: 'running',
              created_at: event.timestamp
            }];
          });
        }

        // Update status on stop
        if (event.event_type === 'session_stop') {
          setSessions((prev) =>
            prev.map(s =>
              s.session_id === event.session_id
                ? { ...s, status: 'finished' }
                : s
            )
          );
        }
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  return { sessions, events, connected };
}
```

**File**: `observability/frontend/src/components/ConversationView.tsx`

```typescript
import React from 'react';
import { ToolCallCard } from './ToolCallCard';

interface Event {
  event_type: string;
  timestamp: string;
  data: any;
}

interface Props {
  sessionId: string;
  events: Event[];
}

export function ConversationView({ sessionId, events }: Props) {
  if (!events || events.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        No events yet. Waiting for agent activity...
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-6 overflow-y-auto">
      {events.map((event, index) => (
        <div key={index} className="border-l-4 border-blue-500 pl-4">
          <div className="text-xs text-gray-500 mb-1">
            {new Date(event.timestamp).toLocaleTimeString()}
          </div>

          {event.event_type === 'pre_tool' && (
            <ToolCallCard
              toolName={event.data.tool_name}
              input={event.data.tool_input}
            />
          )}

          {event.event_type === 'post_tool' && (
            <div className="bg-green-50 p-3 rounded">
              <div className="font-semibold text-green-800">
                Tool Completed: {event.data.tool_name}
              </div>
              {event.data.error && (
                <div className="text-red-600 mt-2">
                  Error: {event.data.error}
                </div>
              )}
            </div>
          )}

          {event.event_type === 'session_stop' && (
            <div className="bg-gray-100 p-3 rounded">
              <div className="font-semibold">Session Finished</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## 4. Alternative Approaches Considered

### 4.1 File System Watching (Rejected)

**Approach**: Use `watchdog` or `inotify` to monitor `.jsonl` file changes

**Pros**:
- Simple to implement
- No hook configuration needed
- Works independently of Claude Code

**Cons**:
- ❌ Race conditions with rapid updates
- ❌ Inefficient for 5-20 agents (high I/O)
- ❌ Missed events if file updates are batched
- ❌ No structured event data (requires parsing)
- ❌ Latency in detecting changes

**Verdict**: Not suitable for real-time monitoring of multiple agents

### 4.2 Polling JSONL Files (Rejected)

**Approach**: Periodically read `.jsonl` files and parse for new messages

**Pros**:
- Simple implementation
- No hooks needed

**Cons**:
- ❌ High I/O overhead for 5-20 files
- ❌ Polling delay reduces real-time feel
- ❌ Inefficient parsing of large files
- ❌ No lifecycle events (start/stop)

**Verdict**: Not suitable for real-time requirements

### 4.3 Server-Sent Events (SSE) vs WebSockets

**SSE Approach**: One-way server → client streaming

**Pros**:
- ✅ Simpler than WebSockets
- ✅ Auto-reconnection built-in
- ✅ HTTP-based (easier proxying)

**Cons**:
- ❌ One-way only (but sufficient for view-only)
- ❌ Less efficient for high-frequency updates

**WebSocket Approach**: Bidirectional communication

**Pros**:
- ✅ Better for future control features
- ✅ More efficient for frequent updates
- ✅ Standard in modern web apps

**Cons**:
- ❌ Slightly more complex

**Verdict**: WebSockets chosen for scalability and future control features

---

## 5. Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Set up FastAPI backend with UV
- [ ] Implement SQLite database schema
- [ ] Create basic WebSocket manager
- [ ] Build hook scripts for SessionStart/Stop
- [ ] Test with 1-2 agents

### Phase 2: Event Streaming (Week 2)
- [ ] Implement PreToolUse/PostToolUse hooks
- [ ] Add event ingestion API
- [ ] Build WebSocket broadcasting
- [ ] Test with 5 concurrent agents

### Phase 3: Web UI (Week 3)
- [ ] React app scaffolding with Vite
- [ ] Session list component
- [ ] Conversation view with timeline
- [ ] Tool call visualization
- [ ] WebSocket integration

### Phase 4: Polish & Testing (Week 4)
- [ ] Error handling and reconnection logic
- [ ] Performance testing with 20 agents
- [ ] UI/UX improvements
- [ ] Documentation

---

## 6. Configuration Integration

### 6.1 Automatic Hook Setup

Add to `ao-new` and `ao-resume` commands:

```python
def setup_observability_hooks(sessions_dir: Path):
    """Inject observability hooks into agent settings"""

    # Set environment variable for hooks
    os.environ["AGENT_SESSION_NAME"] = session_name
    os.environ["OBSERVABILITY_BACKEND_URL"] = "http://localhost:8765/api/events"

    # Hooks will be loaded from .claude/settings.json
    # No need to inject per-session since hooks are global
```

### 6.2 Starting the Backend

**File**: `observability/start.sh`

```bash
#!/bin/bash
# Start observability backend

cd "$(dirname "$0")/backend"

# Start FastAPI server
uv run uvicorn main:app --host 127.0.0.1 --port 8765 --reload
```

---

## 7. Future Enhancements

### 7.1 Agent Control (Planned)

Using hooks to implement steering:

- **Stop Agent**: Use `Stop` hook with `{"continue": false}` response
- **Inject Context**: Use `UserPromptSubmit` hook with `additionalContext`
- **Pause/Resume**: Modify hook behavior dynamically

### 7.2 Advanced Features

- **Token Usage Tracking**: Parse SDK messages for cost analysis
- **Conversation Replay**: Load historical sessions from JSONL
- **Multi-User Support**: WebSocket rooms per user
- **Agent Templates**: Launch agents from UI (future control)
- **Search & Filter**: Full-text search across conversations
- **Export**: Download session transcripts

---

## 8. Performance Considerations

### 8.1 Scalability

For 5-20 agents:
- **WebSocket connections**: Minimal overhead (<1MB per connection)
- **SQLite**: Can handle 100+ writes/sec easily
- **Hook overhead**: ~10-50ms per event (non-blocking)

### 8.2 Optimization Strategies

- **Batch events**: Group tool calls within 100ms window
- **Database indexing**: Pre-indexed on session_id + timestamp
- **Event pruning**: Auto-archive events older than 7 days
- **WebSocket compression**: Enable for large payloads

---

## 9. Security Considerations

### 9.1 Local-Only Access

- Backend binds to `127.0.0.1` (localhost only)
- No authentication needed for local development
- CORS restricted to `localhost:3000`

### 9.2 Future: Production Deployment

If deploying remotely:
- Add JWT authentication for WebSocket
- TLS/SSL for encrypted communication
- API key for hook → backend communication

---

## 10. Quick Start Guide

### 10.1 Installation

```bash
# 1. Install observability backend
cd observability
uv sync

# 2. Install frontend dependencies
cd frontend
npm install

# 3. Configure hooks in .claude/settings.json
# (Copy configuration from Section 3.1)
```

### 10.2 Running

```bash
# Terminal 1: Start backend
cd observability/backend
uv run uvicorn main:app --reload

# Terminal 2: Start frontend
cd observability/frontend
npm run dev

# Terminal 3: Run agent orchestrator
uv run commands/ao-new test-agent -p "Your task"

# Open browser to http://localhost:3000
```

---

## 11. Conclusion

### Recommended Approach: Hook-Based Real-Time Observability

**Why this architecture?**

1. ✅ **Reliable**: Hooks provide precise, structured events
2. ✅ **Efficient**: No polling or file watching overhead
3. ✅ **Scalable**: Handles 5-20 agents with minimal latency
4. ✅ **Future-Proof**: WebSockets enable future control features
5. ✅ **Python/UV Native**: Matches your existing tech stack
6. ✅ **Maintainable**: Clean separation of concerns

**Key Benefits**:
- Real-time updates with <100ms latency
- Full conversation visibility (messages, tools, lifecycle)
- Minimal impact on agent performance
- Easy to extend for future features (control, analytics)

**Next Steps**:
1. Review this architecture document
2. Confirm technical decisions align with requirements
3. Begin Phase 1 implementation (backend + basic hooks)
4. Iterate based on feedback from real usage

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Questions or Feedback**: Please provide input before implementation begins
