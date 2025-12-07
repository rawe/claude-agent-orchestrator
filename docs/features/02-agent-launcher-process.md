# Work Package 2: Agent Launcher Process

**Reference**: [agent-callback-architecture.md](./agent-callback-architecture.md)
- Read sections: "Architecture > Launcher Lifecycle", "Concurrent Execution Model", "Implementation Plan > Phase 2", "File Structure", "Configuration"

## Goal

Create standalone Agent Launcher process that polls Agent Runtime for jobs and executes `ao-start`/`ao-resume` commands as subprocesses.

## Runnable State After Completion

- Launcher starts and registers with Agent Runtime
- Jobs created via API are picked up and executed
- Multiple jobs can run concurrently
- Dashboard can start sessions via Job API (if Package 3 done, otherwise via curl/API)

## Files to Create

| File | Purpose |
|------|---------|
| `servers/agent-launcher/agent-launcher` | Main script (uv run --script) |
| `servers/agent-launcher/lib/__init__.py` | Package marker |
| `servers/agent-launcher/lib/config.py` | Configuration loading |
| `servers/agent-launcher/lib/registry.py` | Running Jobs Registry (thread-safe) |
| `servers/agent-launcher/lib/poller.py` | Poll Thread - fetches jobs |
| `servers/agent-launcher/lib/supervisor.py` | Supervisor Thread - monitors processes |
| `servers/agent-launcher/lib/executor.py` | Job execution (subprocess spawning) |
| `servers/agent-launcher/lib/api_client.py` | HTTP client for Agent Runtime |

## Implementation Tasks

### 1. Configuration (`lib/config.py`)

Environment variables:
- `AGENT_RUNTIME_URL` (default: `http://localhost:8765`)
- `POLL_TIMEOUT` (default: `30`)
- `HEARTBEAT_INTERVAL` (default: `60`)
- `PROJECT_DIR` (default: cwd)

Pattern: follow existing `config.py` in ao-* commands.

### 2. API Client (`lib/api_client.py`)

HTTP client wrapping launcher endpoints:
- `register() -> RegistrationResponse`
- `poll_job(launcher_id) -> Optional[Job]`
- `report_started(launcher_id, job_id)`
- `report_completed(launcher_id, job_id)`
- `report_failed(launcher_id, job_id, error)`
- `heartbeat(launcher_id)`

Use `httpx` (sync client). Handle timeouts gracefully.

### 3. Running Jobs Registry (`lib/registry.py`)

Thread-safe dict tracking active jobs:
```python
running_jobs: Dict[str, RunningJob]  # job_id -> RunningJob
# RunningJob = { process: Popen, started_at: datetime }
```

Methods:
- `add_job(job_id, process)`
- `remove_job(job_id)`
- `get_running_jobs() -> Dict[str, RunningJob]`
- `get_job(job_id) -> Optional[RunningJob]`

Use `threading.Lock`.

### 4. Job Executor (`lib/executor.py`)

Maps job types to commands:
- `start_session` → `ao-start {session_name} --agent {agent_name} --prompt "{prompt}" --project-dir {project_dir}`
- `resume_session` → `ao-resume {session_name} --prompt "{prompt}"`

Key responsibilities:
- **Command discovery**: Find ao-* commands relative to project root (see MCP server pattern in `interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py`)
- **Environment setup**: Set `AGENT_SESSION_NAME` env var (for Package 4)
- **Subprocess spawn**: Use `subprocess.Popen()` with stdout/stderr capture
- Return the Popen object for supervisor to monitor

### 5. Poll Thread (`lib/poller.py`)

Background thread that:
1. Calls `api_client.poll_job(launcher_id)`
2. On timeout (None returned) → retry immediately
3. On job received:
   - Spawn subprocess via executor
   - Add to registry
   - Report started to API
4. Loop forever

Handle connection errors with backoff.

### 6. Supervisor Thread (`lib/supervisor.py`)

Background thread that:
1. Every ~1 second, iterate running jobs
2. Check `process.poll()` for each
3. If process finished:
   - If returncode == 0: report_completed
   - Else: report_failed with stderr
   - Remove from registry

### 7. Main Script (`agent-launcher`)

Entry point following ao-* pattern:
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "typer"]
# ///
```

Main flow:
1. Load config
2. Register with Agent Runtime
3. Start poll thread
4. Start supervisor thread
5. Start heartbeat thread
6. Wait for interrupt (Ctrl+C)
7. Graceful shutdown

### 8. Heartbeat Thread

Simple thread that:
- Every `HEARTBEAT_INTERVAL` seconds
- Calls `api_client.heartbeat(launcher_id)`

## Testing Checklist

- [ ] `./servers/agent-launcher/agent-launcher` starts without error
- [ ] Launcher registers with Agent Runtime (check logs)
- [ ] Create job via API → Launcher picks it up
- [ ] `ao-start` executes and session appears in Agent Runtime
- [ ] Multiple jobs run concurrently
- [ ] Job completion reported to Agent Runtime
- [ ] Ctrl+C gracefully stops launcher

## Notes

- For command discovery, look at `interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py` lines ~50-70
- Logging should be concise but visible for debugging
- No need for `AGENT_ORCHESTRATOR_COMMAND_PATH` override (per spec)
