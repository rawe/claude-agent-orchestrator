# Multi-Turn Architecture Design

## Status: Phase 1 implemented, Phase 2 superseded by dedicated docs

> **Note**: The Phase 2 sections of this document are superseded by 5 dedicated architecture
> documents. See `PHASE2-IMPLEMENTATION-PLAN.md` for the authoritative Phase 2 plan and
> references to: `REGISTRY-REDESIGN.md`, `STOP-COMMAND-REDESIGN.md`,
> `SESSION-STATUS-REDESIGN.md`, `NDJSON-PROTOCOL-SIMPLIFICATION.md`,
> `EXECUTOR-SESSION-ID-SCOPE.md`. Phase 1 sections remain accurate.

## Problem

The Claude CLI does not support `--resume` + `--input-format stream-json` (GitHub #16712).
The `ClaudeSDKClient` supports hooks but not cross-process resume. The standalone `query()`
supports resume but not hooks. **Hooks are non-negotiable.**

## Decision

Keep the `ClaudeSDKClient` process alive across turns. Call `client.query(prompt)` multiple
times on the same instance instead of spawning a new process per turn.

## SDK Validation

The Executor Specialist confirmed from SDK source (v0.1.33, CLI 2.1.37):

- `ClaudeSDKClient.query()` writes one JSON line to the already-running CLI subprocess stdin.
  It does NOT spawn a new subprocess per call.
- `receive_response()` yields messages until `ResultMessage`, then returns. The client stays
  fully usable for another `query()` call.
- Hooks are registered once during `initialize()` (in `connect()`) and persist across all turns.
- `bind()` in `SessionEventEmitter` is guarded by `if self._bound` — safe to call repeatedly.
- The SDK docstring explicitly describes multi-turn as the primary use case.

**Conclusion**: The SDK already supports multi-turn within one process. The problem is entirely
in the surrounding infrastructure (Runner, Executor entry point, Supervisor).

---

## Architecture Overview

### Current Flow (broken for resume)

```
Coordinator creates Run (start_session)
  → Runner claims via long-poll
  → Runner spawns subprocess (stdin: JSON, close stdin)
  → Executor reads stdin, runs one turn, exits
  → Supervisor detects process exit → reports completed
  → Session status: "finished"

Coordinator creates Run (resume_session)
  → Runner claims via long-poll
  → Runner spawns NEW subprocess with --resume flag  ← BROKEN
  → Executor reads stdin, runs one turn, exits
  → Supervisor detects process exit → reports completed
```

### New Flow (multi-turn)

```
Coordinator creates Run (start_session)       ← NO CHANGE
  → Runner claims via long-poll                ← NO CHANGE
  → Runner spawns subprocess (stdin: NDJSON, keep stdin OPEN)  ← CHANGED
  → Executor reads first line, opens ClaudeSDKClient, runs turn 1
  → Executor writes turn_complete to stdout    ← NEW
  → Supervisor reads turn_complete → reports run completed  ← CHANGED
  → Executor stays alive, waiting for next stdin line       ← NEW
  → Session status: "finished" (idle)

Coordinator creates Run (resume_session)       ← NO CHANGE
  → Runner claims via long-poll                ← NO CHANGE
  → Runner sees session has live process       ← CHANGED
  → Runner writes NDJSON line to existing process stdin  ← CHANGED
  → Executor reads next line, calls client.query(), runs turn 2
  → Executor writes turn_complete to stdout
  → Supervisor reads turn_complete → reports run completed
  → Executor stays alive for more turns

Shutdown:
  → Runner writes {"type": "shutdown"} to stdin  ← NEW
  → Executor exits cleanly
  → Supervisor detects process exit → no-op (expected)
```

---

## Component Changes

### 1. Agent Coordinator — NO CHANGES

The coordinator's model already supports multi-turn:

| Concept | Current | Multi-turn | Change? |
|---------|---------|------------|---------|
| Session | Conversation container (multiple runs) | Same | None |
| Run | One turn of work (PENDING→CLAIMED→RUNNING→COMPLETED) | Same | None |
| Run types | `start_session`, `resume_session` | Same | None |
| Affinity demands | Route resume to same runner (hostname + profile) | Same | None |
| Session bind | Executor binds with executor_session_id | Same | None |
| Session events | user_message, assistant_message, result per turn | Same | None |
| Run completion | Runner calls POST /runner/runs/{id}/completed | Same | None |
| Callback processor | On child complete → resume parent | Same | None |

The key insight: the coordinator already treats each turn as a separate Run. Whether the
runner spawns a new process or routes to an existing one is invisible to the coordinator.

### 2. Runner — MODERATE CHANGES

#### 2a. Registry: Add session-to-process mapping

**File**: `servers/agent-runner/lib/registry.py`

Current `RunningRunsRegistry` maps `run_id → RunningRun`. For multi-turn, we also need
`session_id → RunningRun` to route resume runs to existing processes.

```
Current:
  _runs: dict[str, RunningRun]  # run_id → RunningRun

New:
  _runs: dict[str, RunningRun]           # run_id → RunningRun
  _session_processes: dict[str, RunningRun]  # session_id → RunningRun (for live processes)
```

When a start_session run spawns a process, register it in both maps.
When a resume_session run arrives, look up the process from `_session_processes`.
When the process exits, remove from both maps.

The `RunningRun` dataclass needs one addition: the `session_id` field (currently only has `run_id`).

#### 2b. Executor spawner: Keep stdin open, use NDJSON

**File**: `servers/agent-runner/lib/executor.py`

Current (`_execute_with_payload`, line 348-355):
```python
process = subprocess.Popen(cmd, stdin=subprocess.PIPE, ...)
process.stdin.write(payload_json)
process.stdin.close()  # ← stdin closed, no way to send more data
```

New:
```python
process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, ...)
process.stdin.write(payload_json + "\n")  # NDJSON: one JSON per line
process.stdin.flush()                      # flush but DON'T close
# stdin stays open for future turns
```

#### 2c. Poller: Route resume to existing process

**File**: `servers/agent-runner/lib/poller.py`

Current `_handle_run()` always calls `executor.execute_run(run)` which spawns a new process.

New logic:
```
if run.type == "resume_session":
    existing = registry.get_session_process(run.session_id)
    if existing:
        # Route to existing process (write NDJSON to stdin)
        send_turn_to_process(existing, run)
        return
    # Fallback: no live process → report failure
    report_failed("No live executor process for session")
else:
    # start_session → spawn new process as before
    executor.execute_run(run)
```

The `send_turn_to_process()` function writes NDJSON to the process stdin:
```python
def send_turn_to_process(running_run: RunningRun, run: Run):
    turn_payload = {
        "type": "turn",
        "run_id": run.run_id,
        "parameters": run.parameters,
        "agent_blueprint": run.resolved_agent_blueprint,
    }
    running_run.process.stdin.write(json.dumps(turn_payload) + "\n")
    running_run.process.stdin.flush()
```

#### 2d. Supervisor: Read turn_complete from stdout

**File**: `servers/agent-runner/lib/supervisor.py`

Current: polls `process.poll()` every 1s. Non-None return code = done.

New: **two detection mechanisms**:

1. **Turn completion** (stdout protocol): Executor writes `{"type": "turn_complete", "run_id": "...", "result": "..."}` to stdout when a turn finishes. Supervisor reads stdout and reports `run_completed` to coordinator. Process stays alive.

2. **Process exit** (existing mechanism): If process exits unexpectedly (crash), supervisor detects via `process.poll()` and reports `run_failed` for any in-progress run.

Implementation: The supervisor needs a **stdout reader thread** per process. This thread reads NDJSON lines from stdout. When it sees `turn_complete`, it reports the run as completed. The existing `process.poll()` loop continues to catch crashes.

```
per process:
  - stdout reader thread: reads lines, dispatches turn_complete events
  - poll loop (existing): detects unexpected process exit
```

### 3. Executor — SIGNIFICANT CHANGES

#### 3a. Entry point: NDJSON stdin loop

**File**: `servers/agent-runner/executors/claude-sdk-executor/ao-claude-code-exec`

Current:
```python
invocation = ExecutorInvocation.from_stdin()  # reads ALL stdin, parses one JSON
if invocation.mode == "start":
    run_start(invocation)
elif invocation.mode == "resume":
    run_resume(invocation)
```

New:
```python
# Read first line from stdin (initial invocation)
first_line = sys.stdin.readline()
invocation = ExecutorInvocation.from_json(first_line.strip())

# Start the multi-turn session
run_multi_turn(invocation, stdin_reader=sys.stdin)
```

#### 3b. SDK client: Multi-turn session loop

**File**: `servers/agent-runner/executors/claude-sdk-executor/lib/sdk_client.py`

The current `run_claude_session()` opens `ClaudeSDKClient`, runs one query, closes.

New architecture: The function becomes a long-lived coroutine that keeps the client open
across all turns:

```python
async def run_multi_turn_session(
    initial_invocation: ExecutorInvocation,
    stdin_reader,  # sys.stdin or async reader
    ...
):
    emitter = SessionEventEmitter(api_url, session_id)

    # Build options (system_prompt, hooks, MCP servers, etc.)
    options = build_options(initial_invocation)

    async with ClaudeSDKClient(options=options) as client:
        # --- Turn 1 (from initial invocation) ---
        prompt = format_prompt(initial_invocation)
        await client.query(prompt)
        result = await process_message_stream(client, prompt, emitter)

        # Signal turn complete to runner (via stdout)
        print(json.dumps({"type": "turn_complete", "run_id": run_id}))
        sys.stdout.flush()

        # --- Subsequent turns (from stdin NDJSON) ---
        for line in read_stdin_lines(stdin_reader):
            msg = json.loads(line)

            if msg["type"] == "shutdown":
                break

            if msg["type"] == "turn":
                prompt = msg["parameters"]["prompt"]
                run_id = msg["run_id"]

                emitter.emit_user_message(prompt)
                await client.query(prompt)
                result = await process_message_stream(client, prompt, emitter)

                # Signal turn complete
                print(json.dumps({"type": "turn_complete", "run_id": run_id}))
                sys.stdout.flush()

    # Context manager exits → CLI subprocess terminated
```

Key changes from current `run_claude_session()`:
- `async with ClaudeSDKClient` wraps ALL turns, not just one
- `asyncio.run()` stays alive for the process lifetime
- `emitter.emit_user_message()` moves out of `SystemMessage.init` handler into the turn loop
  (SystemMessage.init may not be re-sent on subsequent queries)
- `process_message_stream()` works mostly as-is but first-turn guards remain correct
  (`executor_session_id is None` prevents re-binding)
- Turn results go to stdout as NDJSON (not `print(result)` which is how the runner currently
  reads the final output)

#### 3c. Async stdin reading inside the event loop

The executor must read stdin inside an async context (within `async with ClaudeSDKClient`).
Options:

1. `await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)` — simplest,
   runs blocking readline in a thread pool
2. `asyncio.StreamReader` wrapping stdin fd — more complex
3. Dedicated thread + `asyncio.Queue` — most control

Recommend option 1 for simplicity:
```python
async def read_stdin_lines(stdin):
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, stdin.readline)
        if not line:  # EOF
            break
        yield line.strip()
```

### 4. Invocation Schema — MINOR CHANGES

**File**: `servers/agent-runner/lib/invocation.py`

The `ExecutorInvocation.from_stdin()` method currently calls `sys.stdin.read()` (reads ALL).
For multi-turn, the initial invocation reads ONE line instead.

Additionally, a new message type for subsequent turns:

```python
# Initial invocation (first line on stdin) — existing schema, no change:
{"schema_version": "2.2", "mode": "start", "session_id": "ses_abc", "parameters": {"prompt": "..."}, ...}

# Subsequent turn (follow-up lines on stdin) — new message type:
{"type": "turn", "run_id": "run_xyz", "parameters": {"prompt": "follow-up question"}, "agent_blueprint": {...}}

# Shutdown signal:
{"type": "shutdown"}
```

The initial invocation uses the existing `ExecutorInvocation` schema (no changes needed).
Subsequent turns use a simpler format since session config (system_prompt, MCP servers, etc.)
is already established.

### 5. Test Infrastructure — MODERATE CHANGES

**File**: `servers/agent-runner/tests/integration/infrastructure/harness.py`

Current `run_executor()` uses `subprocess.run()` (blocks until process exit).

New: Add `MultiTurnExecutor` class alongside existing `run_executor()`:

```python
class MultiTurnExecutor:
    def start(self, initial_payload) -> dict:
        """Spawn process, send initial invocation, wait for turn_complete."""
        self._process = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True)
        self._process.stdin.write(json.dumps(initial_payload) + "\n")
        self._process.stdin.flush()
        return self._read_turn_result()

    def send_turn(self, run_id, parameters, blueprint=None) -> dict:
        """Send follow-up turn, wait for turn_complete."""
        msg = {"type": "turn", "run_id": run_id, "parameters": parameters}
        if blueprint:
            msg["agent_blueprint"] = blueprint
        self._process.stdin.write(json.dumps(msg) + "\n")
        self._process.stdin.flush()
        return self._read_turn_result()

    def shutdown(self):
        """Send shutdown and wait for process exit."""
        self._process.stdin.write('{"type": "shutdown"}\n')
        self._process.stdin.flush()
        self._process.wait(timeout=10)

    def _read_turn_result(self) -> dict:
        """Read stdout lines until turn_complete marker."""
        while True:
            line = self._process.stdout.readline()
            if not line:
                raise RuntimeError("Process exited before turn_complete")
            try:
                msg = json.loads(line.strip())
                if msg.get("type") == "turn_complete":
                    return msg
            except json.JSONDecodeError:
                continue  # skip non-JSON output
```

Resume tests become multi-turn tests that use `MultiTurnExecutor` instead of two separate
`run_executor()` calls.

---

## Process Lifecycle

```
                    ┌──────────────────────────────────────────────────────┐
                    │           Executor Process Lifecycle                 │
                    │                                                      │
  stdin line 1      │   ┌─────────┐    ┌──────────────────────────────┐   │
  (invocation) ────►│   │ Parse   │───►│ async with ClaudeSDKClient   │   │
                    │   │ initial │    │                              │   │
                    │   │ payload │    │   ┌──────┐  ┌───────────┐   │   │  stdout
                    │   └─────────┘    │   │Turn 1│─►│turn_complete──►├───┼──────►
                    │                  │   └──────┘  └───────────┘   │   │
  stdin line 2      │                  │                              │   │
  (turn) ──────────►│                  │   ┌──────┐  ┌───────────┐   │   │  stdout
                    │                  │   │Turn 2│─►│turn_complete──►├───┼──────►
                    │                  │   └──────┘  └───────────┘   │   │
  stdin line N      │                  │                              │   │
  (shutdown) ──────►│                  │   break loop                 │   │
                    │                  │                              │   │
                    │                  └──────────────────────────────┘   │
                    │                          │                          │
                    │                     process exit                    │
                    └──────────────────────────────────────────────────────┘
```

### States

| State | Description | Trigger |
|-------|-------------|---------|
| **Starting** | Process spawned, reading first stdin line | Popen by runner |
| **Initializing** | ClaudeSDKClient connecting, hooks registering | First invocation parsed |
| **Executing** | Running a turn (client.query + receive_response) | Prompt received |
| **Idle** | Turn complete, waiting for next stdin line | turn_complete emitted |
| **Shutting down** | Closing ClaudeSDKClient, cleaning up | shutdown message or stdin EOF |
| **Exited** | Process terminated | Normal exit or crash |

### Crash Recovery

**Policy: Accept session loss on crash** (simplest, recommended for initial implementation).

If the executor process crashes:
1. Supervisor detects via `process.poll()` (non-zero exit code)
2. Supervisor reports `run_failed` for any in-progress run
3. Supervisor removes process from session registry
4. Coordinator marks session as `failed`
5. User must start a new session

The `executor_session_id` is still stored in the coordinator. If the SDK ever supports
`ClaudeSDKClient` + resume in the future, recovery becomes possible without architectural
changes.

---

## NDJSON Protocol Specification

### Runner → Executor (stdin)

Line 1 (initial invocation):
```json
{"schema_version": "2.2", "mode": "start", "session_id": "ses_abc", "parameters": {"prompt": "..."}, "agent_blueprint": {...}, "executor_config": {...}}
```

Subsequent lines (follow-up turns):
```json
{"type": "turn", "run_id": "run_xyz", "parameters": {"prompt": "follow-up"}, "agent_blueprint": {...}}
```

Shutdown:
```json
{"type": "shutdown"}
```

### Executor → Runner (stdout)

Turn complete:
```json
{"type": "turn_complete", "run_id": "run_xyz", "result": "assistant response text"}
```

Note: Session events (bind, user_message, assistant_message, result) continue to flow via
HTTP to the Runner Gateway as they do today. The stdout protocol is ONLY for turn lifecycle
signaling between executor and supervisor.

---

## What Is Preserved (No Changes)

- Session ID scheme and format
- Agent Run concept (one run per turn)
- Run lifecycle (PENDING → CLAIMED → RUNNING → COMPLETED)
- Blueprint resolution (coordinator resolves before dispatch)
- Session binding (first turn, via Gateway HTTP)
- Session event emission (via Gateway HTTP, not stdout)
- Affinity-based routing (hostname + executor_profile)
- Long-poll dispatch (coordinator → runner)
- Callback processor (async parent/child orchestration)
- Stop command handling (SIGTERM to process kills session)
- Hook execution on coordinator side
- Runner registration and heartbeat

## What Changes

| Component | File | Change | Scope |
|-----------|------|--------|-------|
| Runner Registry | `registry.py` | Add `session_id → process` index | Small |
| Runner Executor | `executor.py` | Keep stdin open, write NDJSON | Small |
| Runner Poller | `poller.py` | Route resume to existing process | Medium |
| Runner Supervisor | `supervisor.py` | Stdout reader thread per process | Medium |
| Executor entry point | `ao-claude-code-exec` | NDJSON stdin loop | Medium |
| Executor SDK client | `sdk_client.py` | Multi-turn session loop | Large |
| Executor events | `sdk_client.py` | Move user_message emit to turn loop | Small |
| Invocation schema | `invocation.py` | `from_stdin()` reads one line | Small |
| Test harness | `harness.py` | Add MultiTurnExecutor class | Medium |
| Resume tests | `test_resume_mode.py` | Convert to multi-turn tests | Medium |

---

## Resource Management

### Idle processes

Each idle executor process holds:
- One Python interpreter (~30-50 MB RSS)
- One Claude CLI subprocess (~20-30 MB RSS, mostly the bundled binary)
- One `ClaudeSDKClient` with open stdin/stdout pipes

Estimated per-session idle cost: ~50-80 MB.

### Idle timeout

Implement an idle timeout in the supervisor. If no turn arrives within N minutes
(configurable, default 30), the supervisor sends a shutdown message to the executor
and reports the session as completed.

### Max concurrent sessions

The runner should enforce a max concurrent sessions limit (configurable).
When the limit is reached, reject new start_session runs.

---

## Implementation Phases

### Phase 1: Executor multi-turn (can be tested in isolation)
- Modify `ao-claude-code-exec` entry point for NDJSON stdin loop
- Modify `sdk_client.py` for multi-turn session loop
- Add `MultiTurnExecutor` to test harness
- Write basic multi-turn integration tests
- **Testable with the test harness alone** (no runner changes needed)

### Phase 2: Runner integration
- Modify `registry.py` for session-to-process mapping
- Modify `executor.py` to keep stdin open
- Modify `poller.py` to route resume to existing processes
- Modify `supervisor.py` for stdout reading + turn completion

### Phase 3: Clean up and harden
- Add idle timeout to supervisor
- Add max concurrent sessions limit
- Convert all resume tests to multi-turn tests
- Remove dead resume code paths (no more `--resume` flag usage)
- Remove `[DIAG]` lines from previous sessions
