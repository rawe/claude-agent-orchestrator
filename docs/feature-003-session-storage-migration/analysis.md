# Session Storage Migration Analysis

## Goal

Migrate from file-based session storage (.jsonl/.meta.json) to database-backed storage via **Agent Session Manager** service. Files become backup only.

## Naming Decisions

| Concept | Name | Rationale |
|---------|------|-----------|
| Service | Agent Session Manager | "Session" alone too generic, "Agent" distinguishes from other sessions |
| API Client | `session_client.py` | Clean, no reference to deprecated naming |
| API paths | `/sessions/*` | Unified resource-centric design |
| Server folder | `agent-orchestrator-observability` | Keep current folder, rename later |

**Configuration (breaking change):**

| Remove | Replace with |
|--------|--------------|
| `AGENT_ORCHESTRATOR_OBSERVABILITY_URL` | `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` |
| `AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED` | *(remove - no longer optional)* |

```python
# config.py - new
ENV_SESSION_MANAGER_URL = "AGENT_ORCHESTRATOR_SESSION_MANAGER_URL"
DEFAULT_SESSION_MANAGER_URL = "http://127.0.0.1:8765"
```

Agent Session Manager is now **required** - no enable/disable toggle.

**Important**: Avoid "observability" in any new code, API endpoints, or client naming. This term will be deprecated.

## Current State

### File-Based System (to be deprecated as primary)
**Location:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/session.py`

**Files per session:**
- `{session_name}.meta.json` - Metadata
- `{session_name}.jsonl` - Event stream

### Database Backend (becomes primary)
**Location:** `agent-orchestrator-observability/backend/`

**Tables:**
- `sessions` - Session metadata and status
- `events` - All session events (tool calls, messages, results)

## API Design (Unified under /sessions)

### New Unified Endpoints

```
POST   /sessions                    Create new session
GET    /sessions                    List all sessions
GET    /sessions/{id}               Get session details
GET    /sessions/{id}/status        Get status (running/finished/not_existent)
GET    /sessions/{id}/result        Get final result (from events)
GET    /sessions/{id}/events        Get all events for session
POST   /sessions/{id}/events        Add event to session
PATCH  /sessions/{id}               Update session metadata
DELETE /sessions/{id}               Delete session and events
```

### Deprecated Endpoints

```
POST   /events                      → Remove session_start handling
                                    → Keep temporarily for session_stop until migrated
GET    /events/{session_id}         → Use GET /sessions/{id}/events
PATCH  /sessions/{id}/metadata      → Use PATCH /sessions/{id}
```

**Note:** `POST /events` with `event_type: session_start` will be **removed** entirely.
The session is now created via `POST /sessions` before any events are sent.

### WebSocket (unchanged)

```
WS     /ws                          Real-time updates (frontend uses this)
```

Frontend continues to use WebSocket exactly as before. No changes needed.

## No Redundancy Principle

**Single source of truth**: Database is the primary source.

**Data flow:**
1. Commands call session_client → API → Database
2. API broadcasts to WebSocket → Frontend
3. Files written as backup only (after API success)

**What NOT to duplicate:**
- Don't send same data to multiple endpoints
- Don't store same info in both session metadata and events
- Don't have separate "observability" and "session" API calls for same data

## Event Type Consolidation

**Current redundant flow:**
```
1. user_prompt_hook → POST /events {session_start} → creates session row (minimal)
2. claude_client.py → PATCH /sessions/{id}/metadata → adds project_dir, agent_name
3. events flow → POST /events
4. session_stop event → POST /events → updates status to 'finished'
```

**New clean flow:**
```
1. SystemMessage received → POST /sessions (full metadata) → creates session row
2. events flow → POST /sessions/{id}/events
3. session_stop event → POST /sessions/{id}/events → updates status to 'finished'
```

**Event type changes:**

| Event Type | Action | Rationale |
|------------|--------|-----------|
| `session_start` | **REMOVE** | Replaced by `POST /sessions` - no longer an "event" |
| `session_stop` | KEEP | Stores exit_code/reason, triggers status='finished' |
| `message` | KEEP | User and assistant messages |
| `pre_tool` | KEEP | Tool call start |
| `post_tool` | KEEP | Tool call result |

**`POST /sessions/{id}/events` special handling:**

When `event_type == 'session_stop'`:
1. Insert event into events table (preserves exit_code, reason)
2. Update session status to 'finished'
3. Broadcast to WebSocket

**Result extraction (`GET /sessions/{id}/result`):**

```sql
SELECT content FROM events
WHERE session_id = ? AND event_type = 'message' AND role = 'assistant'
ORDER BY timestamp DESC LIMIT 1
```
Returns `content[0].text` as the result string.

## Implementation Plan

### Phase 1: Extend Server API

**Add new endpoints to `main.py`:**
```python
POST   /sessions                      # Create session with full metadata
GET    /sessions/{session_id}         # Get single session
GET    /sessions/{session_id}/status  # Returns: running/finished/not_existent
GET    /sessions/{session_id}/result  # Extract from last assistant message
POST   /sessions/{session_id}/events  # Add event (replaces POST /events)
```

**`POST /sessions` request body:**
```json
{
  "session_id": "uuid-from-sdk",
  "session_name": "my-session",
  "project_dir": "/path/to/project",
  "agent_name": "researcher"  // optional
}
```

**`POST /sessions/{id}/events` behavior:**
- Validates session exists (returns 404 if not)
- Inserts event into events table
- If `event_type == 'session_stop'`: also updates session status to 'finished'
- Broadcasts to WebSocket

**Update `database.py`:**
- `create_session()` - Full metadata at creation (not from event)
- `get_session_by_id()` - Single session lookup
- `get_session_result()` - Extract from last assistant message event

**Schema changes:**
```sql
ALTER TABLE sessions ADD COLUMN last_resumed_at TEXT;
```

**Remove from `POST /events` handler:**
- Remove `session_start` special case (session creation moves to `POST /sessions`)
- Keep `session_stop` handling OR move to new endpoint

### Phase 2: Create Session Client

**Update `lib/config.py`:**
- Remove `ENV_OBSERVABILITY_ENABLED`, `ENV_OBSERVABILITY_URL`
- Add `ENV_SESSION_MANAGER_URL` with default `http://127.0.0.1:8765`
- Remove `observability_enabled` from `Config` dataclass
- Rename `observability_url` → `session_manager_url`

