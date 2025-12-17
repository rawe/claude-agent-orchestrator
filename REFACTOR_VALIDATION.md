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

## Validation Strategy

**Approach:** One phase per session to ensure thorough validation and easy rollback if issues are found.

**Sessions:**
- Session 1: Docker Compose Full Stack (Phase 1)
- Session 2: Integration Tests (Phase 2)
- Session 3: Manual Service Verification (Phase 3)
- Session 4: Dashboard Verification (Phase 4)

Each phase is documented with results before proceeding to the next session.

---

## Runtime Validation

The static checks confirm code correctness. The following runtime validation is tracked below:

### Phase 1: Docker Compose Full Stack ✅ PASSED

**Session Date:** 2025-12-17

| Step | Command | Result |
|------|---------|--------|
| Build | `make build` | All 3 images built successfully |
| Start | `make start` | All 5 containers started |
| Health | `make health` | All health endpoints returned 200 |

**Container Status:**

| Container | Status | Port |
|-----------|--------|------|
| agent-coordinator | healthy | 8765 |
| dashboard | up | 3000 |
| neo4j | healthy | 7475/7688 |
| context-store | healthy | 8766 |
| elasticsearch | healthy | 9200 |

**API Endpoint Verification:**

| Test | Result |
|------|--------|
| `GET /runners` | ✅ Returns `{"runners": []}` |
| `GET /sessions` | ✅ Returns session list |
| `GET /jobs` (old) | ✅ Returns 404 (removed) |
| `GET /launchers` (old) | ✅ Returns 404 (removed) |
| Dashboard static | ✅ Returns 200 |
| Context Store | ✅ Health + documents working |

### Phase 2: Integration Tests ✅ PASSED

**Session Date:** 2025-12-17

All 7 integration test cases passed successfully.

| Test | Name | Result | Notes |
|------|------|--------|-------|
| 01 | basic-session-start | ✅ PASS | Session created, all 5 events received correctly |
| 02 | session-resume | ✅ PASS | Session resumed, message history persisted |
| 03 | session-with-agent | ✅ PASS | Agent blueprint applied correctly |
| 04 | child-agent-sync | ✅ PASS | MCP tool call, child spawned and returned result |
| 05 | child-agent-callback | ✅ PASS | Callback mode, parent_session_name set correctly |
| 06 | concurrent-callbacks | ✅ PASS | All 5 concurrent callbacks received, no race conditions |
| 07 | callback-on-child-failure | ✅ PASS | Failure callback received with error details |

**Test Categories Verified:**

| Category | Tests | Status |
|----------|-------|--------|
| Session Lifecycle | 01-04 | ✅ All passed |
| Callback Feature | 05-07 | ✅ All passed |

**API Endpoints Verified During Tests:**

| Endpoint | Method | Status |
|----------|--------|--------|
| `/runs` | POST | ✅ Creates runs correctly |
| `/runners` | GET | ✅ Shows registered runners |
| `/sessions` | GET | ✅ Returns session list |
| `/agents` | GET | ✅ Returns agent blueprints |

**Minor Notes:**
- `last_resumed_at` not propagated to coordinator DB (tracked in executor only)
- `parent_session_name` null in sync mode (expected, only set in callback mode)

### Phase 3: Manual Service Verification (TODO)

```bash
# Start Agent Coordinator
cd servers/agent-coordinator && uv run python main.py

# Start Agent Runner (separate terminal)
./servers/agent-runner/agent-runner

# Verify new API endpoints
curl http://localhost:8765/runs
curl http://localhost:8765/runners
```

### Phase 4: Dashboard Verification (TODO)

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
