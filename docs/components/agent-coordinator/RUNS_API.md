# Runs API

The Runs API enables distributed agent execution by separating orchestration (Agent Coordinator) from execution (Agent Runner). This allows the Agent Coordinator to be containerized while runners run on host machines where agent frameworks are installed.

## Architecture

```
ao-* CLI / Dashboard / MCP Server
              │
              │ POST /runs
              ▼
┌─────────────────────────────────────────┐
│       Agent Coordinator :8765           │
│  ┌───────────────────────────┐          │
│  │   In-Memory Run Queue     │          │
│  │  (thread-safe, singleton) │          │
│  └───────────────────────────┘          │
└──────────────┬──────────────────────────┘
               │ Long-poll GET /runner/runs
               ▼
┌─────────────────────────────────────────┐
│        Agent Runner                     │
│  - Polls for pending runs               │
│  - Concurrent execution                 │
│  - Reports run status                   │
│  - Heartbeat monitoring                 │
└──────────────┬──────────────────────────┘
               │ Subprocess
               ▼
┌─────────────────────────────────────────┐
│    Claude Code Executors                │
│  - ao-*-exec: Start or Resumes sessions │
└─────────────────────────────────────────┘
```

## Run Lifecycle

Runs follow a state machine with seven statuses:

```
┌─────────┐    claim    ┌─────────┐   started   ┌─────────┐
│ PENDING │────────────►│ CLAIMED │────────────►│ RUNNING │
└────┬────┘             └─────────┘             └────┬────┘
     │                                               │
     │ timeout                      ┌────────────────┼────────────────┐
     │ (no match)                   │                │                │
     ▼                              ▼                ▼                ▼
┌────────┐                   ┌───────────┐    ┌──────────┐     ┌────────┐
│ FAILED │                   │ COMPLETED │    │ STOPPING │────►│ STOPPED│
└────────┘                   └───────────┘    └──────────┘     └────────┘
```

| Status | Description |
|--------|-------------|
| `pending` | Run created, waiting for a runner to claim it |
| `claimed` | Runner claimed the run, preparing to execute |
| `running` | Run execution has started |
| `stopping` | Stop requested, waiting for runner to terminate process |
| `completed` | Run completed successfully |
| `failed` | Run execution failed (or no matching runner within timeout) |
| `stopped` | Run was stopped (terminated by stop command) |

## Data Model

### Run

