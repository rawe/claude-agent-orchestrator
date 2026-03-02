# Handover: Phase 1 Complete — Executor Multi-Turn

## Branch

```
refactor/claude-code-executor
```

## Summary

Phase 1 implements multi-turn support at the executor level. The `ClaudeSDKClient` stays alive across multiple conversation turns within a single process. Turns arrive as NDJSON on stdin, completion signals go to stdout. Testable in isolation — no runner changes required.

**All 46 integration tests pass** (4 new multi-turn + 42 existing, zero regressions).

## What Was Implemented

### 1. Entry Point: NDJSON stdin reading

**File**: `servers/agent-runner/executors/claude-sdk-executor/ao-claude-code-exec`

- Changed stdin parsing from `ExecutorInvocation.from_stdin()` (reads all) to `sys.stdin.readline()` + `ExecutorInvocation.from_json()` (reads one NDJSON line, leaves stdin open)
- `mode="start"` routes to `run_multi_turn()` (new)
- `mode="resume"` still routes to `run_resume()` (unchanged, legacy)

### 2. Executor bridge: `run_multi_turn()`

**File**: `servers/agent-runner/executors/claude-sdk-executor/lib/executor.py`

- New `run_multi_turn(inv)` function: loads config, delegates to `run_multi_turn_session_sync()`
- Existing `run_start()`, `run_resume()`, `_execute_session()` unchanged

### 3. Core multi-turn session loop

**File**: `servers/agent-runner/executors/claude-sdk-executor/lib/sdk_client.py`

Three new functions added:

- **`_read_stdin_line()`** — async stdin reading via `loop.run_in_executor(None, sys.stdin.readline)`, keeps event loop responsive
- **`run_multi_turn_session()`** — the core loop:
  - Builds `ClaudeAgentOptions` (permission_mode, hooks, system_prompt, MCP servers, output_format)
  - Opens `async with ClaudeSDKClient(options=options)` wrapping ALL turns
  - Turn 1: executes from initial invocation, handles session binding via `SystemMessage.init`
  - Subsequent turns: reads NDJSON from stdin, `type=turn` → execute, `type=shutdown` → break
  - Each turn: emits events via HTTP, writes `turn_complete` to stdout
  - Supports structured output (`output_schema` → `output_format`, `structured_output` capture)
- **`run_multi_turn_session_sync()`** — `asyncio.run()` wrapper

Existing `run_claude_session()` and `run_session_sync()` unchanged.

### 4. Test infrastructure: `MultiTurnExecutor`

**File**: `servers/agent-runner/tests/integration/infrastructure/harness.py`

- **`_StderrDrainer`** — background thread draining stderr to prevent pipe deadlocks
- **`MultiTurnExecutor`** class:
  - `start(payload)` → spawn Popen, write first NDJSON line, wait for `turn_complete`
  - `send_turn(run_id, parameters)` → write turn message, wait for `turn_complete`
  - `shutdown()` → send shutdown, close stdin, wait for exit
  - `close_stdin()` → EOF-based shutdown (no explicit message)
  - `kill()` → force kill
  - `_read_turn_result()` → reads stdout lines, skips non-JSON, returns on `turn_complete`
- **`create_multi_turn_executor()`** on `ExecutorTestHarness`

### 5. Multi-turn integration tests

**File**: `servers/agent-runner/tests/integration/tests/test_multi_turn.py`

| Test | What It Verifies |
|------|-----------------|
| `test_single_turn_with_shutdown` | Start session, get response, clean shutdown (exit 0) |
| `test_two_turns_context_preserved` | Turn 2 remembers turn 1 content ("elephant" secret word) |
| `test_shutdown_via_eof` | Process exits cleanly on stdin EOF (no explicit shutdown) |
| `test_events_emitted_per_turn` | Each turn emits user_message, assistant_message, result via HTTP |

## Findings During Implementation

### F1: NDJSON prompt path mismatch (fixed)

The developer initially read `msg.get("prompt")` for subsequent turns. The protocol spec nests it under `parameters`: `msg["parameters"]["prompt"]`. Fixed by team lead during code review.

### F2: output_schema regression (fixed)

Routing all `mode="start"` to `run_multi_turn()` broke output_schema agents because the new function didn't handle structured output. Fixed by adding `output_format`, `structured_output` capture, `skip_assistant_message`, and validation — mirroring `run_claude_session()`.

### F3: Unused imports (cleaned)

Developer imported `AssistantMessage` and `ExecutorInvocation` in the new function but didn't use them. Cleaned during review.

## Test Results

