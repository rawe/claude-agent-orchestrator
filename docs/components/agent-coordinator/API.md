# Agent Coordinator API

API documentation for the Agent Coordinator server.

**Base URL:** `http://127.0.0.1:8765`

---

## Interactive API Documentation

The Agent Coordinator provides auto-generated OpenAPI documentation that stays in sync with the code:

| Format | URL | Description |
|--------|-----|-------------|
| **Swagger UI** | [`/docs`](http://127.0.0.1:8765/docs) | Interactive API explorer with try-it-out |
| **ReDoc** | [`/redoc`](http://127.0.0.1:8765/redoc) | Clean, readable documentation |
| **OpenAPI JSON** | [`/openapi.json`](http://127.0.0.1:8765/openapi.json) | Raw OpenAPI 3.1.0 specification |

> **Note:** The interactive docs are the authoritative source. This markdown file provides additional context but may lag behind the implementation.

### Enabling/Disabling Documentation Endpoints

The documentation endpoints can be controlled via the `DOCS_ENABLED` environment variable:

| Setting | Behavior |
|---------|----------|
| `DOCS_ENABLED=false` | (Default) All documentation endpoints return 404 Not Found |
| `DOCS_ENABLED=true` | `/docs`, `/redoc`, `/openapi.json` are available |

**Development (docs enabled):**
```bash
AUTH_ENABLED=false DOCS_ENABLED=true uv run python -m main
```

**Production (docs disabled):**
```bash
AUTH_ENABLED=true DOCS_ENABLED=false uv run python -m main
```

> **Security Note:** The documentation endpoints are NOT protected by authentication even when `AUTH_ENABLED=true`. For public deployments, set `DOCS_ENABLED=false` to prevent exposing your API schema.

---

## Server-Sent Events (SSE)

Real-time updates for sessions and events via SSE (migrated from WebSocket per ADR-013).

**URL:** `GET /sse/sessions`

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
Sent when a new session is created via POST /runs with `type: "start_session"`.

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
  "session_id": "ses_abc123"
}
```
Sent when a session is deleted via DELETE endpoint.

**Run Failed:**
```json
{
  "type": "run_failed",
  "run_id": "run_abc123",
  "session_id": "ses_abc123",
  "error": "Error message"
}
```
Sent when a run fails (e.g., no matching runner within timeout).

### Event Types

- `session_start` - When an agent session starts
- `pre_tool` - Before a tool executes (shows input parameters)
- `post_tool` - After a tool executes (shows input + output)
- `session_stop` - When a session ends
- `message` - Agent or user messages

See [Event Types](DATA_MODELS.md#event-types) for detailed schemas.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Filter to single session |
| `include_init` | bool | Include initial state on connect (default: true) |

### Headers

| Header | Description |
|--------|-------------|
| `Last-Event-ID` | Resume from last event (for reconnection) |

### Connection Flow

1. Client connects via `EventSource` or fetch with streaming
2. Server sends `init` event with all matching sessions (unless resuming)
3. Server broadcasts events as they occur
4. Client receives events with unique IDs for resumption
5. Heartbeat sent every 30s to keep connection alive

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

#### GET /sessions/{session_id}/affinity

Get session affinity information for resume routing.

**Response:**
```json
{
  "affinity": {
    "hostname": "macbook-pro",
    "project_dir": "/path/to/project",
    "executor_type": "claude-code",
    "executor_session_id": "uuid-from-claude-sdk"
  }
}
```

**Notes:**
- Used to route resume requests to the correct runner
- Returns the runner/executor information from the last execution

#### POST /sessions/{session_id}/bind

Bind executor information to a session after framework starts.

**Request Body:**
```json
{
  "executor_session_id": "uuid-from-claude-sdk",
  "hostname": "macbook-pro",
  "executor_type": "claude-code",
  "project_dir": "/path/to/project"  // optional
}
```

**Response:**
```json
{
  "ok": true,
  "session": Session
}
```

**Notes:**
- Called by agent runner after Claude Code framework starts
- Updates session status from `pending` to `running`
- Stores executor information for session affinity

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
  "project_dir": "/new/path",           // optional
  "agent_name": "new-agent",            // optional
  "last_resumed_at": "ISO 8601",        // optional
  "executor_session_id": "uuid",        // optional
  "executor_type": "claude-code",       // optional
  "hostname": "macbook-pro"             // optional
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
- Session must exist (created via POST /runs with `type: "start_session"`)
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
- Prefer POST /runs (with `type: "start_session"`) + POST /sessions/{id}/events for new integrations

---

### Agents API

Manage agent blueprints (templates for creating agents).

**Capability Resolution:** Agents can reference capabilities (reusable configurations). When fetching an agent, capabilities are resolved and merged into `system_prompt` and `mcp_servers`. Use `?raw=true` to get unresolved data for editing. See [Capabilities System](../features/capabilities-system.md).

#### GET /agents

List all agent blueprints.

**Query Parameters:**
- `tags` (optional) - Comma-separated list of tags to filter agents (AND logic)

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
    "tags": ["research"],
    "capabilities": ["neo4j-knowledge-graph"],
    "demands": {
      "hostname": null,
      "project_dir": null,
      "executor_type": null,
      "tags": ["web-access"]
    },
    "status": "active",
    "created_at": "2025-12-10T10:00:00Z",
    "modified_at": "2025-12-10T10:00:00Z"
  }
]
```

**Notes:**
- List returns raw agents (capabilities not resolved)
- `demands` are blueprint demands that are merged with run's `additional_demands`

#### GET /agents/{name}

Get a specific agent blueprint.

**Query Parameters:**
- `raw` (optional, default: `false`) - If `true`, return raw agent without capability resolution

**Response (default - resolved):**
```json
{
  "name": "researcher",
  "description": "Research agent",
  "system_prompt": "You are...\n\n---\n\n## Capability Instructions...",
  "mcp_servers": { ... },
  "skills": [],
  "tags": [],
  "capabilities": ["neo4j-knowledge-graph"],
  "status": "active",
  "created_at": "2025-12-10T10:00:00Z",
  "modified_at": "2025-12-10T10:00:00Z"
}
```

**Response (`?raw=true` - unresolved):**
```json
{
  "name": "researcher",
  "description": "Research agent",
  "system_prompt": "You are...",
  "mcp_servers": null,
  "skills": [],
  "tags": [],
  "capabilities": ["neo4j-knowledge-graph"],
  "status": "active",
  "created_at": "2025-12-10T10:00:00Z",
  "modified_at": "2025-12-10T10:00:00Z"
}
```

**Errors:**
- `404 Not Found` - Agent doesn't exist
- `422 Unprocessable Entity` - Capability resolution failed (missing capability or MCP server conflict)

#### POST /agents

Create a new agent blueprint.

**Request Body:**
```json
{
  "name": "researcher",
  "description": "Research agent",
  "system_prompt": "You are...",  // optional
  "mcp_servers": {},              // optional
  "skills": [],                   // optional
  "tags": [],                     // optional
  "capabilities": [],             // optional - capability names to include
  "demands": {                    // optional
    "hostname": null,
    "project_dir": null,
    "executor_type": null,
    "tags": ["web-access"]
  }
}
```

**Response:** `201 Created` with Agent object.

**Error:** `409 Conflict` if agent name already exists.

**Notes:**
- `capabilities` array references capability names; resolved at read time
- `demands` specify blueprint demands for runner matching
- These demands are merged with `additional_demands` when a run is created

#### PATCH /agents/{name}

Update an existing agent blueprint (partial update).

**Request Body:**
```json
{
  "description": "Updated description",  // optional
  "system_prompt": "...",                // optional
  "mcp_servers": {},                     // optional
  "skills": [],                          // optional
  "tags": [],                            // optional
  "capabilities": [],                    // optional
  "demands": {}                          // optional
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

### Capabilities API

Manage reusable capability configurations that can be shared across agents.

#### GET /capabilities

List all capabilities with summary metadata.

**Response:**
```json
[
  {
    "name": "neo4j-knowledge-graph",
    "description": "Company knowledge graph",
    "has_text": true,
    "has_mcp": true,
    "mcp_server_names": ["neo4j"],
    "created_at": "2025-12-10T10:00:00Z",
    "modified_at": "2025-12-10T10:00:00Z"
  }
]
```

#### GET /capabilities/{name}

Get a specific capability with full content.

**Response:**
```json
{
  "name": "neo4j-knowledge-graph",
  "description": "Company knowledge graph",
  "text": "## Knowledge Graph Ontology\n\n...",
  "mcp_servers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9003/mcp/"
    }
  },
  "created_at": "2025-12-10T10:00:00Z",
  "modified_at": "2025-12-10T10:00:00Z"
}
```

**Error:** `404 Not Found` if capability doesn't exist.

#### POST /capabilities

Create a new capability.

**Request Body:**
```json
{
  "name": "neo4j-knowledge-graph",
  "description": "Company knowledge graph",
  "text": "## Knowledge Graph Ontology\n\n...",  // optional
  "mcp_servers": {}                              // optional
}
```

**Response:** `201 Created` with Capability object.

**Errors:**
- `400 Bad Request` - Invalid capability name
- `409 Conflict` - Capability already exists

#### PATCH /capabilities/{name}

Update an existing capability (partial update).

**Request Body:**
```json
{
  "description": "Updated description",  // optional
  "text": "...",                         // optional
  "mcp_servers": {}                      // optional
}
```

**Response:** Capability object.

**Error:** `404 Not Found` if capability doesn't exist.

#### DELETE /capabilities/{name}

Delete a capability.

**Response:** `204 No Content`

**Errors:**
- `404 Not Found` - Capability doesn't exist
- `409 Conflict` - Capability is referenced by agents

---

### Runs API

Queue and manage runs for runners to execute. See [RUNS_API.md](./RUNS_API.md) for comprehensive documentation.

#### POST /runs

Create a new run for a runner to execute.

**Request Body:**
```json
{
  "type": "start_session" | "resume_session",
  "session_id": null,                        // coordinator-generated if not provided
  "agent_name": "researcher",                // optional
  "prompt": "Research quantum computing",
  "project_dir": "/path/to/project",         // optional
  "parent_session_id": "ses_parent123",      // optional
  "execution_mode": "sync",                  // optional: sync, async_poll, async_callback
  "additional_demands": {                    // optional
    "tags": ["research"]
  }
}
```

**Response:**
```json
{
  "run_id": "run_abc123",
  "session_id": "ses_abc123",
  "status": "pending"
}
```

**Notes:**
- For `start_session`, creates a pending session and broadcasts `session_created`
- Demands from agent blueprint are merged with `additional_demands`
- Runs with demands get a 5-minute timeout for matching

#### GET /runs/{run_id}

Get run status and details.

**Response:**
```json
{
  "run_id": "run_abc123",
  "type": "start_session",
  "session_id": "ses_abc123",
  "agent_name": "researcher",
  "prompt": "Research quantum computing",
  "project_dir": "/path/to/project",
  "parent_session_id": "ses_parent123",
  "execution_mode": "async_callback",
  "demands": {
    "hostname": null,
    "project_dir": null,
    "executor_type": null,
    "tags": ["research"]
  },
  "status": "completed",
  "runner_id": "lnch_xyz789abc",
  "error": null,
  "created_at": "2025-12-10T10:00:00Z",
  "claimed_at": "2025-12-10T10:00:01Z",
  "started_at": "2025-12-10T10:00:02Z",
  "completed_at": "2025-12-10T10:05:00Z",
  "timeout_at": null
}
```

**Run Status Values:**
- `pending` - Run created, waiting for runner
- `claimed` - Runner claimed the run
- `running` - Run execution started
- `stopping` - Stop requested, waiting for runner to terminate process
- `completed` - Run completed successfully
- `failed` - Run execution failed (or no matching runner within timeout)
- `stopped` - Run was stopped (terminated by stop command)

**Error:** `404 Not Found` if run doesn't exist.

#### POST /runs/{run_id}/stop

Stop a running run by signaling its runner.

**Response (Success):**
```json
{
  "ok": true,
  "run_id": "run_abc123",
  "session_id": "ses_abc123",
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
  "hostname": "macbook-pro",
  "project_dir": "/path/to/project",
  "executor_type": "claude-code",
  "tags": ["research", "web-access"]  // optional capability tags
}
```

**Response:**
```json
{
  "runner_id": "lnch_abc123xyz",
  "poll_endpoint": "/runner/runs",
  "poll_timeout_seconds": 30,
  "heartbeat_interval_seconds": 60
}
```

**Notes:**
- `runner_id` is deterministically derived from (hostname, project_dir, executor_type)
- Returns `409 Conflict` if an online runner with the same identity already exists
- Stale runners with the same identity are treated as reconnections
- `tags` are capability tags for demand matching

**Error (Duplicate Runner):**
```json
{
  "error": "DuplicateRunnerError",
  "message": "An online runner with this identity already exists",
  "runner_id": "lnch_abc123xyz",
  "hostname": "macbook-pro",
  "project_dir": "/path/to/project",
  "executor_type": "claude-code"
}
```
**Status Code:** `409 Conflict`

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
    "session_id": "ses_abc123",
    "prompt": "Do something",
    "execution_mode": "sync",
    "demands": null,
    ...
  }
}
```

