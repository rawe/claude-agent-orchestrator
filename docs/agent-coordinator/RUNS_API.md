# Runs API

The Runs API enables distributed agent execution by separating orchestration (Agent Coordinator) from execution (Agent Launcher). This allows the Agent Coordinator to be containerized while launchers run on host machines where agent frameworks are installed.

## Architecture

```
ao-* CLI / Dashboard / MCP Server
              │
              │ POST /runs
              ▼
┌─────────────────────────────────┐
│       Agent Coordinator :8765       │
│  ┌───────────────────────────┐  │
│  │   In-Memory Run Queue     │  │
│  │  (thread-safe, singleton) │  │
│  └───────────────────────────┘  │
└──────────────┬──────────────────┘
               │ Long-poll GET /launcher/runs
               ▼
┌─────────────────────────────────┐
│        Agent Launcher           │
│  - Polls for pending runs       │
│  - Concurrent execution         │
│  - Reports run status           │
│  - Heartbeat monitoring         │
└──────────────┬──────────────────┘
               │ Subprocess
               ▼
┌─────────────────────────────────┐
│    Claude Code Executors        │
│  - ao-start: Start new sessions │
│  - ao-resume: Resume sessions   │
└─────────────────────────────────┘
```

## Run Lifecycle

Runs follow a state machine with five statuses:

```
┌─────────┐    claim    ┌─────────┐   started   ┌─────────┐
│ PENDING │────────────►│ CLAIMED │────────────►│ RUNNING │
└─────────┘             └─────────┘             └────┬────┘
                                                     │
                                    ┌────────────────┼────────────────┐
                                    │                                 │
                                    ▼                                 ▼
                             ┌───────────┐                     ┌────────┐
                             │ COMPLETED │                     │ FAILED │
                             └───────────┘                     └────────┘
```

| Status | Description |
|--------|-------------|
| `pending` | Run created, waiting for a launcher to claim it |
| `claimed` | Launcher claimed the run, preparing to execute |
| `running` | Run execution has started |
| `completed` | Run completed successfully |
| `failed` | Run execution failed |

## Data Model

### Run