```
test_multi_turn.py      4/4  PASSED
test_start_mode.py      9/9  PASSED
test_error_handling.py  15/15 PASSED
test_mcp_integration.py 8/8  PASSED
test_output_schema.py   10/10 PASSED
────────────────────────────────────
TOTAL                   46/46 PASSED
```

Test command:
```bash
cd servers/agent-runner
EXECUTOR_UNDER_TEST=executors/claude-sdk-executor/ao-claude-code-exec \
  uv run --with pytest pytest tests/integration/tests/ -v \
  --ignore=tests/integration/tests/test_resume_mode.py
```

Resume tests (`test_resume_mode.py`) remain broken — they test the old `--resume` CLI flag which is unsupported. They will be converted to multi-turn tests in Phase 3.

## File Map

| File | Status | Description |
|------|--------|-------------|
| `executors/claude-sdk-executor/ao-claude-code-exec` | Modified | NDJSON readline, start→multi-turn routing |
| `executors/claude-sdk-executor/lib/executor.py` | Modified | Added `run_multi_turn()` |
| `executors/claude-sdk-executor/lib/sdk_client.py` | Modified | Added `run_multi_turn_session()`, `_read_stdin_line()`, sync wrapper |
| `tests/integration/infrastructure/harness.py` | Modified | Added `_StderrDrainer`, `MultiTurnExecutor`, `create_multi_turn_executor()` |
| `tests/integration/infrastructure/__init__.py` | Modified | Added `MultiTurnExecutor` export |
| `tests/integration/tests/test_multi_turn.py` | **New** | 4 multi-turn integration tests |
| `docs/design/.../NDJSON-PROTOCOL-REFERENCE.md` | **New** | Complete NDJSON protocol specification |
| `docs/design/.../MULTI-TURN-EXECUTOR-ARCHITECTURE.md` | **New** | Executor architecture, lifecycle, component map |

## Technical Reference Documents

These standalone documents contain the full technical specifications extracted from this implementation:

- **[NDJSON Protocol Reference](NDJSON-PROTOCOL-REFERENCE.md)** — Message formats (stdin/stdout), field tables, flow diagram, error handling, HTTP vs stdout channel separation, Phase 2 integration notes
- **[Multi-Turn Executor Architecture](MULTI-TURN-EXECUTOR-ARCHITECTURE.md)** — Process lifecycle, states, SDK internals, session config lifecycle, event emission per turn, crash recovery policy, resource footprint, component map (executor + runner)

## What Is Still Open: Phase 2 (Runner Integration)

Phase 2 makes the runner aware of multi-turn. The executor is ready — Phase 2 only touches runner-side files.

### Changes needed

| File | Change | Scope |
|------|--------|-------|
| `servers/agent-runner/lib/registry.py` | Add `session_id → RunningRun` index alongside `run_id → RunningRun` | Small |
| `servers/agent-runner/lib/executor.py` | Keep stdin open after first write (flush, don't close) | Small |
| `servers/agent-runner/lib/poller.py` | Route `resume_session` runs to existing process via stdin NDJSON | Medium |
| `servers/agent-runner/lib/supervisor.py` | Add stdout reader thread per process for `turn_complete` detection | Medium |

### How it connects

1. Runner spawns executor with `stdin=PIPE, stdout=PIPE` (keep open)
2. Runner writes initial invocation as NDJSON line 1
3. Supervisor reads `turn_complete` from stdout → reports run completed
4. When `resume_session` arrives, poller looks up process in registry by `session_id`
5. Poller writes turn NDJSON to existing process stdin (no new spawn)
6. Supervisor reads next `turn_complete` → reports resume run completed

See [NDJSON Protocol Reference](NDJSON-PROTOCOL-REFERENCE.md) "Phase 2 Integration Notes" section for detailed guidance.

### What stays the same

Coordinator: zero changes. Affinity routing, run lifecycle, session events, callbacks — all unchanged.

## How to Test

```bash
cd servers/agent-runner

# All non-resume tests (46 tests, should all pass)
EXECUTOR_UNDER_TEST=executors/claude-sdk-executor/ao-claude-code-exec \
  uv run --with pytest pytest tests/integration/tests/ -v \
  --ignore=tests/integration/tests/test_resume_mode.py

# Multi-turn tests only
EXECUTOR_UNDER_TEST=executors/claude-sdk-executor/ao-claude-code-exec \
  uv run --with pytest pytest tests/integration/tests/test_multi_turn.py -v

# Specific test
EXECUTOR_UNDER_TEST=executors/claude-sdk-executor/ao-claude-code-exec \
  uv run --with pytest pytest tests/integration/tests/test_multi_turn.py::TestMultiTurnBasic::test_two_turns_context_preserved -v
```
