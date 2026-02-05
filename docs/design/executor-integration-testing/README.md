# Claude Code Executor Integration Testing

Design document for testing the Claude Code executor as a complete unit to enable safe refactoring.

**Status**: Implemented
**Created**: 2026-02-05

## Problem Statement

The Claude Code executor (`ao-claude-code-exec`) and its dependent libraries need to be refactored. The current code organization has issues:

- Logic in `claude_client.py` should be moved to the executor
- Some executor logic should move to shared libs
- The separation of concerns is not optimal

To safely refactor, we need a test system that:
1. Tests the executor as a **complete black box** (script + all libs + real Claude SDK)
2. Verifies behavior is **identical before and after** refactoring
3. Tests **real Claude Agent SDK** integration, not mocks
4. Tests **real MCP server** integration

## Design Decisions

### DD-1: Test the Whole Executor as One Unit

**Decision**: Don't mock internal libraries. Treat executor + all libs as a single unit under test.

**Rationale**:
- Refactoring will significantly change internal library structure
- Mocking internal libs would require rewriting mocks after refactoring
- We care about external behavior, not internal implementation

### DD-2: Use Real Claude Agent SDK

**Decision**: Tests call the real Claude Agent SDK (real API calls).

**Rationale**:
- We need to verify actual SDK integration works
- Mock SDK could mask real integration issues
- Deterministic prompts minimize cost and variability

**Cost Mitigation**:
- Use very simple, deterministic prompts ("Return the word 'hello'")
- Mark Claude tests with `@pytest.mark.claude` for selective runs
- Fast tests (error handling, validation) don't call Claude

### DD-3: Minimal MCP Server for Tool Verification

**Decision**: Create a simple standalone MCP server with basic tools (echo, get_time).

**Rationale**:
- Verifies Claude actually invokes MCP tools
- Simpler than mocking or using the full Context Store
- Records all tool invocations for test assertions

### DD-4: Run Start + Resume in Sequence

**Decision**: For resume tests, run a start operation first, then resume it.

**Rationale**:
- Tests the real flow users experience
- Avoids maintaining fake session state
- Verifies start/resume actually work together

### DD-5: Manual Test Execution Only

**Decision**: Integration tests run manually, not automatically in CI.

**Rationale**:
- Each Claude test costs money (~$0.01-0.10)
- CI runs frequently, costs would accumulate
- Run before/after refactoring to verify behavior

## Architecture

### Test Boundary

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TEST BOUNDARY                               │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │               EXECUTOR (black box under test)                  │ │
│  │                                                                │ │
│  │   ao-claude-code-exec                                         │ │
│  │   ├── lib/claude_client.py      (Claude SDK integration)      │ │
│  │   ├── lib/invocation.py         (payload parsing)             │ │
│  │   ├── lib/session_client.py     (HTTP client)                 │ │
│  │   ├── lib/executor_config.py    (config loading)              │ │
│  │   ├── lib/utils.py              (utilities, ADR-015 formatting)│ │
│  │   └── claude-agent-sdk          (REAL SDK, not mocked)        │ │
│  │                                                                │ │
│  └───────────────────────────────────────────────────────────────┘ │
│           │                    │                      │            │
│     JSON stdin          HTTP calls              HTTP calls         │
│     (payload)           (to gateway)            (to MCP)           │
│           │                    │                      │            │
└───────────┼────────────────────┼──────────────────────┼────────────┘
            │                    │                      │
            ▼                    ▼                      ▼
     ┌──────────────┐  ┌────────────────────┐  ┌──────────────────┐
     │ Test Payload │  │ Fake Runner Gateway│  │ Minimal MCP      │
     │ (JSON)       │  │ (records calls)    │  │ Server           │
     └──────────────┘  └────────────────────┘  └──────────────────┘
