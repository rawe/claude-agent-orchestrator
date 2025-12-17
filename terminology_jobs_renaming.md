# Jobs → Agent Runs: Renaming Analysis

This document catalogs all occurrences of "Jobs" / "Jobs API" terminology that need to be renamed when transitioning to "Agent Runs" / "Runs API".

**Total estimated changes:** ~182 references across the codebase.

---

## 1. API Endpoints

| Current | New | Method | Description |
|---------|-----|--------|-------------|
| `POST /jobs` | `POST /runs` | POST | Create a new run |
| `GET /jobs/{job_id}` | `GET /runs/{run_id}` | GET | Get run details |
| `POST /jobs/{job_id}/stop` | `POST /runs/{run_id}/stop` | POST | Stop a running run |
| `GET /launcher/jobs` | `GET /runner/runs` | GET | Poll for pending runs |
| `POST /launcher/jobs/{job_id}/started` | `POST /runner/runs/{run_id}/started` | POST | Report run started |
| `POST /launcher/jobs/{job_id}/completed` | `POST /runner/runs/{run_id}/completed` | POST | Report run completed |
| `POST /launcher/jobs/{job_id}/failed` | `POST /runner/runs/{run_id}/failed` | POST | Report run failed |
| `POST /launcher/jobs/{job_id}/stopped` | `POST /runner/runs/{run_id}/stopped` | POST | Report run stopped |

---

## 2. Python Classes (job_queue.py)

| Current | New | Type |
|---------|-----|------|
| `class JobType` | `class RunType` | Enum |
| `class JobStatus` | `class RunStatus` | Enum |
| `class JobCreate` | `class RunCreate` | Pydantic model |
| `class Job` | `class Run` | Pydantic model |
| `class JobQueue` | `class RunQueue` | Service class |
| `job_queue` (singleton) | `run_queue` | Instance |

**Note:** Enum values (`START_SESSION`, `RESUME_SESSION`, `PENDING`, `CLAIMED`, etc.) stay unchanged.

---

## 3. Python Classes (main.py)

| Current | New | Type |
|---------|-----|------|
| `JobCompletedRequest` | `RunCompletedRequest` | Pydantic model |
| `JobFailedRequest` | `RunFailedRequest` | Pydantic model |
| `JobStoppedRequest` | `RunStoppedRequest` | Pydantic model |

---

## 4. Python Classes (api_client.py - Agent Launcher)

| Current | New | Type |
|---------|-----|------|
| `class Job` | `class Run` | Dataclass |
| `Job.job_id` | `Run.run_id` | Field |
| `PollResult.job` | `PollResult.run` | Field |
| `PollResult.stop_jobs` | `PollResult.stop_runs` | Field |

---

## 5. Python Classes (Agent Launcher lib/)

| Current | New | File |
|---------|-----|------|
| `JobPoller` | `RunPoller` | poller.py |
| `JobExecutor` | `RunExecutor` | executor.py |
| `JobSupervisor` | `RunSupervisor` | supervisor.py |
| `RunningJobsRegistry` | `RunningRunsRegistry` | registry.py |

---

## 6. Method Names (RunQueue)

| Current | New |
|---------|-----|
| `add_job()` | `add_run()` |
| `claim_job()` | `claim_run()` |
| `get_job()` | `get_run()` |
| `update_job_status()` | `update_run_status()` |
| `get_pending_jobs()` | `get_pending_runs()` |
| `get_all_jobs()` | `get_all_runs()` |
| `get_job_by_session_name()` | `get_run_by_session_name()` |

---

## 7. Variable Names

| Current | New | Context |
|---------|-----|---------|
| `job` | `run` | Local variables throughout |
| `job_id` | `run_id` | Parameters, responses |
| `job_create` | `run_create` | Parameters |
| `stop_jobs` | `stop_runs` | Collections |

---

## 8. TypeScript (Dashboard)

| Current | New | File |
|---------|-----|------|
| `CreateJobRequest` | `CreateRunRequest` | chatService.ts |
| `CreateJobResponse` | `CreateRunResponse` | chatService.ts |
| `job_id` (field) | `run_id` | chatService.ts |
| `/jobs` (API call) | `/runs` | chatService.ts |

---

## 9. Plugin CLI (job_client.py)

| Current | New |
|---------|-----|
| `JobClient` | `RunClient` |
| `_create_job()` | `_create_run()` |
| `_get_job()` | `_get_run()` |
| `JobClientError` | `RunClientError` |
| `JobTimeoutError` | `RunTimeoutError` |
| `JobFailedError` | `RunFailedError` |

**File rename:** `job_client.py` → `run_client.py`

---

## 10. Service File Rename

| Current | New |
|---------|-----|
| `services/job_queue.py` | `services/run_queue.py` |

---

## 11. Documentation Files

| Current | New | Action |
|---------|-----|--------|
| `docs/agent-runtime/JOBS_API.md` | `docs/agent-runtime/RUNS_API.md` | RENAME |
| `docs/agent-runtime/JOB_EXECUTION_FLOW.md` | `docs/agent-runtime/RUN_EXECUTION_FLOW.md` | RENAME |
| `docs/adr/ADR-001-job-session-separation.md` | - | UPDATE content |
| `docs/adr/ADR-008-concurrent-job-execution.md` | `docs/adr/ADR-008-concurrent-run-execution.md` | RENAME |
| `docs/agent-runtime/DATA_MODELS.md` | - | UPDATE "Job" → "Run" |
| `docs/agent-runtime/API.md` | - | UPDATE endpoints |
| `docs/ARCHITECTURE.md` | - | UPDATE references |

---

## 12. Log Messages

| Current | New |
|---------|-----|
| `"Created job {job.job_id}"` | `"Created run {run.run_id}"` |
| `"Job {job_id} started"` | `"Run {run_id} started"` |
| `"Job {job_id} completed"` | `"Run {run_id} completed"` |
| `"Job {job_id} failed"` | `"Run {run_id} failed"` |
| `"Job {job_id} stopped"` | `"Run {run_id} stopped"` |
| `"Pending job cancelled"` | `"Pending run cancelled"` |
| `"Stop requested for job"` | `"Stop requested for run"` |
| `"Launcher claimed job"` | `"Runner claimed run"` |

---

## Summary

| Category | Count | Priority |
|----------|-------|----------|
| API endpoints | 8 | Critical |
| Python classes | 12+ | Critical |
| Method names | 7 | High |
| TypeScript interfaces | 2 | High |
| Variable names | 30+ | High |
| Service file rename | 2 | High |
| Documentation files | 7+ | Medium |
| Log messages | 9+ | Medium |

---

## Important Notes

- **Enum values stay unchanged:** `START_SESSION`, `RESUME_SESSION`, `PENDING`, `CLAIMED`, etc.
- **Session identifiers unchanged:** `session_name`, `session_id` are different concepts
- **Breaking API change:** Requires version bump and client updates
- **Combined with Agent Runner rename:** `/launcher/jobs/` → `/runner/runs/`
