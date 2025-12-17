# Implementation Guide: Jobs → Agent Runs

**Sequence:** 2 of 3
**Estimated Changes:** ~182 references
**Dependencies:** Complete "Agent Runtime → Agent Coordinator" first

---

## Context

This is the second of three terminology renames. It changes the conceptual model from "jobs" to "runs" to better reflect the relationship between sessions and their executions.

### What is a Job (currently)?

A unit of work queued in the Agent Coordinator for a launcher to execute. Types:
- `start_session` - First execution, creates new session
- `resume_session` - Subsequent execution, continues session
- `stop_command` - Termination signal

### Why Rename to "Agent Run"?

"Job" is generic and doesn't capture the relationship:
- **Sessions** are persistent entities with state and history
- **Runs** are discrete executions of a session

A session can have multiple runs over its lifetime:
```
Session (persistent)
├── Run 1 (start)
├── Run 2 (resume)
├── Run 3 (resume)
└── ...
```

"Agent Run" clarifies this relationship and pairs naturally with "Agent Runner" (implementation 3).

---

## Scope

### What Changes

1. API endpoint paths (`/jobs/*` → `/runs/*`)
2. Python classes and enums
3. Method names
4. Variable names (`job_id` → `run_id`)
5. TypeScript interfaces
6. Documentation
7. Log messages

### What Does NOT Change

- Enum string values (`START_SESSION`, `RESUME_SESSION`, `PENDING`, etc.)
- Session identifiers (`session_name`, `session_id`)
- The `/launcher/*` prefix (that changes in implementation 3)

---

## Implementation Checklist

### Phase 1: Core Service (servers/agent-coordinator/services/job_queue.py)

**Rename file:** `job_queue.py` → `run_queue.py`

#### Class Renames

| Current | New |
|---------|-----|
| `class JobType` | `class RunType` |
| `class JobStatus` | `class RunStatus` |
| `class JobCreate` | `class RunCreate` |
| `class Job` | `class Run` |
| `class JobQueue` | `class RunQueue` |
| `job_queue` (singleton) | `run_queue` |

#### Method Renames

| Current | New |
|---------|-----|
| `add_job()` | `add_run()` |
| `claim_job()` | `claim_run()` |
| `get_job()` | `get_run()` |
| `update_job_status()` | `update_run_status()` |
| `get_pending_jobs()` | `get_pending_runs()` |
| `get_all_jobs()` | `get_all_runs()` |
| `get_job_by_session_name()` | `get_run_by_session_name()` |

**Note:** Keep enum VALUES unchanged:
```python
class RunType(str, Enum):
    START_SESSION = "start_session"    # Keep this value
    RESUME_SESSION = "resume_session"  # Keep this value
```

### Phase 2: Main API (servers/agent-coordinator/main.py)

#### Import Update
```python
# Old
from services.job_queue import JobQueue, Job, JobCreate, JobStatus, JobType, job_queue

# New
from services.run_queue import RunQueue, Run, RunCreate, RunStatus, RunType, run_queue
```

#### Request/Response Models

| Current | New |
|---------|-----|
| `JobCompletedRequest` | `RunCompletedRequest` |
| `JobFailedRequest` | `RunFailedRequest` |
| `JobStoppedRequest` | `RunStoppedRequest` |

#### API Endpoints

| Current Path | New Path |
|--------------|----------|
| `POST /jobs` | `POST /runs` |
| `GET /jobs/{job_id}` | `GET /runs/{run_id}` |
| `POST /jobs/{job_id}/stop` | `POST /runs/{run_id}/stop` |
| `GET /launcher/jobs` | `GET /launcher/runs` |
| `POST /launcher/jobs/{job_id}/started` | `POST /launcher/runs/{run_id}/started` |
| `POST /launcher/jobs/{job_id}/completed` | `POST /launcher/runs/{run_id}/completed` |
| `POST /launcher/jobs/{job_id}/failed` | `POST /launcher/runs/{run_id}/failed` |
| `POST /launcher/jobs/{job_id}/stopped` | `POST /launcher/runs/{run_id}/stopped` |

#### Variable Names (throughout main.py)

| Current | New |
|---------|-----|
| `job` | `run` |
| `job_id` | `run_id` |
| `job_create` | `run_create` |
| `stop_jobs` | `stop_runs` |

#### Response Fields

Update all response dictionaries:
```python
# Old
return {"job_id": job.job_id, "status": job.status}

# New
return {"run_id": run.run_id, "status": run.status}
```

### Phase 3: Agent Launcher (servers/agent-launcher/)

#### lib/api_client.py

| Current | New |
|---------|-----|
| `class Job` | `class Run` |
| `Job.job_id` | `Run.run_id` |
| `PollResult.job` | `PollResult.run` |
| `PollResult.stop_jobs` | `PollResult.stop_runs` |