**Response (Stop Commands - highest priority):**
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
- Stop commands are checked first (highest priority) and wake up the poll immediately
- Demand matching is applied: only runs matching runner's capabilities are returned
- Holds connection open for up to `poll_timeout_seconds` if no runs available
- Returns `deregistered: true` if runner has been deregistered

#### POST /runner/runs/{run_id}/started

Report that run execution has started.

**Request Body:**
```json
{
  "runner_id": "lnch_abc123xyz"
}
```

**Response:**
```json
{
  "ok": true
}
```

**Notes:**
- Updates run status to `running`
- Links `parent_session_id` to the session for hierarchy tracking

#### POST /runner/runs/{run_id}/completed

Report that run completed successfully.

**Request Body:**
```json
{
  "runner_id": "lnch_abc123xyz",
  "status": "success"  // optional
}
```

**Response:**
```json
{
  "ok": true
}
```

**Notes:**
- Updates run status to `completed`
- If `execution_mode` is `async_callback`, triggers callback to parent session

#### POST /runner/runs/{run_id}/failed

Report that run execution failed.

**Request Body:**
```json
{
  "runner_id": "lnch_abc123xyz",
  "error": "Error message"
}
```

**Response:**
```json
{
  "ok": true
}
```

**Notes:**
- Updates run status to `failed`
- If `execution_mode` is `async_callback`, triggers callback to parent session with error

#### POST /runner/runs/{run_id}/stopped

Report that run was stopped (terminated by stop command).

**Request Body:**
```json
{
  "runner_id": "lnch_abc123xyz",
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
- Updates run status to `stopped` and session status to `stopped`
- Signal indicates which signal was used to terminate the process (`SIGTERM` or `SIGKILL`)
- If `execution_mode` is `async_callback`, triggers callback to parent session

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
      "runner_id": "lnch_abc123xyz",
      "registered_at": "2025-12-10T10:00:00Z",
      "last_heartbeat": "2025-12-10T10:05:00Z",
      "hostname": "macbook-pro",
      "project_dir": "/path/to/project",
      "executor_type": "claude-code",
      "tags": ["research", "web-access"],
      "status": "online",
      "seconds_since_heartbeat": 15.5
    }
  ]
}
```

**Runner Status Values:**
- `online` - Heartbeat within last 2 minutes
- `stale` - No heartbeat for 2+ minutes (connection may be lost)

**Notes:**
- `tags` are capability tags that runners advertise for demand matching
- `runner_id` is deterministically derived from (hostname, project_dir, executor_type)

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
