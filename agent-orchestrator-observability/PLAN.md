# MVP Observability Plan for Agent Orchestrator

**Date**: 2025-11-16
**Status**: Implementation Ready
**Estimated Time**: 90 minutes

## 1. Core Philosophy

**MVP Principles:**
- **KISS**: Keep It Simple Stupid - minimal viable features only
- **YAGNI**: You Aren't Gonna Need It - cut all "nice-to-have" features
- **ONE SESSION**: Must be fully implementable in a single work session
- **Backend + Frontend separation** for clarity
- **SQLite** for dead-simple persistence

## 2. What We're CUTTING from Full Architecture

**Features NOT in MVP:**
- ❌ PostToolUse hooks (add later if needed)
- ❌ SubagentStop hooks (add later if needed)
- ❌ Session stop hooks (sessions can just timeout)
- ❌ Complex UI components (filters, search, export)
- ❌ Error retry logic beyond basics
- ❌ Authentication/authorization
- ❌ Multiple WebSocket rooms
- ❌ Event batching/optimization
- ❌ Database migrations
- ❌ Comprehensive error handling
- ❌ Historical session replay
- ❌ Token usage tracking
- ❌ Auto-reconnection logic (page refresh works)

## 3. MVP Core Features (Absolute Minimum)

**What We're KEEPING:**
- ✅ SessionStart hook (know when agents start)
- ✅ PreToolUse hook (see what tools are being called)
- ✅ FastAPI backend with single WebSocket endpoint
- ✅ SQLite database (2 tables: sessions, events)
- ✅ React frontend (1 page, 2 components)
- ✅ Real-time updates via WebSocket
- ✅ List of active sessions
- ✅ Event stream for selected session

## 4. File Structure

```
observability/
├── PLAN.md                          # This document
├── README.md                        # Quick start guide
├── pyproject.toml                   # UV dependencies
│
├── backend/
│   ├── main.py                      # FastAPI app (80 lines)
│   ├── database.py                  # SQLite operations (100 lines)
│   └── models.py                    # Pydantic models (30 lines)
│
├── hooks/
│   ├── session_start_hook.py        # SessionStart hook (40 lines)
│   └── pre_tool_hook.py             # PreToolUse hook (40 lines)
│
└── frontend/
    ├── package.json                 # npm dependencies
    ├── vite.config.ts               # Vite config
    ├── index.html                   # HTML entry point
    └── src/
        ├── main.tsx                 # React entry point
        ├── App.tsx                  # Main app (150 lines)
        └── styles.css               # Minimal CSS
```

**Total Files: 13**
**Total Estimated Lines of Code: ~600**

## 5. Database Schema (Minimal)

```sql
-- Table 1: sessions
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    session_name TEXT NOT NULL,
    status TEXT NOT NULL,           -- 'running' | 'idle'
    created_at TEXT NOT NULL
);

-- Table 2: events
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,       -- 'session_start' | 'pre_tool'
    timestamp TEXT NOT NULL,
    tool_name TEXT,                 -- Only for pre_tool events
    tool_input TEXT,                -- JSON string
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Single index for performance
CREATE INDEX idx_events_session ON events(session_id, timestamp DESC);
```

**Total: 2 tables, 1 index**

## 6. Backend Components

### 6.1 Models (`backend/models.py`)

```python
from pydantic import BaseModel
from typing import Optional

class Event(BaseModel):
    event_type: str  # 'session_start' | 'pre_tool'
    session_id: str
    session_name: str
    timestamp: str
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
```

### 6.2 Database (`backend/database.py`)

Core functions:
- `init_db()` - Create tables and indexes
- `insert_session()` - Create/update session record
- `insert_event()` - Store event
- `get_sessions()` - List all sessions
- `get_events()` - Get events for a session

### 6.3 FastAPI App (`backend/main.py`)

**Endpoints:**
- `POST /events` - Receive events from hooks
- `GET /sessions` - List all sessions
- `GET /events/{session_id}` - Get events for session
- `WebSocket /ws` - Real-time updates

**Key Features:**
- In-memory WebSocket connection management
- Broadcast events to all connected clients
- CORS enabled for localhost:5173

## 7. Hook Scripts

### 7.1 SessionStart Hook (`hooks/session_start_hook.py`)

**Triggered**: When agent session starts
**Captures**:
- session_id
- session_name
- timestamp

**Action**: POST event to backend at `http://127.0.0.1:8765/events`

### 7.2 PreToolUse Hook (`hooks/pre_tool_hook.py`)

**Triggered**: Before any tool is executed
**Captures**:
- session_id
- tool_name
- tool_input (full parameters)
- timestamp

**Action**: POST event to backend at `http://127.0.0.1:8765/events`

**Note**: Hooks fail gracefully - if backend is down, they print warning but don't block agent execution.

