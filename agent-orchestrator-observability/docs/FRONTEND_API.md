# Frontend API

API for reading data from the observability backend.

**Used by:**
- Web UI (React frontend)
- Any client that needs to display observability data

**For writing/updating data** (used by hooks and Python commands), see [BACKEND_API.md](BACKEND_API.md).

## WebSocket

**URL:** `ws://127.0.0.1:8765/ws`
**Protocol:** WebSocket

### Server → Client Messages

**Initial State:**
```json
{
  "type": "init",
  "sessions": [Session, ...]
}
```
See [Session model](DATA_MODELS.md#session) in DATA_MODELS.md

**Real-time Event:**
```json
{
  "type": "event",
  "data": Event
}
```
See [Event model](DATA_MODELS.md#event) in DATA_MODELS.md

**Session Update:**
```json
{
  "type": "session_updated",
  "session": Session
}
```
Sent when session metadata (name or project_dir) is updated via the PATCH endpoint.

**Event Types Received:**
- `session_start` - When an agent session starts
- `pre_tool` - Before a tool executes (shows input parameters)
- `post_tool` - After a tool executes (shows input + output)
- `session_stop` - When a session ends
- `message` - Agent or user messages (extracted from transcript)

See [Event Types](DATA_MODELS.md#event-types) for detailed schemas.

### Connection Flow

1. Client connects to WebSocket
2. Server sends initial state with all sessions
3. Server broadcasts new events as they arrive
4. Client updates UI in real-time

## REST Endpoints

### Get All Sessions

**URL:** `http://127.0.0.1:8765/sessions`
**Method:** `GET`

**Response:**
```json
{
  "sessions": [Session, ...]
}
```

### Get Session Events

**URL:** `http://127.0.0.1:8765/events/{session_id}`
**Method:** `GET`
**Query Params:** `limit` (default: 100)

**Response:**
```json
{
  "events": [Event, ...]
}
```

Events are returned in ascending timestamp order (oldest first).

---

**Note:** To update session metadata, see `PATCH /sessions/{session_id}/metadata` in [BACKEND_API.md](BACKEND_API.md).
