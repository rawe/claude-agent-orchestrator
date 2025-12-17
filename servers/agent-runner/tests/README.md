# Agent Runner Tests

## Run All Tests

```bash
uv run --with pytest --with httpx pytest servers/agent-runner/tests/ -v
```

## Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `test_invocation.py` | 25 | Shared JSON payload parsing, validation, serialization |
| `test_executor.py` | 10 | Runner payload building, subprocess spawning |

## Run Individual Files

```bash
# Invocation tests (no extra deps)
uv run --with pytest pytest servers/agent-runner/tests/test_invocation.py -v

# Executor tests (needs httpx)
uv run --with pytest --with httpx pytest servers/agent-runner/tests/test_executor.py -v
```
