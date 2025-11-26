# Phase 1: Backend API Extensions

## Overall Context

We are migrating the Agent Orchestrator from file-based session storage to database-backed storage via the **Agent Session Manager** service. The current server is in `agent-orchestrator-observability/backend/`. After this migration, all session operations go through the API; files become backup only.

**Key principle:** Avoid "observability" in any NEW code, endpoints, or naming.

## This Phase's Goal

Extend the backend API with new session management endpoints. This is the foundation that all other phases depend on.

## Prerequisites

None - this is the first phase.

## Reference

Read these sections in `analysis.md`:
- "API Design (Unified under /sessions)" - endpoint specifications
- "Event Type Consolidation" - how session_stop triggers status update
- "Phase 1: Extend Server API" - detailed requirements

## Tasks

### 1. Database Schema Update

**File:** `agent-orchestrator-observability/backend/database.py`

Add `last_resumed_at` column to sessions table in `init_db()`:
```sql
ALTER TABLE sessions ADD COLUMN last_resumed_at TEXT;
```

Add new functions:
- `create_session(session_id, session_name, project_dir, agent_name, timestamp)` - full metadata at creation
- `get_session_by_id(session_id)` - returns single session dict or None
- `get_session_result(session_id)` - extracts result from last assistant message event

### 2. Models Update

**File:** `agent-orchestrator-observability/backend/models.py`

Add Pydantic model for session creation:
```python
class SessionCreate(BaseModel):
    session_id: str
    session_name: str
    project_dir: Optional[str] = None
    agent_name: Optional[str] = None
```

### 3. New Endpoints

**File:** `agent-orchestrator-observability/backend/main.py`

Add these endpoints:

| Endpoint | Description |
|----------|-------------|
| `POST /sessions` | Create session with full metadata, returns session, broadcasts `session_created` |
| `GET /sessions/{session_id}` | Get single session details, returns 404 if not found |
| `GET /sessions/{session_id}/status` | Returns status string: "running", "finished", or "not_existent" |
| `GET /sessions/{session_id}/result` | Returns result text from last assistant message, 404 if not found/not finished |
| `POST /sessions/{session_id}/events` | Add event to session (must exist), handle session_stop special case |
| `GET /sessions/{session_id}/events` | Get events for session (move logic from `/events/{session_id}`) |

### 4. WebSocket Broadcasts

Ensure these broadcast to WebSocket clients:
- `POST /sessions` → broadcast `{"type": "session_created", "session": {...}}`
- `POST /sessions/{id}/events` → broadcast `{"type": "event", "data": {...}}`
- `session_stop` event → also broadcast `{"type": "session_updated", "session": {...}}`

### 5. Deprecation Notes

In `POST /events` handler, add comment that `session_start` handling will be removed. Do NOT remove yet - keep backward compatibility during migration.

## Success Criteria

1. `POST /sessions` creates session with all metadata in one call
2. `GET /sessions/{id}` returns single session
3. `GET /sessions/{id}/status` returns correct status
4. `GET /sessions/{id}/result` returns result from events
5. `POST /sessions/{id}/events` accepts events and handles `session_stop`
6. All new endpoints broadcast to WebSocket
7. Existing frontend still works (WebSocket unchanged)

## Verification

```bash
# Start server
cd agent-orchestrator-observability/backend
uv run python main.py

# Test new endpoints
curl -X POST http://localhost:8765/sessions \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-123", "session_name": "test", "project_dir": "/tmp"}'

curl http://localhost:8765/sessions/test-123
curl http://localhost:8765/sessions/test-123/status

curl -X POST http://localhost:8765/sessions/test-123/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "message", "session_id": "test-123", "session_name": "test", "timestamp": "2024-01-01T00:00:00Z", "role": "assistant", "content": [{"type": "text", "text": "Hello"}]}'

curl http://localhost:8765/sessions/test-123/result
```

## Guidelines

- **Follow the instructions above** - do not add features beyond what is specified
- **Embrace KISS** - keep implementations simple and straightforward
- **Embrace YAGNI** - do not build for hypothetical future requirements
- **Ask if there is any confusion** before proceeding with implementation
