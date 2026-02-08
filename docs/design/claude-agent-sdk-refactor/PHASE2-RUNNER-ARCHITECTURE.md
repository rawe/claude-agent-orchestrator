# Phase 2: Runner Integration — Architecture

## Status: Partially superseded

> **Note**: The registry design (section 1) is superseded by `REGISTRY-REDESIGN.md`
> (session-primary indexing replaces the dual-index proposal). The stop handling in
> section 3.3 is superseded by `STOP-COMMAND-REDESIGN.md` (session_id-based).
> The stdout reader in section 4 is superseded — use `entry.current_run_id` from
> the registry, NOT `msg["run_id"]` from NDJSON.
>
> The profile/lifecycle sections (section 2) and `send_turn()`/`send_shutdown()` method
> signatures remain valid, EXCEPT `send_turn()` must NOT include `run_id` in the message
> (see `NDJSON-PROTOCOL-SIMPLIFICATION.md`).

## Context

Phase 1 implemented multi-turn at the executor level. The executor process now keeps a
`ClaudeSDKClient` alive across turns, receiving NDJSON on stdin and writing `turn_complete`
to stdout. All tested in isolation — 46 tests pass (see `PHASE1-IMPLEMENTATION-SUMMARY.md`).

Phase 2 makes the **runner** aware of multi-turn. The runner must route resume turns to
existing executor processes instead of spawning new ones.

The challenge: the runner currently assumes **process exit = run complete**. Multi-turn
breaks that assumption. This document defines how to handle both one-shot and persistent
executors through a single, uniform interface.

---

## Current Executor Types

The runner spawns executor subprocesses based on profiles. Each profile declares a `type`
(for the coordinator) and a `command` (the executable).

| Executor | Profile type | Lifecycle | Status |
|----------|-------------|-----------|--------|
| **claude-sdk** | `autonomous` | Persistent (multi-turn) | Active, Phase 1 done |
| **claude-code** | `autonomous` | One-shot | Legacy, will be replaced by claude-sdk |
| **procedural** | `procedural` | One-shot | Active, executes scripts |

### claude-sdk executor

- Reads first stdin line as `ExecutorInvocation`, subsequent lines as NDJSON turn/shutdown messages
- Keeps `ClaudeSDKClient` alive across all turns within one session
- Writes `{"type": "turn_complete", ...}` to stdout after each turn
- Process lifetime = session lifetime
- Supports hooks, MCP servers, structured output

### claude-code executor (legacy)

- Reads all stdin, runs one turn, exits
- Will be deleted once all profiles migrate to claude-sdk
- **Not considered in this design** — all new work targets claude-sdk

### procedural executor

- Reads all stdin via `sys.stdin.read()` (blocks until EOF — closing stdin is mandatory)
- Runs one CLI command, prints JSON result to stdout, exits
- Never resumed, never multi-turn
- Process lifetime = one run

---

## Design: Lifecycle-Aware Process Management

### Core Concept

The runner does not need to know _which_ executor it is managing. It only needs to know
the executor's **lifecycle mode** — how the process signals completion and whether it
stays alive between runs.

Two lifecycle modes:

| Mode | Completion signal | Process after run | Stdin after payload |
|------|------------------|-------------------|-------------------|
| `one_shot` | Process exit (exit code) | Terminates | Closed |
| `persistent` | stdout NDJSON (`turn_complete`) | Stays alive (idle) | Kept open |

### Profile Enhancement

The executor profile gains a `lifecycle` field:

```json
{
  "type": "autonomous",
  "lifecycle": "persistent",
  "command": "executors/claude-sdk-executor/ao-claude-code-exec",
  "config": { ... }
}
```

```json
{
  "type": "procedural",
  "command": "executors/procedural-executor/ao-procedural-exec",
  "agents_dir": "executors/procedural-executor/scripts/echo/agents"
}
```

Rules:
- **Default**: `"one_shot"` when `lifecycle` is absent — all existing profiles work unchanged
- **`persistent`**: Must be explicitly declared; executor must implement the NDJSON protocol (see `NDJSON-PROTOCOL-REFERENCE.md`)
- The runner branches on `lifecycle` at process spawn time, not per-operation

### Why This Is Not Executor-Specific Branching

The runner never checks `if profile.name == "claude-sdk"`. It checks `if profile.lifecycle == "persistent"`.
Any future executor that implements the NDJSON stdout protocol can declare `"persistent"` and get
multi-turn support with zero runner changes.

Analogy: systemd distinguishes `Type=oneshot` from `Type=simple`. That is lifecycle-aware management,
not service-specific branching.

---

## Component Changes

### Overview

| Component | File | Change | Scope |
|-----------|------|--------|-------|
| Profile schema | `profiles/*.json` | Add `lifecycle` field | Trivial |
| Profile loader | `lib/executor.py` | Parse `lifecycle` into `ExecutorProfile` | Small |
| Registry | `lib/registry.py` | Add session-to-process index | Small |
| Executor spawner | `lib/executor.py` | Conditional stdin handling, new `send_turn`/`send_shutdown` | Small |
| Poller | `lib/poller.py` | Route resume to existing process | Medium |
| Supervisor | `lib/supervisor.py` | Stdout reader threads, split exit handling | Medium |

