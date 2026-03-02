# Testing Overview

## Agent Coordinator — Unit & API Tests

**Location**: `servers/agent-coordinator/tests/`
**No running services required** — uses isolated SQLite + FastAPI TestClient.

```bash
cd servers/agent-coordinator

# All tests
uv run --with pytest --with httpx pytest tests/ -v

# Unit tests only
uv run --with pytest --with httpx pytest tests/unit/ -v

# API tests only
uv run --with pytest --with httpx pytest tests/api/ -v
```

| File | Tests | Coverage |
|------|-------|----------|
| `unit/test_smoke.py` | 1 | Fixture smoke test |
| `unit/test_database_sessions.py` | — | Session CRUD, state transitions |
| `unit/test_database_runs.py` | — | Run CRUD, atomic claiming |
| `unit/test_database_events.py` | — | Event CRUD, cascade delete |
| `unit/test_run_queue.py` | — | RunQueue add/claim/demand matching |
| `unit/test_runner_registry.py` | — | Runner register/heartbeat/lifecycle |
| `unit/test_run_demands.py` | — | Demand matching logic |
| `api/test_runs_api.py` | — | POST /runs endpoints |
| `api/test_sessions_api.py` | — | GET/DELETE /sessions endpoints |
| `api/test_runner_api.py` | — | Runner register/poll/report endpoints |
| `test_mcp_registry.py` | — | MCP registry |
| `test_placeholder_resolver.py` | — | Placeholder resolver |

---

## Agent Runner — Unit Tests

**Location**: `servers/agent-runner/tests/`
**No running services required** — uses FakeCoordinator HTTP server and mocks.

```bash
cd servers/agent-runner

# All unit tests
uv run --with pytest --with httpx pytest tests/ --ignore=tests/integration -v

# Individual files
uv run --with pytest pytest tests/test_registry.py -v
uv run --with pytest --with httpx pytest tests/test_api_client.py -v
uv run --with pytest --with httpx pytest tests/test_runner_gateway.py -v
uv run --with pytest pytest tests/test_supervisor.py -v
uv run --with pytest pytest tests/test_poller.py -v
uv run --with pytest pytest tests/test_invocation.py -v
```

| File | Tests | Coverage |
|------|-------|----------|
| `test_registry.py` | 21 | ProcessRegistry: dual-index CRUD, swap/clear run, stopping guard, concurrency |
| `test_api_client.py` | 21 | CoordinatorAPIClient: registration, polling, status reports, heartbeat, deregistration |
| `test_runner_gateway.py` | 11 | RunnerGateway: bind enrichment, event/metadata forwarding, validation |
| `test_supervisor.py` | 20 | RunSupervisor: one-shot/persistent exit handling, NDJSON stdout reader, dedup |
| `test_poller.py` | 15 | RunPoller: start/resume routing, stop handling, poll loop lifecycle |
| `test_invocation.py` | 30 | Invocation JSON payload parsing, validation, serialization |

Test infrastructure: `fakes/fake_coordinator.py` (HTTP server), `conftest.py` (shared fixtures).

---

## Agent Runner — Integration Tests (Executor)

**Location**: `servers/agent-runner/tests/integration/`
**Requires**: `EXECUTOR_UNDER_TEST` environment variable pointing to an executor.

```bash
cd servers/agent-runner

# All integration tests (uses echo executor)
EXECUTOR_UNDER_TEST=executors/echo-executor/ao-echo-exec \
  uv run --with pytest --with httpx pytest tests/integration/tests/ -v

# Single file
EXECUTOR_UNDER_TEST=executors/echo-executor/ao-echo-exec \
  uv run --with pytest --with httpx pytest tests/integration/tests/test_start_mode.py -v
```

| File | Coverage |
|------|----------|
| `test_start_mode.py` | Basic start, blueprints, executor config, deterministic responses |
| `test_error_handling.py` | Invalid payloads, validation errors, gateway interaction |
| `test_mcp_integration.py` | MCP tool invocation, multi-tool calls, error handling |
| `test_multi_turn.py` | Multi-turn context, shutdown via EOF |
| `test_output_schema.py` | JSON schema validation, retry on invalid output |

---

## System Integration Tests (Manual)

**Location**: `tests/integration/`
**Requires**: Running Coordinator + Runner + SSE monitor.

See `tests/README.md` for full setup instructions, or use slash commands:

```bash
/tests:setup echo-executor   # Start all services
/tests:case 1                # Run a specific test case
/tests:run                   # Run all test cases
/tests:teardown              # Stop services
```
