# Frontend → Backend API

Interface between the web UI and the observability backend.

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
