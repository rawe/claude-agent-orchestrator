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
  "project_dir": "/path/to/project",    // optional
  "agent_name": "researcher",           // optional
  "parent_session_name": "parent-task"  // optional
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

#### POST /sessions/{session_id}/stop

Stop a running session by signaling its launcher.

Finds the active job for this session and queues a stop command.

**Response (Success):**
```json
{
  "ok": true,
  "session_id": "abc-123",
  "job_id": "job_xyz789",
  "session_name": "my-task",
  "status": "stopping"
}
```

**Error Responses:**
- `404 Not Found` - Session not found
- `400 Bad Request` - Session is not running
- `404 Not Found` - No active job found for session
- `400 Bad Request` - Job not claimed by any launcher / Job cannot be stopped

**Notes:**
- Convenience endpoint that looks up the job by session
- For direct job control, use `POST /jobs/{job_id}/stop` instead
- Queues a stop command for the launcher that will terminate the session's process
- The launcher receives the stop command immediately (wakes up from long-poll)
- Launcher sends SIGTERM first, then SIGKILL after 5 seconds if process doesn't respond

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

### Agents API

Manage agent blueprints (templates for creating agents).

#### GET /agents

List all agent blueprints.

**Response:**
```json
[
  {
    "name": "researcher",
    "description": "Research agent with web search",
    "system_prompt": "You are a research assistant...",
    "mcp_servers": {
      "brave-search": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "env": { "BRAVE_API_KEY": "..." }
      }
    },
    "skills": ["research", "web-search"],
    "status": "active",
    "created_at": "2025-12-10T10:00:00Z",
    "modified_at": "2025-12-10T10:00:00Z"
  }
]
```

#### GET /agents/{name}

Get a specific agent blueprint.

**Response:**
```json
{
  "name": "researcher",
  "description": "Research agent",
  "system_prompt": "You are...",
  "mcp_servers": {},
  "skills": [],
  "status": "active",
  "created_at": "2025-12-10T10:00:00Z",
  "modified_at": "2025-12-10T10:00:00Z"
}
```

**Error:** `404 Not Found` if agent doesn't exist.

#### POST /agents

Create a new agent blueprint.

**Request Body:**
```json
{
  "name": "researcher",
  "description": "Research agent",
  "system_prompt": "You are...",  // optional
  "mcp_servers": {},               // optional
  "skills": []                     // optional
}
```

**Response:** `201 Created` with Agent object.

**Error:** `409 Conflict` if agent name already exists.

#### PATCH /agents/{name}

Update an existing agent blueprint (partial update).

**Request Body:**
```json
{
  "description": "Updated description",  // optional
  "system_prompt": "...",                // optional
  "mcp_servers": {},                     // optional
  "skills": []                           // optional
}
```

**Response:**
```json
{
  "name": "researcher",
  "description": "Updated description",
  ...
}
```

**Error:** `404 Not Found` if agent doesn't exist.

#### DELETE /agents/{name}

Delete an agent blueprint.

**Response:** `204 No Content`

**Error:** `404 Not Found` if agent doesn't exist.

#### PATCH /agents/{name}/status

Update agent status (active/inactive).

**Request Body:**
```json
{
  "status": "active" | "inactive"
}
```

**Response:**
```json
{
  "name": "researcher",
  "status": "inactive",
  ...
}
```

---

### Jobs API

Queue and manage jobs for launchers to execute.

#### POST /jobs

Create a new job for a launcher to execute.

**Request Body:**
```json
{
  "type": "start_session" | "resume_session",
  "session_name": "my-task",
  "agent_name": "researcher",           // optional
  "prompt": "Research quantum computing",
  "project_dir": "/path/to/project",    // optional
  "parent_session_name": "parent-task"  // optional
}
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "pending"
}
```

#### GET /jobs/{job_id}

Get job status and details.

**Response:**
```json
{
  "job_id": "job_abc123",
  "type": "start_session",
  "session_name": "my-task",
  "agent_name": "researcher",
  "prompt": "Research quantum computing",
  "project_dir": "/path/to/project",
  "parent_session_name": "parent-task",
  "status": "completed",
  "launcher_id": "lnch_xyz789",
  "error": null,
  "created_at": "2025-12-10T10:00:00Z",
  "claimed_at": "2025-12-10T10:00:01Z",
  "started_at": "2025-12-10T10:00:02Z",
  "completed_at": "2025-12-10T10:05:00Z"
}
```

**Job Status Values:**
- `pending` - Job created, waiting for launcher
- `claimed` - Launcher claimed the job
- `running` - Job execution started
- `stopping` - Stop requested, waiting for launcher to terminate process
- `completed` - Job completed successfully
- `failed` - Job execution failed
- `stopped` - Job was stopped (terminated by stop command)

**Error:** `404 Not Found` if job doesn't exist.

#### POST /jobs/{job_id}/stop

Stop a running job by signaling its launcher.

**Response (Success):**
```json
{
  "ok": true,
  "job_id": "job_abc123",
  "session_name": "my-task",
  "status": "stopping"
}
```

