# Refactor Validation

**Date:** 2025-12-17
**Branch:** `refactor/component-renamings`
**Commits:** 3cf44c7, 35d9ec7, 117c4ad

## What Changed

| Old | New | Scope |
|-----|-----|-------|
| Agent Runtime | Agent Coordinator | Server, Docker, Makefile, docs |
| Jobs | Runs | API (`/jobs` → `/runs`), classes, variables |
| Agent Launcher | Agent Runner | Server, API (`/launcher` → `/runner`), dashboard |

---

## Static Validation Completed

The following checks were performed to verify the refactoring at code level:

| Check | Status | Details |
|-------|--------|---------|
| Python compile (Coordinator) | PASS | `main.py`, `run_queue.py`, `runner_registry.py` |
| Python compile (Runner) | PASS | All `lib/*.py` files |
| Dashboard TypeScript build | PASS | `npm run build` - 761KB bundle |
| Old terminology grep | PASS | No `agent-runtime`, `agent-launcher` found |
| Old API paths grep | PASS | No `/jobs`, `/launcher` endpoints found |
| Old class names grep | PASS | No `JobQueue`, `LauncherRegistry`, `AgentRuntime` |
| Docker config | PASS | Service `agent-coordinator`, volume `coordinator-data` |
| Makefile targets | PASS | `restart-coordinator` target present |
| MCP API paths | PASS | Uses `/runs`, `run_id` correctly |
| Plugin CLI | PASS | `run_client.py` uses new terminology |
| Agent Runner script | PASS | Uses `Runner`, `runner_id`, `RunPoller` |
| Dashboard routes | PASS | Route `/runners`, component `Runners.tsx` |

---

## Runtime Validation TODO

The static checks confirm code correctness. The following runtime validation is still needed:

### 1. Docker Compose Full Stack
```bash
make build
make start
make health
```
- Verify all containers start without errors
- Check health endpoints respond correctly
- Verify inter-service communication works

### 2. Integration Tests
```bash
/tests:setup
/tests:run
/tests:teardown
```
- Run full integration test suite
- Verify agent runs execute correctly
- Check session lifecycle works end-to-end

### 3. Manual Service Verification
```bash
# Start Agent Coordinator
cd servers/agent-coordinator && uv run python main.py

# Start Agent Runner (separate terminal)
./servers/agent-runner/agent-runner

# Verify new API endpoints
curl http://localhost:8765/runs
curl http://localhost:8765/runners
```

### 4. Dashboard Verification
- Navigate to http://localhost:3000
- Check `/runners` page shows connected runners
- Verify sessions can be created and monitored

---

## Key API Changes

| Old Endpoint | New Endpoint |
|--------------|--------------|
| `GET /jobs` | `GET /runs` |
| `POST /jobs` | `POST /runs` |
| `GET /jobs/{id}` | `GET /runs/{id}` |
| `GET /launchers` | `GET /runners` |
| `POST /launchers/register` | `POST /runners/register` |
| `DELETE /launchers/{id}` | `DELETE /runners/{id}` |

## Key Field Renames

| Old Field | New Field |
|-----------|-----------|
| `job_id` | `run_id` |
| `launcher_id` | `runner_id` |
| `JobStatus` | `RunStatus` |
| `LauncherStatus` | `RunnerStatus` |
