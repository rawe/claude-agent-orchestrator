# Agent Runtime API

API documentation for the Agent Runtime server.

**Base URL:** `http://127.0.0.1:8765`

---

## WebSocket

Real-time updates for sessions and events.

**URL:** `ws://127.0.0.1:8765/ws`

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

**Session Created:**
```json
{
  "type": "session_created",
  "session": Session
}
```
Sent when a new session is created via POST /sessions.

**Session Update:**
```json
{
  "type": "session_updated",
  "session": Session
}
```
Sent when session metadata is updated or session status changes.

**Session Deleted:**
```json
{
  "type": "session_deleted",
  "session_id": "abc-123"
}
```
Sent when a session is deleted via DELETE endpoint.

### Event Types

- `session_start` - When an agent session starts
- `pre_tool` - Before a tool executes (shows input parameters)
- `post_tool` - After a tool executes (shows input + output)
- `session_stop` - When a session ends
- `message` - Agent or user messages

See [Event Types](DATA_MODELS.md#event-types) for detailed schemas.

### Connection Flow

1. Client connects to WebSocket
2. Server sends initial state with all sessions
3. Server broadcasts new events as they arrive
4. Client updates UI in real-time

---

## REST Endpoints

### Sessions

#### GET /sessions

Get all sessions.

**Response:**
```json
{
  "sessions": [Session, ...]
}
```

#### POST /sessions

Create a new session with full metadata.

**Request Body:**
```json
{
  "session_id": "abc-123",
  "session_name": "My Session",
  "project_dir": "/path/to/project",  // optional
  "agent_name": "researcher"          // optional
}
```

**Response:**
```json
{
  "ok": true,
  "session": Session
}
```

**Error (Session Exists):**
```json
{
  "detail": "Session already exists"
}
```
**Status Code:** `409 Conflict`

#### GET /sessions/{session_id}

Get a single session by ID.

**Response:**
```json
{
  "session": Session
}
```

**Error:** `404 Not Found` if session doesn't exist.

#### GET /sessions/{session_id}/status

Get session status.

**Response:**
```json
{
  "status": "running" | "finished" | "not_existent"
}
```

#### GET /sessions/{session_id}/result

Get the result text from the last assistant message.

**Response:**
```json
{
  "result": "The assistant's final response text..."
}
```

**Errors:**
- `404 Not Found` - Session doesn't exist
- `400 Bad Request` - Session not finished

#### PATCH /sessions/{session_id}/metadata

Update session metadata.

**Request Body:**
```json
{
  "session_name": "New Name",      // optional
  "project_dir": "/new/path",      // optional
  "agent_name": "new-agent"        // optional
}
```

At least one field must be provided.

**Response:**
```json
{
  "ok": true,
  "session": Session
}
```

**Notes:**
- Updates are broadcast to WebSocket clients via `session_updated` message

#### DELETE /sessions/{session_id}

Delete a session and all its associated events.

**Response:**
```json
{
  "ok": true,
  "session_id": "abc-123",
  "deleted": {
    "session": true,
    "events_count": 42
  }
}
```

**Notes:**
- Permanently deletes session and all events (cannot be undone)
- Broadcasts `session_deleted` to WebSocket clients

---

### Events

#### GET /sessions/{session_id}/events

Get events for a specific session.

**Response:**
```json
{
  "events": [Event, ...]
}
```

Events are returned in ascending timestamp order (oldest first).

#### GET /events/{session_id}

Legacy endpoint. Same as GET /sessions/{session_id}/events.

#### POST /sessions/{session_id}/events

Add an event to a session.

**Request Body:**
See [Event model](DATA_MODELS.md#event)

**Response:**
```json
{
  "ok": true
}
```

**Notes:**
- Session must exist (created via POST /sessions first)
- If event_type is `session_stop`, session status is updated to `finished`

#### POST /events

Legacy endpoint for sending events.

**Request Body:**
See [Event model](DATA_MODELS.md#event)

**Response:**
```json
{
  "ok": true
}
```

**Notes:**
- Creates session if `session_start` event
- Updates status to `finished` if `session_stop` event
- Prefer POST /sessions + POST /sessions/{id}/events for new integrations

---

## Configuration

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` | `http://127.0.0.1:8765` | Agent Runtime URL |
| `DEBUG_LOGGING` | `false` | Enable verbose logging |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins |

---

## Error Handling

All endpoints return JSON error responses:

```json
{
  "detail": "Error message here"
}
```

Common status codes:
- `200 OK` - Success
- `400 Bad Request` - Invalid request
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists
