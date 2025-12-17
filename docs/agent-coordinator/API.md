# Agent Coordinator API

API documentation for the Agent Coordinator server.

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

Stop a running session by signaling its runner.

Finds the active run for this session and queues a stop command.

**Response (Success):**
```json
{
  "ok": true,
  "session_id": "abc-123",
  "run_id": "run_xyz789",
  "session_name": "my-task",
  "status": "stopping"
}
```

**Error Responses:**
- `404 Not Found` - Session not found
- `400 Bad Request` - Session is not running
- `404 Not Found` - No active run found for session
- `400 Bad Request` - Run not claimed by any runner / Run cannot be stopped

**Notes:**
- Convenience endpoint that looks up the run by session
- For direct run control, use `POST /runs/{run_id}/stop` instead
- Queues a stop command for the runner that will terminate the session's process
- The runner receives the stop command immediately (wakes up from long-poll)
- Runner sends SIGTERM first, then SIGKILL after 5 seconds if process doesn't respond

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

### Runs API

Queue and manage runs for runners to execute.

#### POST /runs

Create a new run for a runner to execute.

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
  "run_id": "run_abc123",
  "status": "pending"
}
```

#### GET /runs/{run_id}

Get run status and details.

**Response:**
```json
{
  "run_id": "run_abc123",
  "type": "start_session",
  "session_name": "my-task",
  "agent_name": "researcher",
  "prompt": "Research quantum computing",
  "project_dir": "/path/to/project",
  "parent_session_name": "parent-task",
  "status": "completed",
  "runner_id": "lnch_xyz789",
  "error": null,
  "created_at": "2025-12-10T10:00:00Z",
  "claimed_at": "2025-12-10T10:00:01Z",
  "started_at": "2025-12-10T10:00:02Z",
  "completed_at": "2025-12-10T10:05:00Z"
}
```

**Run Status Values:**
- `pending` - Run created, waiting for runner
- `claimed` - Runner claimed the run
- `running` - Run execution started
- `stopping` - Stop requested, waiting for runner to terminate process
- `completed` - Run completed successfully
- `failed` - Run execution failed
- `stopped` - Run was stopped (terminated by stop command)

**Error:** `404 Not Found` if run doesn't exist.

#### POST /runs/{run_id}/stop

Stop a running run by signaling its runner.

**Response (Success):**
```json
{
  "ok": true,
  "run_id": "run_abc123",
  "session_name": "my-task",
  "status": "stopping"
}
```

**Error Responses:**
- `404 Not Found` - Run not found
- `400 Bad Request` - Run cannot be stopped (not in `claimed` or `running` status)
- `400 Bad Request` - Run not claimed by any runner

**Notes:**
- Queues a stop command for the runner that will terminate the run's process
- The runner receives the stop command immediately (wakes up from long-poll)
- Runner sends SIGTERM first, then SIGKILL after 5 seconds if process doesn't respond
- Use `POST /sessions/{session_id}/stop` if you have session_id instead of run_id

---

### Runner API

Endpoints for runner instances to communicate with the Agent Coordinator.

#### POST /runner/register

Register a new runner instance.

**Request Body:**
```json
{
  "hostname": "macbook-pro",    // optional
  "project_dir": "/path",       // optional
  "executor_type": "claude-code" // optional - executor folder name
}
```

**Response:**
```json
{
  "runner_id": "lnch_abc123",
  "poll_endpoint": "/runner/runs",
  "poll_timeout_seconds": 30,
  "heartbeat_interval_seconds": 60
}
```

#### GET /runner/runs

Long-poll for available runs or stop commands (used by runner).

**Query Parameters:**
- `runner_id` (required) - The registered runner ID

**Response (Run Available):**
```json
{
  "run": {
    "run_id": "run_abc123",
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
  "stop_runs": ["run_abc123", "run_def456"]
}
```

**Response (No Runs):** `204 No Content`

**Response (Deregistered):**
```json
{
  "deregistered": true
}
```

**Notes:**
- Holds connection open for up to `poll_timeout_seconds`
- Returns immediately if run or stop command available
- Stop commands wake up the poll immediately (no waiting)
- Returns `deregistered: true` if runner has been deregistered

#### POST /runner/runs/{run_id}/started

Report that run execution has started.

**Request Body:**
```json
{
  "runner_id": "lnch_abc123"
}
```

**Response:**
```json
{
  "ok": true
}
```

#### POST /runner/runs/{run_id}/completed

Report that run completed successfully.

**Request Body:**
```json
{
  "runner_id": "lnch_abc123",
  "status": "success"  // optional
}
```

**Response:**
```json
{
  "ok": true
}
```

#### POST /runner/runs/{run_id}/failed

Report that run execution failed.

**Request Body:**
```json
{
  "runner_id": "lnch_abc123",
  "error": "Error message"
}
```

**Response:**
```json
{
  "ok": true
}
```

#### POST /runner/runs/{run_id}/stopped

Report that run was stopped (terminated by stop command).

**Request Body:**
```json
{
  "runner_id": "lnch_abc123",
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
- Called by runner after terminating a process in response to a stop command
- Signal indicates which signal was used to terminate the process

#### POST /runner/heartbeat

Keep runner registration alive.

**Request Body:**
```json
{
  "runner_id": "lnch_abc123"
}
```

**Response:**
```json
{
  "ok": true
}
```

**Notes:**
- Runners should send heartbeat every `heartbeat_interval_seconds`
- Runner is considered stale after `heartbeat_timeout_seconds` without heartbeat

#### GET /runners

List all registered runners with their status.

**Response:**
```json
{
  "runners": [
    {
      "runner_id": "lnch_abc123",
      "registered_at": "2025-12-10T10:00:00Z",
      "last_heartbeat": "2025-12-10T10:05:00Z",
      "hostname": "macbook-pro",
      "project_dir": "/path/to/project",
      "executor_type": "claude-code",
      "status": "online",
      "seconds_since_heartbeat": 15.5
    }
  ]
}
```

**Runner Status Values:**
- `online` - Heartbeat within last 2 minutes
- `stale` - No heartbeat for 2+ minutes (connection may be lost)

#### DELETE /runners/{runner_id}

Deregister a runner.

**Query Parameters:**
- `self` (optional, default: false) - If true, runner is deregistering itself

**Response (External Deregistration):**
```json
{
  "ok": true,
  "message": "Runner marked for deregistration",
  "initiated_by": "external"
}
```

**Response (Self-Deregistration):**
```json
{
  "ok": true,
  "message": "Runner deregistered",
  "initiated_by": "self"
}
```

**Notes:**
- External deregistration (dashboard): Marks runner for deregistration, signals on next poll
- Self-deregistration (runner shutdown): Immediately removes from registry

**Error:** `404 Not Found` if runner doesn't exist.

---

## Configuration

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | Agent Orchestrator API URL |
| `DEBUG_LOGGING` | `false` | Enable verbose logging |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins |
| `RUNNER_POLL_TIMEOUT` | `30` | Runner run poll timeout in seconds |
| `RUNNER_HEARTBEAT_INTERVAL` | `60` | Runner heartbeat interval in seconds |
| `RUNNER_HEARTBEAT_TIMEOUT` | `120` | Runner heartbeat timeout in seconds |

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