Update endpoint URLs:
```python
# Old
f"{self.base_url}/launcher/jobs"

# New
f"{self.base_url}/launcher/runs"
```

#### lib/poller.py

| Current | New |
|---------|-----|
| `class JobPoller` | `class RunPoller` |
| `poll_job()` | `poll_run()` |
| `result.job` | `result.run` |
| `result.stop_jobs` | `result.stop_runs` |

#### lib/executor.py

| Current | New |
|---------|-----|
| `class JobExecutor` | `class RunExecutor` |
| `execute_job()` | `execute_run()` |
| `job` parameter | `run` parameter |

#### lib/supervisor.py

| Current | New |
|---------|-----|
| `class JobSupervisor` | `class RunSupervisor` |
| Job-related variables | Run-related variables |

#### lib/registry.py (if exists)

| Current | New |
|---------|-----|
| `RunningJobsRegistry` | `RunningRunsRegistry` |

### Phase 4: Dashboard (dashboard/src/)

#### services/chatService.ts

| Current | New |
|---------|-----|
| `CreateJobRequest` | `CreateRunRequest` |
| `CreateJobResponse` | `CreateRunResponse` |
| `job_id` field | `run_id` field |
| `'/jobs'` endpoint | `'/runs'` endpoint |

```typescript
// Old
const response = await api.post('/jobs', { type: 'start_session', ... });
return response.data.job_id;

// New
const response = await api.post('/runs', { type: 'start_session', ... });
return response.data.run_id;
```

### Phase 5: Plugin CLI (plugins/orchestrator/)

#### commands/lib/job_client.py

**Rename file:** `job_client.py` → `run_client.py`

| Current | New |
|---------|-----|
| `class JobClient` | `class RunClient` |
| `_create_job()` | `_create_run()` |
| `_get_job()` | `_get_run()` |
| `JobClientError` | `RunClientError` |
| `JobTimeoutError` | `RunTimeoutError` |
| `JobFailedError` | `RunFailedError` |

Update endpoint URLs and response parsing.

### Phase 6: Stop Command Queue

#### servers/agent-coordinator/services/stop_command_queue.py

Update parameter names and comments:
```python
# Old
def add_stop(self, launcher_id: str, job_id: str):

# New
def add_stop(self, launcher_id: str, run_id: str):
```

### Phase 7: Documentation

#### Rename Files

| Current | New |
|---------|-----|
| `docs/agent-coordinator/JOBS_API.md` | `docs/agent-coordinator/RUNS_API.md` |
| `docs/agent-coordinator/JOB_EXECUTION_FLOW.md` | `docs/agent-coordinator/RUN_EXECUTION_FLOW.md` |
| `docs/adr/ADR-008-concurrent-job-execution.md` | `docs/adr/ADR-008-concurrent-run-execution.md` |

#### Update Content

Replace throughout all documentation:
- "Jobs API" → "Runs API"
- "job_id" → "run_id"
- "Job lifecycle" → "Run lifecycle"
- "POST /jobs" → "POST /runs"
- "Job Queue" → "Run Queue"

Files to update:
- docs/agent-coordinator/DATA_MODELS.md
- docs/agent-coordinator/API.md
- docs/ARCHITECTURE.md
- docs/adr/ADR-001-job-session-separation.md
- docs/features/agent-callback-architecture.md

### Phase 8: Log Messages

Update all log messages in main.py and launcher files:

| Current | New |
|---------|-----|
| `"Created job {job.job_id}"` | `"Created run {run.run_id}"` |
| `"Job {job_id} started"` | `"Run {run_id} started"` |
| `"Job {job_id} completed"` | `"Run {run_id} completed"` |
| `"Job {job_id} failed"` | `"Run {run_id} failed"` |
| `"Job {job_id} stopped"` | `"Run {run_id} stopped"` |
| `"Launcher claimed job"` | `"Launcher claimed run"` |

---

## Verification Steps

1. **Python syntax check:**
   ```bash
   uv run python -m py_compile servers/agent-coordinator/main.py
   uv run python -m py_compile servers/agent-coordinator/services/run_queue.py
   ```

2. **Start coordinator:**
   ```bash
   cd servers/agent-coordinator && uv run python main.py
   ```

3. **Test API endpoints:**
   ```bash
   curl http://localhost:8765/runs  # Should work
   curl http://localhost:8765/jobs  # Should 404
   ```

4. **Grep verification:**
   ```bash
   # Should return minimal results
   grep -r "job_id\|JobStatus\|JobQueue\|/jobs" --include="*.py" servers/ | grep -v __pycache__
   ```

---

## Breaking Changes

This is a **breaking API change**:
- All clients using `/jobs` endpoints must update to `/runs`
- Response field `job_id` changes to `run_id`
- Consider version bump

---

## Next Steps

After completing this rename, proceed to:
- **Implementation 3:** Agent Launcher → Agent Runner (`implementation_03_launcher_to_runner.md`)