```json
{
  "run_id": "run_abc123def456",
  "type": "start_session",
  "session_name": "my-research-task",
  "agent_name": "researcher",
  "prompt": "Research quantum computing advances",
  "project_dir": "/path/to/project",
  "parent_session_name": "orchestrator-main",
  "status": "running",
  "launcher_id": "lnch_xyz789",
  "error": null,
  "created_at": "2025-12-10T10:00:00Z",
  "claimed_at": "2025-12-10T10:00:01Z",
  "started_at": "2025-12-10T10:00:02Z",
  "completed_at": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Unique identifier (e.g., `run_abc123def456`) |
| `type` | enum | `start_session` or `resume_session` |
| `session_name` | string | Name of the session to start/resume |
| `agent_name` | string? | Optional agent blueprint to use |
| `prompt` | string | User prompt/instruction for the agent |
| `project_dir` | string? | Optional project directory path |
| `parent_session_name` | string? | Parent session name for callback support |
| `status` | enum | Current run status |
| `launcher_id` | string? | ID of the launcher that claimed/executed the run |
| `error` | string? | Error message if run failed |
| `created_at` | ISO 8601 | Timestamp when run was created |
| `claimed_at` | ISO 8601? | Timestamp when launcher claimed the run |
| `started_at` | ISO 8601? | Timestamp when execution started |
| `completed_at` | ISO 8601? | Timestamp when run completed or failed |

### Run Types

| Type | Description |
|------|-------------|
| `start_session` | Start a new Claude Code session |
| `resume_session` | Resume an existing session with a new prompt |

## API Endpoints

### Create Run

Create a new run for a launcher to execute.

```
POST /runs
```

**Request Body:**
```json
{
  "type": "start_session",
  "session_name": "my-task",
  "agent_name": "researcher",
  "prompt": "Research quantum computing",
  "project_dir": "/path/to/project",
  "parent_session_name": "parent-task"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `start_session` or `resume_session` |
| `session_name` | Yes | Name for the session |
| `prompt` | Yes | Task prompt for the agent |
| `agent_name` | No | Agent blueprint to use |
| `project_dir` | No | Project directory path |
| `parent_session_name` | No | Parent session for callbacks |

**Response:**
```json
{
  "run_id": "run_abc123",
  "status": "pending"
}
```

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

**Error:** `404 Not Found` if run doesn't exist.

## Launcher Endpoints

These endpoints are used by the Agent Launcher to poll for and report on runs.

### Poll for Runs

Long-poll for available runs. Returns immediately if a run is available, otherwise holds the connection open.

```
GET /launcher/runs?launcher_id={launcher_id}
```

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `launcher_id` | Yes | The registered launcher ID |

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

**Response (No Runs):** `204 No Content`

**Response (Deregistered):**
```json
{
  "deregistered": true
}
```

### Report Run Started

Report that run execution has started.

```
POST /launcher/runs/{run_id}/started
```

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

### Report Run Completed

Report that run completed successfully.

```
POST /launcher/runs/{run_id}/completed
```

**Request Body:**
```json
{
  "launcher_id": "lnch_abc123",
  "status": "success"
}
```

**Response:**
```json
{
  "ok": true
}
```

### Report Run Failed

Report that run execution failed.

```
POST /launcher/runs/{run_id}/failed
```

**Request Body:**
```json
{
  "launcher_id": "lnch_abc123",
  "error": "Error message describing what went wrong"
}
```

**Response:**
```json
{
  "ok": true
}
```

## Implementation Details

### Run Queue

**File:** `servers/agent-coordinator/services/run_queue.py`

The run queue is an in-memory, thread-safe singleton that stores runs in a dictionary with locking for atomic operations.

```python
class RunQueue:
    def add_run(run_create: RunCreate) -> Run
    def claim_run(launcher_id: str) -> Optional[Run]
    def get_run(run_id: str) -> Optional[Run]
    def update_run_status(run_id: str, status: RunStatus, error: str = None) -> Optional[Run]
    def get_run_by_session_name(session_name: str) -> Optional[Run]
```

Key characteristics:
- Runs are **not persisted** to SQLite (in-memory only)
- Thread-safe with `threading.Lock` for concurrent access
- FIFO ordering for run claiming
- Module-level singleton: `run_queue`

### Agent Launcher Components

| Component | File | Purpose |
|-----------|------|---------|
| `RunPoller` | `servers/agent-launcher/lib/poller.py` | Background thread polling for pending runs |
| `RunExecutor` | `servers/agent-launcher/lib/executor.py` | Spawns ao-start/ao-resume subprocesses |
| `RunSupervisor` | `servers/agent-launcher/lib/supervisor.py` | Monitors running runs, reports completion |
| `CoordinatorAPIClient` | `servers/agent-launcher/lib/api_client.py` | HTTP client for launcher endpoints |

### Long-Polling Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `LAUNCHER_POLL_TIMEOUT` | `30` | Seconds to hold connection open |
| `LAUNCHER_HEARTBEAT_INTERVAL` | `60` | Seconds between heartbeats |
| `LAUNCHER_HEARTBEAT_TIMEOUT` | `120` | Seconds before launcher marked stale |

## Usage Examples

### Dashboard

The dashboard creates runs when users start or resume sessions:

```typescript
// dashboard/src/services/chatService.ts
const response = await agentOrchestratorApi.post('/runs', {
  type: 'start_session',
  session_name: sessionName,
  agent_name: agentName,
  prompt: prompt,
  project_dir: projectDir
});
```

### CLI Commands

The orchestrator plugin uses `RunClient` to create runs and wait for completion:

```python
# plugins/orchestrator/skills/orchestrator/commands/lib/run_client.py
client = RunClient(api_url)
result = client.start_session(
    session_name="my-task",
    prompt="Do something",
    agent_name="researcher"
)
```

### Parent-Child Callbacks

Runs support hierarchical orchestration through `parent_session_name`:

1. Parent agent starts child with `parent_session_name` set
2. Agent Coordinator tracks the relationship
3. When child completes, Callback Processor notifies parent
4. Parent resumes with child's result

```
Parent (orchestrator)          Child (worker)
       │                            │
       │ POST /runs                 │
       │ parent_session_name=self   │
       │───────────────────────────►│
       │                            │
       │ continues work...          │ executes task...
       │                            │
       │ becomes idle               │ completes
       │                            │
       │◄─── callback notification ─┤
       │     (via resume run)       │
       │                            │
       ▼
  resumes with child result
```

## Related Documentation

- [API.md](./API.md) - Complete REST API reference
- [DATA_MODELS.md](./DATA_MODELS.md) - All data model schemas
- [USAGE.md](./USAGE.md) - Quick start guide
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