## 8. Frontend Architecture

### 8.1 Tech Stack
- **React 18** with TypeScript
- **Vite** for build tooling
- **Vanilla CSS** (no Tailwind to keep it simple)
- **WebSocket API** for real-time updates

### 8.2 Main Component (`App.tsx`)

**State Management:**
```typescript
sessions: Session[]         // List of all sessions
selectedSession: string     // Currently selected session ID
events: { [id]: Event[] }   // Events grouped by session
connected: boolean          // WebSocket connection status
```

**WebSocket Logic:**
- Connect on mount
- Handle initial state
- Handle real-time events
- Update UI immediately

**UI Layout:**
```
┌─────────────┬──────────────────────┐
│  Sessions   │  Selected Session    │
│  Sidebar    │  Events Timeline     │
│             │                      │
│  ● Session1 │  [10:30] Started     │
│    Session2 │  [10:31] Tool: Read  │
│             │  [10:32] Tool: Bash  │
└─────────────┴──────────────────────┘
```

## 9. Implementation Steps

### Step 1: Backend Setup (20 min)
```bash
cd observability
# Create files: models.py, database.py, main.py
uv sync
uv run backend/main.py  # Test
```

### Step 2: Hook Setup (15 min)
```bash
# Create files: session_start_hook.py, pre_tool_hook.py
chmod +x hooks/*.py
# Test manually with curl
```

### Step 3: Frontend Setup (25 min)
```bash
cd frontend
npm install
# Create files: App.tsx, main.tsx, styles.css, etc.
npm run dev  # Test
```

### Step 4: Hook Configuration (10 min)
Add to `.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "uv run /ABSOLUTE/PATH/observability/hooks/session_start_hook.py",
        "timeout": 2000
      }]
    }],
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "uv run /ABSOLUTE/PATH/observability/hooks/pre_tool_hook.py",
        "timeout": 2000
      }]
    }]
  }
}
```

### Step 5: Integration Testing (10 min)
1. Start backend
2. Start frontend
3. Start test agent session
4. Verify real-time updates
5. Test with multiple sessions

### Step 6: Documentation (10 min)
Create README.md with quick start guide

**Total Time: ~90 minutes**

## 10. Success Criteria

The MVP is successful if:

1. ✅ Backend starts without errors
2. ✅ Frontend loads in browser
3. ✅ WebSocket connects successfully
4. ✅ Starting an agent session shows in the session list
5. ✅ Tool calls appear in real-time
6. ✅ Can switch between different agent sessions
7. ✅ Events persist in SQLite database
8. ✅ Page refresh loads historical events
9. ✅ Works with 2-3 concurrent agents

## 11. Known Limitations (Acceptable for MVP)

- No session stop detection (sessions stay "running")
- No tool result/output display (only inputs)
- No error handling UI (errors just don't show up)
- No reconnection logic (refresh page)
- No session filtering/search
- No event export
- No authentication
- No configuration UI
- Hooks require absolute paths
- Only works on localhost

## 12. Future Enhancements (Post-MVP)

**Phase 2 (Next Session):**
- Add PostToolUse hook for results
- Add session stop detection
- Add basic error display
- Auto-reconnection logic

**Phase 3 (Later):**
- Session filtering/search
- Event export (JSON/CSV)
- Tool result visualization
- Performance metrics

**Phase 4 (Advanced):**
- Agent control features
- Multi-user support
- Historical session replay
- Token usage tracking

## 13. Quick Start Commands

```bash
# Terminal 1: Backend
cd observability
uv run backend/main.py

# Terminal 2: Frontend
cd observability/frontend
npm run dev

# Terminal 3: Agent
# (Configure hooks in .claude/settings.json first)
# Then use your normal agent commands
```

## 14. Troubleshooting

**Problem: Hooks not firing**
- Check absolute paths in settings.json
- Verify `uv` is in PATH
- Test hook manually: `echo '{"session_id":"test"}' | uv run hooks/session_start_hook.py`

**Problem: WebSocket won't connect**
- Verify backend is running on port 8765
- Check browser console for errors
- Ensure CORS is configured correctly

**Problem: No events showing**
- Check backend logs for hook POST requests
- Verify database file exists: `.agent-orchestrator/observability.db`
- Use SQLite browser to inspect database

---

## Summary

This MVP plan focuses on the absolute minimum to demonstrate real-time observability:

- **2 hooks** (SessionStart, PreToolUse)
- **2 database tables** (sessions, events)
- **3 backend files** (main.py, database.py, models.py)
- **1 frontend component** (App.tsx)
- **~600 total lines of code**
- **~90 minutes to implement**

By cutting all non-essential features and focusing on core functionality, this can be built in a single session and immediately provide value for monitoring agent activity.