**Error Responses:**
- `404 Not Found` - Job not found
- `400 Bad Request` - Job cannot be stopped (not in `claimed` or `running` status)
- `400 Bad Request` - Job not claimed by any launcher

**Notes:**
- Queues a stop command for the launcher that will terminate the job's process
- The launcher receives the stop command immediately (wakes up from long-poll)
- Launcher sends SIGTERM first, then SIGKILL after 5 seconds if process doesn't respond
- Use `POST /sessions/{session_id}/stop` if you have session_id instead of job_id

---

### Launcher API

Endpoints for launcher instances to communicate with the Agent Runtime.

#### POST /launcher/register

Register a new launcher instance.

**Request Body:**
```json
{
  "hostname": "macbook-pro",  // optional
  "project_dir": "/path"      // optional
}
```

**Response:**
```json
{
  "launcher_id": "lnch_abc123",
  "poll_endpoint": "/launcher/jobs",
  "poll_timeout_seconds": 30,
  "heartbeat_interval_seconds": 60
}
```

#### GET /launcher/jobs

Long-poll for available jobs or stop commands (used by launcher).

**Query Parameters:**
- `launcher_id` (required) - The registered launcher ID

**Response (Job Available):**
```json
{
  "job": {
    "job_id": "job_abc123",
    "type": "start_session",
    "session_name": "my-task",
    "prompt": "Do something",
    ...
  }
}
```

**Response (Stop Commands):**
```json
{
  "stop_jobs": ["job_abc123", "job_def456"]
}
```

**Response (No Jobs):** `204 No Content`

**Response (Deregistered):**
```json
{
  "deregistered": true
}
```

**Notes:**
- Holds connection open for up to `poll_timeout_seconds`
- Returns immediately if job or stop command available
- Stop commands wake up the poll immediately (no waiting)
- Returns `deregistered: true` if launcher has been deregistered

#### POST /launcher/jobs/{job_id}/started

Report that job execution has started.

**Request Body:**
```json
{
  "launcher_id": "lnch_abc123"
}
```

**Response:**
```json
{
  "ok": true
}
```

#### POST /launcher/jobs/{job_id}/completed

Report that job completed successfully.

**Request Body:**
```json
{
  "launcher_id": "lnch_abc123",
  "status": "success"  // optional
}
```

**Response:**
```json
{
  "ok": true
}
```

#### POST /launcher/jobs/{job_id}/failed

Report that job execution failed.

**Request Body:**
```json
{
  "launcher_id": "lnch_abc123",
  "error": "Error message"
}
```

**Response:**
```json
{
  "ok": true
}
```

#### POST /launcher/jobs/{job_id}/stopped

Report that job was stopped (terminated by stop command).

**Request Body:**
```json
{
  "launcher_id": "lnch_abc123",
  "signal": "SIGTERM"  // or "SIGKILL" if force killed
}
```

**Response:**
```json
{
  "ok": true
}
```

**Notes:**
- Called by launcher after terminating a process in response to a stop command
- Signal indicates which signal was used to terminate the process

#### POST /launcher/heartbeat

Keep launcher registration alive.

**Request Body:**
```json
{
  "launcher_id": "lnch_abc123"
}
```

**Response:**
```json
{
  "ok": true
}
```

**Notes:**
- Launchers should send heartbeat every `heartbeat_interval_seconds`
- Launcher is considered stale after `heartbeat_timeout_seconds` without heartbeat

#### GET /launchers

List all registered launchers with their status.

**Response:**
```json
{
  "launchers": [
    {
      "launcher_id": "lnch_abc123",
      "registered_at": "2025-12-10T10:00:00Z",
      "last_heartbeat": "2025-12-10T10:05:00Z",
      "hostname": "macbook-pro",
      "project_dir": "/path/to/project",
      "status": "online",
      "seconds_since_heartbeat": 15.5
    }
  ]
}
```

**Launcher Status Values:**
- `online` - Heartbeat within last 2 minutes
- `stale` - No heartbeat for 2+ minutes (connection may be lost)

#### DELETE /launchers/{launcher_id}

Deregister a launcher.

**Query Parameters:**
- `self` (optional, default: false) - If true, launcher is deregistering itself

**Response (External Deregistration):**
```json
{
  "ok": true,
  "message": "Launcher marked for deregistration",
  "initiated_by": "external"
}
```

**Response (Self-Deregistration):**
```json
{
  "ok": true,
  "message": "Launcher deregistered",
  "initiated_by": "self"
}
```

**Notes:**
- External deregistration (dashboard): Marks launcher for deregistration, signals on next poll
- Self-deregistration (launcher shutdown): Immediately removes from registry

**Error:** `404 Not Found` if launcher doesn't exist.

---

## Configuration

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | Agent Orchestrator API URL |
| `DEBUG_LOGGING` | `false` | Enable verbose logging |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins |
| `LAUNCHER_POLL_TIMEOUT` | `30` | Launcher job poll timeout in seconds |
| `LAUNCHER_HEARTBEAT_INTERVAL` | `60` | Launcher heartbeat interval in seconds |
| `LAUNCHER_HEARTBEAT_TIMEOUT` | `120` | Launcher heartbeat timeout in seconds |

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