```

### Components

#### 1. Fake Runner Gateway

HTTP server simulating the Runner Gateway. Records all calls for assertions.

**Endpoints**:

| Endpoint | Method | Purpose | Records |
|----------|--------|---------|---------|
| `/bind` | POST | Bind executor to session | session_id, executor_session_id, project_dir |
| `/events` | POST | Add event to session | All event data (message, post_tool, result) |
| `/metadata` | PATCH | Update session metadata | session_id, last_resumed_at |
| `/sessions/{id}` | GET | Get session (for resume) | Returns configurable response |

**Features**:
- Thread-safe call recording
- Configurable responses per session
- Automatic session state for start→resume tests

#### 2. Minimal MCP Server

HTTP-based MCP server with simple tools for testing.

**Tools**:

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `echo` | `message: str` | Returns message | Verify basic tool invocation |
| `get_time` | none | ISO timestamp | Verify parameterless tools |
| `add_numbers` | `a: int, b: int` | Sum | Verify multi-param tools |
| `fail_on_purpose` | none | Error | Verify error handling |

**Features**:
- Records all tool invocations with timestamps
- Thread-safe for concurrent access
- Standard MCP HTTP protocol

#### 3. Test Harness

Orchestrates test execution.

```python
class ExecutorTestHarness:
    """Manages fake services and executor subprocess."""

    def __init__(self):
        self.gateway = FakeRunnerGateway()
        self.mcp_server = MinimalMCPServer()

    def start_services(self) -> tuple[str, str]:
        """Start fake gateway and MCP server, return URLs."""

    def stop_services(self):
        """Stop all services."""

    def run_executor(
        self,
        payload: dict,
        timeout: float = 60.0
    ) -> ExecutorResult:
        """
        Run executor subprocess with payload on stdin.

        Returns:
            ExecutorResult with stdout, stderr, exit_code, duration
        """

    def get_gateway_calls(self) -> list[GatewayCall]:
        """Get all recorded gateway calls."""

    def get_mcp_tool_calls(self) -> list[ToolCall]:
        """Get all recorded MCP tool invocations."""

    def get_session_events(self, session_id: str) -> list[dict]:
        """Get all events for a session."""

    def clear_recordings(self):
        """Clear all recorded calls (between tests)."""
```

#### 4. ExecutorResult

```python
@dataclass
class ExecutorResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float

    @property
    def success(self) -> bool:
        return self.exit_code == 0
```

## Test Location

### Directory Structure

```
servers/agent-runner/
├── executors/
│   └── claude-code/
│       ├── ao-claude-code-exec     # Main executor script
│       └── lib/
│           └── claude_client.py    # Claude SDK integration
├── lib/                            # Shared libs
│   ├── invocation.py
│   ├── session_client.py
│   └── utils.py
└── tests/
    ├── test_invocation.py          # Existing unit tests
    ├── test_executor.py            # Existing unit tests
    └── integration/                # NEW: Integration tests
        ├── __init__.py
        ├── conftest.py             # Pytest fixtures (harness setup)
        ├── infrastructure/
        │   ├── __init__.py
        │   ├── fake_gateway.py     # Fake Runner Gateway server
        │   ├── mcp_server.py       # Minimal MCP server
        │   └── harness.py          # Test harness class
        ├── fixtures/
        │   ├── __init__.py
        │   ├── payloads.py         # Payload builder functions
        │   └── schemas.py          # Sample output schemas
        └── tests/
            ├── __init__.py
            ├── test_start_mode.py
            ├── test_resume_mode.py
            ├── test_mcp_integration.py
            ├── test_output_schema.py
            └── test_error_handling.py
```

### Payload Location

Test payloads are generated programmatically via builder functions in `fixtures/payloads.py`:

```python
# fixtures/payloads.py

def minimal_start_payload(
    session_id: str = "ses_test123",
    prompt: str = "Return the word 'hello'",
    project_dir: str = "/tmp/test"
) -> dict:
    """Minimal valid start payload."""
    return {
        "schema_version": "2.2",
        "mode": "start",
        "session_id": session_id,
        "parameters": {"prompt": prompt},
        "project_dir": project_dir,
    }

def start_with_mcp_payload(
    session_id: str,
    prompt: str,
    mcp_url: str,
    **kwargs
) -> dict:
    """Start payload with MCP server configured."""
    payload = minimal_start_payload(session_id, prompt, **kwargs)
    payload["agent_blueprint"] = {
        "name": "test-agent",
        "mcp_servers": {
            "test-mcp": {"url": mcp_url}
        }
    }
    return payload

def start_with_output_schema_payload(
    session_id: str,
    prompt: str,
    output_schema: dict,
    **kwargs
) -> dict:
    """Start payload with output schema validation."""
    payload = minimal_start_payload(session_id, prompt, **kwargs)
    payload["agent_blueprint"] = {
        "name": "schema-agent",
        "output_schema": output_schema
    }
    return payload

