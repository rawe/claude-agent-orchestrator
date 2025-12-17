# Jobs API

The Jobs API enables distributed agent execution by separating orchestration (Agent Coordinator) from execution (Agent Launcher). This allows the Agent Coordinator to be containerized while launchers run on host machines where agent frameworks are installed.

## Architecture

```
ao-* CLI / Dashboard / MCP Server
              │
              │ POST /jobs
              ▼
┌─────────────────────────────────┐
│       Agent Coordinator :8765       │
│  ┌───────────────────────────┐  │
│  │   In-Memory Job Queue     │  │
│  │  (thread-safe, singleton) │  │
│  └───────────────────────────┘  │
└──────────────┬──────────────────┘
               │ Long-poll GET /launcher/jobs
               ▼
┌─────────────────────────────────┐
│        Agent Launcher           │
│  - Polls for pending jobs       │
│  - Concurrent execution         │
│  - Reports job status           │
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

## Job Lifecycle

Jobs follow a state machine with five statuses:

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
| `pending` | Job created, waiting for a launcher to claim it |
| `claimed` | Launcher claimed the job, preparing to execute |
| `running` | Job execution has started |
| `completed` | Job completed successfully |
| `failed` | Job execution failed |

## Data Model

### Job

```json
{
  "job_id": "job_abc123def456",
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
| `job_id` | string | Unique identifier (e.g., `job_abc123def456`) |
| `type` | enum | `start_session` or `resume_session` |
| `session_name` | string | Name of the session to start/resume |
| `agent_name` | string? | Optional agent blueprint to use |
| `prompt` | string | User prompt/instruction for the agent |
| `project_dir` | string? | Optional project directory path |
| `parent_session_name` | string? | Parent session name for callback support |
| `status` | enum | Current job status |
| `launcher_id` | string? | ID of the launcher that claimed/executed the job |
| `error` | string? | Error message if job failed |
| `created_at` | ISO 8601 | Timestamp when job was created |
| `claimed_at` | ISO 8601? | Timestamp when launcher claimed the job |
| `started_at` | ISO 8601? | Timestamp when execution started |
| `completed_at` | ISO 8601? | Timestamp when job completed or failed |

### Job Types

| Type | Description |
|------|-------------|
| `start_session` | Start a new Claude Code session |
| `resume_session` | Resume an existing session with a new prompt |

## API Endpoints

### Create Job

Create a new job for a launcher to execute.

```
POST /jobs
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
  "job_id": "job_abc123",
  "status": "pending"
}
```

### Get Job

Get job status and details.

```
GET /jobs/{job_id}
```

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

**Error:** `404 Not Found` if job doesn't exist.

## Launcher Endpoints

These endpoints are used by the Agent Launcher to poll for and report on jobs.

### Poll for Jobs

Long-poll for available jobs. Returns immediately if a job is available, otherwise holds the connection open.

```
GET /launcher/jobs?launcher_id={launcher_id}
```

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `launcher_id` | Yes | The registered launcher ID |

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

**Response (No Jobs):** `204 No Content`

**Response (Deregistered):**
```json
{
  "deregistered": true
}
```

### Report Job Started

Report that job execution has started.

```
POST /launcher/jobs/{job_id}/started
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

### Report Job Completed

Report that job completed successfully.

```
POST /launcher/jobs/{job_id}/completed
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

### Report Job Failed

Report that job execution failed.

```
POST /launcher/jobs/{job_id}/failed
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

### Job Queue

**File:** `servers/agent-coordinator/services/job_queue.py`

The job queue is an in-memory, thread-safe singleton that stores jobs in a dictionary with locking for atomic operations.

```python
class JobQueue:
    def add_job(job_create: JobCreate) -> Job
    def claim_job(launcher_id: str) -> Optional[Job]
    def get_job(job_id: str) -> Optional[Job]
    def update_job_status(job_id: str, status: JobStatus, error: str = None) -> Optional[Job]
    def get_job_by_session_name(session_name: str) -> Optional[Job]
```

Key characteristics:
- Jobs are **not persisted** to SQLite (in-memory only)
- Thread-safe with `threading.Lock` for concurrent access
- FIFO ordering for job claiming
- Module-level singleton: `job_queue`

### Agent Launcher Components

| Component | File | Purpose |
|-----------|------|---------|
| `JobPoller` | `servers/agent-launcher/lib/poller.py` | Background thread polling for pending jobs |
| `JobExecutor` | `servers/agent-launcher/lib/executor.py` | Spawns ao-start/ao-resume subprocesses |
| `JobSupervisor` | `servers/agent-launcher/lib/supervisor.py` | Monitors running jobs, reports completion |
| `CoordinatorAPIClient` | `servers/agent-launcher/lib/api_client.py` | HTTP client for launcher endpoints |

### Long-Polling Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `LAUNCHER_POLL_TIMEOUT` | `30` | Seconds to hold connection open |
| `LAUNCHER_HEARTBEAT_INTERVAL` | `60` | Seconds between heartbeats |
| `LAUNCHER_HEARTBEAT_TIMEOUT` | `120` | Seconds before launcher marked stale |

## Usage Examples

### Dashboard

The dashboard creates jobs when users start or resume sessions:

```typescript
// dashboard/src/services/chatService.ts
const response = await agentOrchestratorApi.post('/jobs', {
  type: 'start_session',
  session_name: sessionName,
  agent_name: agentName,
  prompt: prompt,
  project_dir: projectDir
});
```

### CLI Commands

The orchestrator plugin uses `JobClient` to create jobs and wait for completion:

```python
# plugins/orchestrator/skills/orchestrator/commands/lib/job_client.py
client = JobClient(api_url)
result = client.start_session(
    session_name="my-task",
    prompt="Do something",
    agent_name="researcher"
)
```

### Parent-Child Callbacks

Jobs support hierarchical orchestration through `parent_session_name`:

1. Parent agent starts child with `parent_session_name` set
2. Agent Coordinator tracks the relationship
3. When child completes, Callback Processor notifies parent
4. Parent resumes with child's result

```
Parent (orchestrator)          Child (worker)
       │                            │
       │ POST /jobs                 │
       │ parent_session_name=self   │
       │───────────────────────────►│
       │                            │
       │ continues work...          │ executes task...
       │                            │
       │ becomes idle               │ completes
       │                            │
       │◄─── callback notification ─┤
       │     (via resume job)       │
       │                            │
       ▼
  resumes with child result
```

## Related Documentation

- [API.md](./API.md) - Complete REST API reference
- [DATA_MODELS.md](./DATA_MODELS.md) - All data model schemas
- [USAGE.md](./USAGE.md) - Quick start guide
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
