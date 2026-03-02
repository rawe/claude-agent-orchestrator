# Agent Runner Tests

## Run All Tests

```bash
cd servers/agent-runner && uv run --with pytest --with httpx pytest tests/ -v
```

## Test Files

| File | Tests | What it covers |
|------|-------|----------------|
| `test_registry.py` | 21 | ProcessRegistry: dual-index CRUD, swap/clear run, stopping guard, concurrency |
| `test_api_client.py` | 21 | CoordinatorAPIClient: registration, polling, status reports, heartbeat, deregistration |
| `test_runner_gateway.py` | 11 | RunnerGateway: bind enrichment, event/metadata forwarding, validation |
| `test_supervisor.py` | 20 | RunSupervisor: one-shot/persistent exit handling, NDJSON stdout reader, dedup |
| `test_poller.py` | 15 | RunPoller: start/resume routing, stop handling, poll loop lifecycle |
| `test_invocation.py` | 30 | Shared JSON payload parsing, validation, serialization |

**Total: 118 tests**

## Run Individual Files

```bash
cd servers/agent-runner

# Registry (no extra deps)
uv run --with pytest pytest tests/test_registry.py -v

# API client (needs httpx for FakeCoordinator)
uv run --with pytest --with httpx pytest tests/test_api_client.py -v

# Runner gateway (needs httpx)
uv run --with pytest --with httpx pytest tests/test_runner_gateway.py -v

# Supervisor (no extra deps)
uv run --with pytest pytest tests/test_supervisor.py -v

# Poller (no extra deps)
uv run --with pytest pytest tests/test_poller.py -v

# Invocation (no extra deps)
uv run --with pytest pytest tests/test_invocation.py -v
```

## Test Infrastructure

- **`fakes/fake_coordinator.py`** — HTTP server implementing all Runner API endpoints. Used by `test_api_client.py` and `test_runner_gateway.py`.
- **`conftest.py`** — Shared fixtures: `fake_coordinator`, `echo_executor_path`, `runner_dir`.

## Integration Tests

See `tests/integration/` for end-to-end tests using real executors. Run with:

```bash
EXECUTOR_UNDER_TEST=<path> uv run --with pytest pytest tests/integration/tests/<file> -v
```