def resume_payload(
    session_id: str,
    prompt: str = "Continue the task"
) -> dict:
    """Resume payload for existing session."""
    return {
        "schema_version": "2.2",
        "mode": "resume",
        "session_id": session_id,
        "parameters": {"prompt": prompt},
    }
```

## Test Cases

### A. Start Mode Tests

| Test ID | Name | Prompt | Verify |
|---------|------|--------|--------|
| S01 | Basic start | "Return the word 'hello'" | exit 0, stdout contains 'hello', gateway.bind called |
| S02 | Start with system prompt | "What is your role?" | exit 0, response reflects system prompt |
| S03 | Start with MCP | "Use echo tool to say 'test'" | exit 0, mcp.echo called with 'test' |
| S04 | Start with output schema | "Return JSON with name 'Alice'" | exit 0, gateway.result event has result_data |
| S05 | Start with custom params (ADR-015) | Custom schema + params | exit 0, `<inputs>` block sent to Claude |

### B. Resume Mode Tests

| Test ID | Name | Pre-condition | Verify |
|---------|------|---------------|--------|
| R01 | Basic resume | S01 completed | exit 0, last_resumed_at updated |
| R02 | Resume continues context | S01 completed, ask follow-up | Response shows memory of previous interaction |
| R03 | Resume session not found | No prior session | exit 1, "not found" in stderr |
| R04 | Resume no executor_session_id | Session exists but no binding | exit 1, clear error message |

### C. MCP Integration Tests

| Test ID | Name | MCP Tools | Prompt | Verify |
|---------|------|-----------|--------|--------|
| M01 | Echo tool | echo | "Use echo to say 'hello world'" | mcp.echo called with 'hello world' |
| M02 | Multiple tools | echo, get_time | "Get time then echo it" | Both tools called |
| M03 | Math tool | add_numbers | "Use add_numbers to add 5 and 3" | mcp.add_numbers(5, 3) called |
| M04 | Tool error | fail_on_purpose | "Call fail_on_purpose" | Executor handles error gracefully |

### D. Output Schema Validation Tests

| Test ID | Name | Schema | Prompt | Verify |
|---------|------|--------|--------|--------|
| O01 | Valid JSON response | `{name: str}` | "Return JSON with name 'Bob'" | exit 0, result_data = {"name": "Bob"} |
| O02 | JSON in code block | `{value: int}` | "Return JSON with value 42 in code block" | exit 0, extracts correctly |
| O03 | Retry succeeds | `{items: array}` | Tricky prompt | exit 0, retry prompt sent |
| O04 | Retry fails | `{required: fields}` | Prompt that can't produce valid JSON | exit 1, validation error |

### E. Error Handling Tests (No Claude Calls)

| Test ID | Name | Input | Expected |
|---------|------|-------|----------|
| E01 | Invalid JSON | `{not json` | exit 1, "Invalid JSON" |
| E02 | Missing session_id | Valid JSON without session_id | exit 1, "Missing required field: session_id" |
| E03 | Missing parameters | Valid JSON without parameters | exit 1, "Missing required field: parameters" |
| E04 | Wrong schema version | schema_version: "99.0" | exit 1, "Unsupported schema version" |
| E05 | Invalid mode | mode: "invalid" | exit 1, "Invalid mode" |
| E06 | Empty stdin | "" | exit 1, "No input received" |

## Running Tests

### Prerequisites

```bash
# Ensure you have API access configured
export ANTHROPIC_API_KEY="your-key"

# Navigate to agent-runner
cd servers/agent-runner
```

### Run Fast Tests Only (No Claude Calls)

```bash
# Error handling and validation tests
uv run pytest tests/integration/tests/test_error_handling.py -v
```

### Run All Tests (Includes Claude Calls)

```bash
# Full test suite (costs money)
uv run pytest tests/integration/ -v
```

### Run Specific Test Categories

```bash
# Only start mode tests
uv run pytest tests/integration/tests/test_start_mode.py -v

# Only MCP tests
uv run pytest tests/integration/tests/test_mcp_integration.py -v

# Only output schema tests
uv run pytest tests/integration/tests/test_output_schema.py -v
```

### Run Single Test

```bash
# Run specific test by name
uv run pytest tests/integration/tests/test_start_mode.py::test_basic_start -v
```

### Test Markers

```python
@pytest.mark.claude      # Makes real Claude API calls
@pytest.mark.mcp         # Requires MCP server
@pytest.mark.slow        # Takes >10 seconds

# Run only fast tests (no Claude):
uv run pytest tests/integration/ -v -m "not claude"

# Run only MCP tests:
uv run pytest tests/integration/ -v -m "mcp"
```

## Refactoring Verification Process

When refactoring the executor:

1. **Before refactoring**: Run full test suite, save results
   ```bash
   uv run pytest tests/integration/ -v --tb=short > before_refactor.txt
   ```

2. **Perform refactoring**: Modify executor and libs

3. **After refactoring**: Run full test suite again
   ```bash
   uv run pytest tests/integration/ -v --tb=short > after_refactor.txt
   ```

4. **Compare results**: All tests should pass with same behavior
   ```bash
   diff before_refactor.txt after_refactor.txt
   ```

## Implementation Plan

### Phase 1: Infrastructure

1. Create `tests/integration/infrastructure/fake_gateway.py`
   - HTTP server with threading
   - Call recording
   - Configurable responses

2. Create `tests/integration/infrastructure/mcp_server.py`
   - MCP HTTP protocol implementation
   - Tool definitions (echo, get_time, add_numbers, fail_on_purpose)
   - Call recording

3. Create `tests/integration/infrastructure/harness.py`
   - Service lifecycle management
   - Subprocess execution
   - Result collection

4. Create `tests/integration/conftest.py`
   - Pytest fixtures for harness
   - Session-scoped service startup

### Phase 2: Fast Tests (No Claude)

1. Create `tests/integration/fixtures/payloads.py`
   - Payload builder functions

2. Create `tests/integration/tests/test_error_handling.py`
   - All E01-E06 tests
   - These run without Claude, good for rapid iteration

### Phase 3: Claude Tests

1. Create `tests/integration/tests/test_start_mode.py`
   - S01-S05 tests

2. Create `tests/integration/tests/test_resume_mode.py`
   - R01-R04 tests

3. Create `tests/integration/tests/test_mcp_integration.py`
   - M01-M04 tests

4. Create `tests/integration/tests/test_output_schema.py`
   - O01-O04 tests

## Appendix: Sample Prompts

### Deterministic Prompts for Testing

These prompts are designed to produce consistent, verifiable output:

```python
# S01: Basic start
"Respond with exactly the word 'hello' and nothing else."

# S03: MCP echo
"Use the echo tool to send the message 'test123'. Then respond with 'done'."

# M02: Multiple tools
"First use get_time to get the current time. Then use echo to repeat that time. Finally respond with 'completed'."

# O01: Output schema
"Return a JSON object with a single field 'name' set to 'Alice'. Output only the JSON."

# R02: Resume context
"What was the last thing I asked you to do?"
```

## Appendix: Current Executor Interface

### Input (stdin)

JSON payload following schema 2.2:

```json
{
  "schema_version": "2.2",
  "mode": "start" | "resume",
  "session_id": "ses_<12-char-hex>",
  "parameters": {"prompt": "...", ...},
  "project_dir": "/path/to/project",
  "agent_blueprint": {
    "name": "agent-name",
    "system_prompt": "...",
    "mcp_servers": {"name": {"url": "..."}},
    "parameters_schema": {...},
    "output_schema": {...}
  },
  "executor_config": {
    "permission_mode": "bypassPermissions",
    "setting_sources": [],
    "model": "opus"
  },
  "metadata": {}
}
```

### Output (stdout)

Agent response text (or JSON for structured output).

### Exit Codes

- `0`: Success
- `1`: Error (validation, SDK error, session error)

### HTTP Calls (to Runner Gateway)

| Call | When | Data |
|------|------|------|
| POST /bind | After SDK returns session_id | session_id, executor_session_id, project_dir |
| POST /events | On messages | event_type, content, timestamp |
| POST /events | On tool use | event_type=post_tool, tool details |
| POST /events | On completion | event_type=result, result_text/result_data |
| PATCH /metadata | On resume | last_resumed_at |
| GET /sessions/{id} | Resume mode | Returns session with executor_session_id |

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://127.0.0.1:8765` | Runner Gateway URL |

Note: Authentication is handled by Claude Code subscription via the Claude Agent SDK.
