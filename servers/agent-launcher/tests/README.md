# Agent Launcher Tests

## Run All Tests

```bash
uv run --with pytest --with httpx pytest servers/agent-launcher/tests/ -v
```

## Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `test_invocation.py` | 25 | Shared JSON payload parsing, validation, serialization |
| `test_executor.py` | 10 | Launcher payload building, subprocess spawning |

## Run Individual Files

```bash
# Invocation tests (no extra deps)
uv run --with pytest pytest servers/agent-launcher/tests/test_invocation.py -v

# Executor tests (needs httpx)
uv run --with pytest --with httpx pytest servers/agent-launcher/tests/test_executor.py -v
```