### 1. Registry — Dual Index

**File**: `lib/registry.py`

The registry gains a second index for routing resume runs to live processes.

```
Primary:    _runs[run_id]              → RunningRun   (active run tracking)
Secondary:  _session_processes[session_id] → RunningRun   (live process lookup)
```

Both point to the **same RunningRun object**. They serve different purposes:
- `_runs` answers: "Is this run still in progress?" (used by supervisor, stop command)
- `_session_processes` answers: "Does this session have a live process?" (used by poller for resume routing)

**RunningRun gets a `persistent` flag**:

```python
@dataclass
class RunningRun:
    process: subprocess.Popen
    started_at: datetime
    run_id: str
    session_id: str
    persistent: bool = False
```

**New methods**:

| Method | Purpose |
|--------|---------|
| `get_session_process(session_id)` | Look up live process for resume routing |
| `add_session_process(session_id, running_run)` | Register persistent process |
| `remove_session_process(session_id)` | Remove on process exit |
| `swap_run_id(session_id, new_run_id)` | When resume arrives: remove old run_id entry, register new one |

**Lifecycle of entries**:

```
start_session (persistent):
  → add_run(run_id, session_id, process, persistent=True)
  → add_session_process(session_id, running_run)

turn_complete (from stdout reader):
  → remove_run(run_id)             # run done
  → session_process stays           # process alive, waiting

resume_session routed:
  → swap_run_id(session_id, new_run_id)
  → session_process unchanged

process exit:
  → remove_run(current_run_id)     # if any active run
  → remove_session_process(session_id)
```

### 2. Executor Spawner — Conditional Stdin, Turn/Shutdown Methods

**File**: `lib/executor.py`

**Profile loading**: `ExecutorProfile` gains `lifecycle: str = "one_shot"`. Parsed from profile JSON,
defaults to `"one_shot"` when absent.

**`_execute_with_payload()` changes** (currently line 288-355):

```python
# Current (both executors):
process.stdin.write(payload_json)
process.stdin.close()

# New:
if self.profile and self.profile.lifecycle == "persistent":
    process.stdin.write(payload_json + "\n")   # NDJSON: newline-delimited
    process.stdin.flush()                       # flush, keep open
else:
    process.stdin.write(payload_json)
    process.stdin.close()                       # one-shot: close signals EOF
```

**New methods**:

```python
def send_turn(self, process: subprocess.Popen, run: Run) -> None:
    """Write NDJSON turn to existing persistent process."""
    msg = json.dumps({"type": "turn", "run_id": run.run_id, "parameters": run.parameters})
    process.stdin.write(msg + "\n")
    process.stdin.flush()

def send_shutdown(self, process: subprocess.Popen) -> None:
    """Send shutdown signal to persistent process."""
    process.stdin.write('{"type": "shutdown"}\n')
    process.stdin.flush()
```

### 3. Poller — Resume Routing

**File**: `lib/poller.py`

**`_handle_run()` changes** (currently line 144-164):

```python
def _handle_run(self, run: Run) -> None:
    if run.type == "resume_session":
        existing = self.registry.get_session_process(run.session_id)
        if existing:
            self._route_resume(run, existing)
            return
        # No live process — fail explicitly (NO fallback, NO new process)
        self.api_client.report_failed(
            self.runner_id, run.run_id,
            f"No live executor process for session {run.session_id}"
        )
        return

    # start_session — spawn new process
    process = self.executor.execute_run(run)
    self.registry.add_run(run.run_id, run.session_id, process,
                          persistent=self.executor.is_persistent)
    if self.executor.is_persistent:
        self.registry.add_session_process(run.session_id, ...)
    self.api_client.report_started(self.runner_id, run.run_id)
```

**New `_route_resume()` method**:

```python
def _route_resume(self, run: Run, existing: RunningRun) -> None:
    try:
        self.registry.swap_run_id(run.session_id, run.run_id)
        self.executor.send_turn(existing.process, run)
        self.api_client.report_started(self.runner_id, run.run_id)
    except BrokenPipeError:
        self.api_client.report_failed(
            self.runner_id, run.run_id,
            "Executor process is no longer running"
        )
```

**`_handle_stop()` changes** (currently line 166-203):

For persistent processes, send shutdown via stdin before SIGTERM:

```python
if running_run.persistent:
    try:
        self.executor.send_shutdown(running_run.process)
        running_run.process.wait(timeout=5)
        # Clean exit
        ...
        return
    except Exception:
        pass  # Fall through to SIGTERM

# SIGTERM path (existing, unchanged)
```

### 4. Supervisor — Stdout Readers + Split Exit Handling

**File**: `lib/supervisor.py`

This is the most significant change. The supervisor gains two detection mechanisms that
work in parallel:

