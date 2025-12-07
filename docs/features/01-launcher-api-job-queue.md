# Work Package 1: Launcher API & Job Queue

**Reference**: [agent-callback-architecture.md](./agent-callback-architecture.md)
- Read sections: "Architecture", "API Specification", "Implementation Plan > Phase 1"

## Goal

Add job queue infrastructure and Launcher API endpoints to Agent Runtime. After completion, the system can accept jobs via API and queue them for a launcher to poll.

## Runnable State After Completion

- Dashboard continues working via existing Agent Control API (unchanged)
- New `/launcher/*` and `/jobs` endpoints available
- Jobs can be created and queried via API
- Ready for Agent Launcher (Package 2) to connect

## Files to Create

| File | Purpose |
|------|---------|
| `servers/agent-runtime/services/job_queue.py` | Thread-safe in-memory job queue |
| `servers/agent-runtime/services/launcher_registry.py` | Launcher registration tracking |
| `servers/agent-runtime/routers/launcher.py` | Launcher API endpoints |
| `servers/agent-runtime/routers/jobs.py` | Job creation/query endpoints |
| `servers/agent-runtime/models/job.py` | Job Pydantic models |

## Files to Modify

| File | Changes |
|------|---------|
| `servers/agent-runtime/main.py` | Register new routers |

## Implementation Tasks

### 1. Job Models (`models/job.py`)

Create Pydantic models:
- `JobType` enum: `start_session`, `resume_session`
- `JobStatus` enum: `pending`, `claimed`, `running`, `completed`, `failed`
- `JobCreate`: type, session_name, agent_name (optional), prompt, project_dir (optional)
- `Job`: adds job_id, status, timestamps, launcher_id, error

### 2. Job Queue Service (`services/job_queue.py`)

Thread-safe queue with:
- `add_job(job_create) -> Job` - creates job with pending status
- `claim_job(launcher_id) -> Optional[Job]` - atomic claim operation
- `get_job(job_id) -> Optional[Job]` - lookup by ID
- `update_job_status(job_id, status, error=None)` - status transitions
- `get_pending_jobs() -> List[Job]` - for debugging

Use `threading.Lock` for concurrency safety.

### 3. Launcher Registry (`services/launcher_registry.py`)

Track registered launchers:
- `register_launcher() -> launcher_id` - generate UUID, store with timestamp
- `heartbeat(launcher_id)` - update last_seen timestamp
- `get_launcher(launcher_id) -> Optional[LauncherInfo]`
- `is_launcher_alive(launcher_id) -> bool`

### 4. Launcher Router (`routers/launcher.py`)

Endpoints per spec:
- `POST /launcher/register` - returns launcher_id, poll config
- `GET /launcher/jobs?launcher_id=X` - long-poll (30s timeout)
- `POST /launcher/jobs/{job_id}/started` - mark job running
- `POST /launcher/jobs/{job_id}/completed` - mark job completed
- `POST /launcher/jobs/{job_id}/failed` - mark job failed with error
- `POST /launcher/heartbeat` - keep launcher alive

Long-poll implementation: use `asyncio.sleep` in loop checking for jobs.

### 5. Jobs Router (`routers/jobs.py`)

Endpoints:
- `POST /jobs` - create new job, return job_id
- `GET /jobs/{job_id}` - get job status

### 6. Wire Up in Main (`main.py`)

- Import and include launcher router
- Import and include jobs router
- Initialize job_queue and launcher_registry as module-level singletons

## Testing Checklist

- [ ] Create a job via `POST /jobs`
- [ ] Query job via `GET /jobs/{job_id}` - shows pending
- [ ] Register launcher via `POST /launcher/register`
- [ ] Poll for job - receives the created job
- [ ] Report started/completed - job status updates
- [ ] Dashboard still works (unchanged)

## Notes

- Keep job queue in-memory (acceptable for POC per spec)
- No authentication on launcher endpoints (POC scope)
- Job timeout handling deferred to future work
