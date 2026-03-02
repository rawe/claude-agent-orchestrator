# Executor Integration Tests

Black-box integration tests for the Claude Code executor using real Claude SDK.

## Quick Start

```bash
cd servers/agent-runner

# Run all tests (~2-3 min)
uv run --with pytest pytest tests/integration/ -v

# Run fast tests only (no Claude calls, <2s)
uv run --with pytest pytest tests/integration/tests/test_error_handling.py -v

# Run specific test file
uv run --with pytest pytest tests/integration/tests/test_start_mode.py -v
```

## Testing Different Executors

The harness supports testing any executor that follows the same interface (JSON stdin, stdout response).

```bash
# Test a different executor via environment variable
EXECUTOR_UNDER_TEST=executors/claude-code-v2/ao-exec uv run --with pytest pytest tests/integration/ -v

# Or in Python
harness = ExecutorTestHarness(executor_path="executors/my-new-executor/ao-exec")
```

The executor path is relative to the `agent-runner` directory.

## Structure

```
tests/integration/
├── README.md                 # This file
├── conftest.py               # Pytest fixtures (harness, session_id, project_dir)
├── infrastructure/           # Test infrastructure
│   ├── fake_gateway.py       # Simulates Runner Gateway (records HTTP calls)
│   ├── mcp_server.py         # Minimal MCP server (echo, get_time, add_numbers)
│   └── harness.py            # Test harness (manages services, runs executor)
├── fixtures/                 # Test data
│   ├── payloads.py           # Payload builder functions
│   └── schemas.py            # Sample JSON schemas for output validation
└── tests/                    # Test modules
    ├── test_error_handling.py   # Fast tests (no Claude) - validation errors
    ├── test_start_mode.py       # Start session tests
    ├── test_resume_mode.py      # Resume session tests (2 Claude calls each)
    ├── test_mcp_integration.py  # MCP tool invocation tests
    └── test_output_schema.py    # Structured output validation tests
```

## Test Categories

| File | Tests | Claude Calls | Description |
|------|-------|--------------|-------------|
| `test_error_handling.py` | 15 | No | Payload validation, missing fields, invalid versions |
| `test_start_mode.py` | 9 | Yes | Basic start, system prompts, events, timing |
| `test_resume_mode.py` | 7 | Yes (2x) | Context preservation, multiple resumes |
| `test_mcp_integration.py` | 8 | Yes | Tool invocation (echo, get_time, add_numbers) |
| `test_output_schema.py` | 10 | Yes | JSON extraction, schema validation, retry |

## Infrastructure

### FakeRunnerGateway
Simulates the Runner Gateway. Records all HTTP calls for assertions.
- `POST /bind` - Session binding
- `POST /events` - Event tracking
- `PATCH /metadata` - Session updates
- `GET /sessions/{id}` - Session retrieval (for resume)

### MinimalMCPServer
HTTP MCP server with test tools:
- `echo(message)` - Returns message back
- `get_time()` - Returns current timestamp
- `add_numbers(a, b)` - Returns sum
- `fail_on_purpose()` - Always errors (for error handling tests)
- `store_data(key, value)` - Stores data for verification

### ExecutorTestHarness
Orchestrates test execution:
- Starts/stops fake gateway and MCP server
- Runs executor as subprocess with JSON payload
- Provides accessors for recorded calls and events

## Usage for Refactoring

```bash
# 1. Before refactoring - run full suite
uv run --with pytest pytest tests/integration/ -v > baseline.txt 2>&1

# 2. Refactor the executor...

# 3. After refactoring - verify behavior unchanged
uv run --with pytest pytest tests/integration/ -v > after.txt 2>&1

# 4. Compare (all tests should pass)
diff baseline.txt after.txt
```