```
┌─────────────────────────────────────────────────────┐
│                    Supervisor                        │
│                                                      │
│  Per persistent process:                             │
│    stdout reader thread ──→ turn_complete → report   │
│                                                      │
│  Poll loop (all processes):                          │
│    process.poll() ──→ exit detected → handle exit    │
│                                                      │
│  Dedup set:                                          │
│    _reported_runs: set[str] → prevent double-report  │
└─────────────────────────────────────────────────────┘
```

**Stdout reader thread** (one per persistent process, started at spawn time):

```python
def _stdout_reader_loop(self, session_id: str, process: subprocess.Popen) -> None:
    """Read NDJSON from persistent process stdout."""
    for line in iter(process.stdout.readline, ''):
        if not line.strip():
            continue
        try:
            msg = json.loads(line.strip())
        except json.JSONDecodeError:
            continue  # skip non-JSON output
        if msg.get("type") == "turn_complete":
            run_id = msg["run_id"]
            self._report_turn_complete(run_id)
    # EOF → process exited or stdout closed
```

**`_report_turn_complete()`**:

```python
def _report_turn_complete(self, run_id: str) -> None:
    if run_id in self._reported_runs:
        return  # already reported (race protection)
    self._reported_runs.add(run_id)
    self.registry.remove_run(run_id)  # run done, process stays
    self.api_client.report_completed(self.runner_id, run_id)
```

**`_check_runs()` changes** — split into two paths:

| Process type | Exit meaning | Action |
|-------------|-------------|--------|
| `one_shot` | Run complete | `report_completed` (exit 0) or `report_failed` (non-zero) — **existing behavior** |
| `persistent` | Crash or shutdown | If active run in registry → `report_failed`. Clean up `_session_processes`. |

```python
def _check_runs(self) -> None:
    runs = self.registry.get_all_runs()
    for run_id, running_run in runs.items():
        return_code = running_run.process.poll()
        if return_code is not None:
            if running_run.persistent:
                self._handle_persistent_exit(run_id, running_run, return_code)
            else:
                self._handle_completion(run_id, running_run, return_code)
```

**`_handle_persistent_exit()`** — handles unexpected death of a persistent process:

```python
def _handle_persistent_exit(self, run_id, running_run, return_code):
    self.registry.remove_run(run_id)
    self.registry.remove_session_process(running_run.session_id)

    if run_id not in self._reported_runs:
        self._reported_runs.add(run_id)
        # Process died with an active run — this is a crash
        error_msg = self._read_stderr(running_run)
        self.api_client.report_failed(self.runner_id, run_id, error_msg)
```

**Idle process cleanup**: When a persistent process exits and there is no active run
(i.e., the process was idle between turns and shut down), the supervisor only needs to
clean up `_session_processes`. No run to report on.

---

## Thread Safety

Three threads touch the registry concurrently:

| Thread | Reads | Writes |
|--------|-------|--------|
| Poller thread | `get_session_process()`, `get_run()` | `add_run()`, `swap_run_id()` |
| Supervisor poll loop | `get_all_runs()` | `remove_run()`, `remove_session_process()` |
| Stdout reader thread (per process) | — | `remove_run()` (via `_report_turn_complete`) |

The existing `threading.Lock` in the registry protects all dict operations. Each method
acquires the lock independently. This is sufficient because:

- `get_all_runs()` returns a **copy** (line 57), so iteration is safe
- `remove_run()` uses `dict.pop()` which is atomic under the lock
- `swap_run_id()` is a single lock acquisition (remove old + add new)

**Double-report prevention**: The `_reported_runs: set` in the supervisor prevents the
stdout reader and the poll loop from both reporting the same run. This handles the edge
case where a persistent process writes `turn_complete` and then exits nearly simultaneously.

---

## Stop Command Behavior

| Process lifecycle | Stop sequence |
|-------------------|--------------|
| `one_shot` | SIGTERM, wait 5s, SIGKILL if needed (unchanged) |
| `persistent` | stdin `{"type": "shutdown"}`, wait 5s, then SIGTERM, then SIGKILL |

---

## What Does NOT Change

- Coordinator API and run lifecycle (PENDING -> CLAIMED -> RUNNING -> COMPLETED)
- Session events via HTTP (bind, user_message, assistant_message, result)
- Affinity-based routing (hostname + executor_profile)
- Long-poll dispatch
- Callback processor
- Runner registration and heartbeat
- Procedural executor code (zero changes)

---

## References

| Document | Purpose |
|----------|---------|
| `MULTI-TURN-DESIGN.md` | Original multi-turn architecture (Phases 1-3) |
| `NDJSON-PROTOCOL-REFERENCE.md` | Complete NDJSON stdin/stdout protocol spec |
| `MULTI-TURN-EXECUTOR-ARCHITECTURE.md` | Executor process lifecycle and states |
| `PHASE1-IMPLEMENTATION-SUMMARY.md` | Phase 1 completed changes and test results |