**Create `lib/session_client.py`:**
```python
class SessionClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def create_session(self, session_id, session_name, ...) -> Session
    def get_session(self, session_id) -> Session
    def get_status(self, session_id) -> str  # running/finished/not_existent
    def get_result(self, session_id) -> str
    def list_sessions() -> List[Session]
    def add_event(self, session_id, event) -> None
    def update_session(self, session_id, **kwargs) -> Session
    def delete_session(self, session_id) -> None
```

**Remove `lib/observability.py`** - replace with `session_client.py`.

### Phase 3: Migrate Commands

| Command | Current | New |
|---------|---------|-----|
| ao-new | `save_session_metadata()` | `client.create_session()` |
| ao-resume | `load_session_metadata()` | `client.get_session()` |
| ao-status | `get_session_status()` | `client.get_status()` |
| ao-get-result | `extract_result()` | `client.get_result()` |
| ao-list-sessions | `list_all_sessions()` | `client.list_sessions()` |
| ao-clean | file deletion | `client.delete_session()` |

### Phase 4: Event Capture

**Update `lib/claude_client.py`:**
- Remove `observability_enabled` parameter (always enabled)
- Rename `observability_url` → `session_manager_url`
- On `SystemMessage` received: call `client.create_session()` (not via hook)
- Remove `user_prompt_hook` session_start logic
- Use `SessionClient.add_event()` for all events

**New event flow in claude_client.py:**
```python
# 1. Start SDK session
async with ClaudeSDKClient(options) as client:
    await client.query(prompt)

    async for message in client.receive_response():
        # 2. On SystemMessage: create session
        if isinstance(message, SystemMessage) and message.subtype == 'init':
            session_id = message.data.get('session_id')
            session_client.create_session(
                session_id=session_id,
                session_name=session_name,
                project_dir=str(project_dir),
                agent_name=agent_name
            )

        # 3. On ResultMessage: send assistant message event
        if isinstance(message, ResultMessage):
            session_client.add_event(session_id, {
                "event_type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": message.result}]
            })

    # 4. After loop: send session_stop
    session_client.add_event(session_id, {
        "event_type": "session_stop",
        "exit_code": 0,
        "reason": "completed"
    })
```

**Events stored in database:**
- `message` (user) - from hook
- `post_tool` - from hook
- `message` (assistant) - from ResultMessage
- `session_stop` - triggers status='finished'

**NOT stored as event:**
- `session_start` - replaced by `POST /sessions`

## File Backup Strategy

Files are backup only, written after API success:

```python
# In commands:
try:
    client.create_session(...)  # Primary
    save_session_metadata(...)  # Backup
except APIError:
    save_session_metadata(...)  # Fallback to file-only mode
```

## YAGNI

**Not doing:**
- No authentication (yet)
- No session versioning
- No historical file migration
- No complex caching
- No server rename (just avoid new "observability" references)

## KISS

**Keep simple:**
- One client class for all operations
- Direct HTTP calls
- Graceful degradation to files
- Existing SQLite database

## Success Criteria

1. All `ao-*` commands use SessionClient as primary
2. No "observability" naming in new code (env vars, files, parameters)
3. `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` is the only config
4. Frontend WebSocket works unchanged
5. Files written as backup
6. No redundant API calls
7. Status/result from database, not file parsing