```json
{
  "run_id": "run_abc123def456",
  "type": "start_session",
  "session_id": "ses_abc123def456",
  "agent_name": "researcher",
  "prompt": "Research quantum computing advances",
  "project_dir": "/path/to/project",
  "parent_session_id": "ses_xyz789",
  "execution_mode": "async_callback",
  "demands": {
    "hostname": null,
    "project_dir": null,
    "executor_type": null,
    "tags": ["research", "web-access"]
  },
  "status": "running",
  "runner_id": "lnch_xyz789abc",
  "error": null,
  "created_at": "2025-12-10T10:00:00Z",
  "claimed_at": "2025-12-10T10:00:01Z",
  "started_at": "2025-12-10T10:00:02Z",
  "completed_at": null,
  "timeout_at": "2025-12-10T10:05:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Unique identifier (e.g., `run_abc123def456`) |
| `type` | enum | `start_session` or `resume_session` |
| `session_id` | string | Coordinator-generated session ID (format: `ses_{12-char-hex}`) |
| `agent_name` | string? | Optional agent blueprint to use |
| `prompt` | string | User prompt/instruction for the agent |
| `project_dir` | string? | Optional project directory path |
| `parent_session_id` | string? | Parent session ID for callback support |
| `execution_mode` | enum | `sync`, `async_poll`, or `async_callback` (default: `sync`) |
| `demands` | object? | Runner demands for capability matching (see below) |
| `status` | enum | Current run status |
| `runner_id` | string? | ID of the runner that claimed/executed the run |
| `error` | string? | Error message if run failed |
| `created_at` | ISO 8601 | Timestamp when run was created |
| `claimed_at` | ISO 8601? | Timestamp when runner claimed the run |
| `started_at` | ISO 8601? | Timestamp when execution started |
| `completed_at` | ISO 8601? | Timestamp when run completed or failed |
| `timeout_at` | ISO 8601? | Timestamp when run will fail if no matching runner found |

### Execution Modes

| Mode | Description |
|------|-------------|
| `sync` | Parent waits for child completion, receives result directly |
| `async_poll` | Parent continues immediately, polls for child status/result |
| `async_callback` | Parent continues immediately, coordinator auto-resumes parent when child completes |

### Runner Demands

Runs can specify requirements for which runners can execute them:

```json
{
  "hostname": "macbook-pro",     // Property demand: exact match on hostname
  "project_dir": "/path/to/project",  // Property demand: exact match on project_dir
  "executor_type": "claude-code", // Property demand: exact match on executor_type
  "tags": ["research", "web-access"]  // Capability demands: runner must have ALL tags
}
```

- **Property demands** (hostname, project_dir, executor_type): Require exact match if specified
- **Tag demands**: Runner must have ALL specified tags in its capabilities
- Runs with demands have a 5-minute timeout; if no matching runner claims the run, it fails

### Run Types

| Type | Description |
|------|-------------|
| `start_session` | Start a new Claude Code session |
| `resume_session` | Resume an existing session with a new prompt |

## API Endpoints

### Create Run

Create a new run for a runner to execute.

```
POST /runs
```

**Request Body:**
```json
{
  "type": "start_session",
  "session_id": null,
  "agent_name": "researcher",
  "prompt": "Research quantum computing",
  "project_dir": "/path/to/project",
  "parent_session_id": "ses_parent123",
  "execution_mode": "async_callback",
  "additional_demands": {
    "tags": ["research"]
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `start_session` or `resume_session` |
| `session_id` | No | Coordinator-generated if not provided (for `start_session`) |
| `prompt` | Yes | Task prompt for the agent |
| `agent_name` | No | Agent blueprint to use (demands merged from blueprint) |
| `project_dir` | No | Project directory path |
| `parent_session_id` | No | Parent session ID for hierarchy tracking |
| `execution_mode` | No | `sync` (default), `async_poll`, or `async_callback` |
| `additional_demands` | No | Additional runner demands (merged with blueprint demands) |

**Response:**
```json
{
  "run_id": "run_abc123",
  "session_id": "ses_abc123",
  "status": "pending"
}
```

**Notes:**
- For `start_session`, creates a pending session immediately
- Broadcasts `session_created` to WebSocket clients
- If agent has demands in its blueprint, they are merged with `additional_demands`
- Runs with demands get a 5-minute timeout for matching

### Get Run

Get run status and details.

```
GET /runs/{run_id}
```

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

**Error:** `404 Not Found` if run doesn't exist.

### Stop Run

Stop a running run by signaling its runner.

```
POST /runs/{run_id}/stop
```

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
- Queues a stop command for the runner
- Runner receives the stop command immediately (wakes up from long-poll)
- Runner sends SIGTERM first, then SIGKILL after 5 seconds if process doesn't respond

## Runner Endpoints

These endpoints are used by the Agent Runner to poll for and report on runs.

### Register Runner

Register a new runner instance.

```
POST /runner/register
```

**Request Body:**
```json
{
  "hostname": "macbook-pro",
  "project_dir": "/path/to/project",
  "executor_type": "claude-code",
  "tags": ["research", "web-access"]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `hostname` | Yes | Machine hostname |
| `project_dir` | Yes | Default project directory |
| `executor_type` | Yes | Executor type (e.g., `claude-code`) |
| `tags` | No | Capability tags for demand matching |

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

### Poll for Runs

Long-poll for available runs or stop commands. Returns immediately if a run or stop command is available, otherwise holds the connection open.

```
GET /runner/runs?runner_id={runner_id}
```

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `runner_id` | Yes | The registered runner ID |

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
- Connection held up to 30 seconds if no runs available

### Report Run Started

Report that run execution has started.

```
POST /runner/runs/{run_id}/started
```

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

### Report Run Completed

Report that run completed successfully.

```
POST /runner/runs/{run_id}/completed
```

**Request Body:**
```json
{
  "runner_id": "lnch_abc123xyz",
  "status": "success"
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

### Report Run Failed

Report that run execution failed.

```
POST /runner/runs/{run_id}/failed
```

**Request Body:**
```json
{
  "runner_id": "lnch_abc123xyz",
  "error": "Error message describing what went wrong"
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

### Report Run Stopped

Report that run was stopped (terminated by stop command).

```
POST /runner/runs/{run_id}/stopped
```

**Request Body:**
```json
{
  "runner_id": "lnch_abc123xyz",
  "signal": "SIGTERM"
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
- `signal` indicates which signal was used to terminate (`SIGTERM` or `SIGKILL`)
- If `execution_mode` is `async_callback`, triggers callback to parent session

## Implementation Details

### Run Queue

**File:** `servers/agent-coordinator/services/run_queue.py`

The run queue is an in-memory, thread-safe singleton that stores runs in a dictionary with locking for atomic operations.

```python
class RunQueue:
    def add_run(run_create: RunCreate, demands: Optional[RunnerDemands] = None) -> Run
    def claim_run(runner_id: str, runner_info: RunnerInfo) -> Optional[Run]
    def get_run(run_id: str) -> Optional[Run]
    def update_run_status(run_id: str, status: RunStatus, error: str = None) -> Optional[Run]
    def get_run_by_session_id(session_id: str) -> Optional[Run]
    def fail_timed_out_runs() -> List[Run]
```

Key characteristics:
- Runs are **not persisted** to SQLite (in-memory only)
- Thread-safe with `threading.Lock` for concurrent access
- FIFO ordering for run claiming
- Demand matching applied during `claim_run`
- Timeout checking via `fail_timed_out_runs` (runs every 30 seconds)
- Module-level singleton: `run_queue`

### Runner Registry

**File:** `servers/agent-coordinator/services/runner_registry.py`

Manages runner registration, lifecycle, and capability matching.

```python
class RunnerRegistry:
    def register(hostname: str, project_dir: str, executor_type: str, tags: List[str]) -> RunnerInfo
    def update_heartbeat(runner_id: str) -> bool
    def deregister(runner_id: str) -> bool
    def get_runner(runner_id: str) -> Optional[RunnerInfo]
    def list_runners() -> List[RunnerWithStatus]
    def update_lifecycle() -> None
```

Key characteristics:
- Deterministic runner_id from (hostname, project_dir, executor_type)
- Prevents duplicate online runner registration (409 Conflict)
- Stale runner detection via background task (runs every 30 seconds)
- Tags stored for capability-based demand matching

### Agent Runner Components

| Component | File | Purpose |
|-----------|------|---------|
| `RunPoller` | `servers/agent-runner/lib/poller.py` | Background thread polling for pending runs |
| `RunExecutor` | `servers/agent-runner/lib/executor.py` | Spawns ao-start/ao-resume subprocesses |
| `RunSupervisor` | `servers/agent-runner/lib/supervisor.py` | Monitors running runs, reports completion |
| `CoordinatorAPIClient` | `servers/agent-runner/lib/api_client.py` | HTTP client for runner endpoints |

### Long-Polling Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `RUNNER_POLL_TIMEOUT` | `30` | Seconds to hold connection open |
| `RUNNER_HEARTBEAT_INTERVAL` | `60` | Seconds between heartbeats |
| `RUNNER_HEARTBEAT_TIMEOUT` | `120` | Seconds before runner marked stale |

## Usage Examples

### Dashboard

The dashboard creates runs when users start or resume sessions:

```typescript
// dashboard/src/services/chatService.ts
const response = await agentOrchestratorApi.post('/runs', {
  type: 'start_session',
  agent_name: agentName,
  prompt: prompt,
  project_dir: projectDir
});
// Response includes: run_id, session_id, status
```

### CLI Commands

The orchestrator plugin uses `RunClient` to create runs and wait for completion:

```python
# plugins/orchestrator/skills/orchestrator/commands/lib/run_client.py
client = RunClient(api_url)
result = client.start_session(
    prompt="Do something",
    agent_name="researcher",
    execution_mode="async_callback"
)
```

### Parent-Child Callbacks (Execution Modes)

Runs support three execution modes for parent-child orchestration:

| Mode | Behavior |
|------|----------|
| `sync` | Parent waits for child, receives result directly |
| `async_poll` | Parent continues, polls `/runs/{run_id}` for status |
| `async_callback` | Parent continues, coordinator auto-resumes parent |

For `async_callback` mode:

1. Parent agent starts child with `parent_session_id` and `execution_mode: async_callback`
2. Parent continues working (non-blocking)
3. When child completes, Callback Processor queues notification
4. When parent becomes idle, coordinator creates resume run with child's result

```
Parent (orchestrator)          Child (worker)
       │                            │
       │ POST /runs                 │
       │ parent_session_id=self     │
       │ execution_mode=async_cb    │
       │───────────────────────────►│
       │                            │
       │ continues work...          │ executes task...
       │                            │
       │ becomes idle               │ completes
       │                            │
       │◄─── callback processor ────┤
       │     creates resume run     │
       │                            │
       ▼
  resumes with child result
```

## Related Documentation

- [API.md](./API.md) - Complete REST API reference
- [DATA_MODELS.md](./DATA_MODELS.md) - All data model schemas
- [USAGE.md](./USAGE.md) - Quick start guide
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
