# Phase 2: Multi-Turn Runner Integration — Implementation Plan

## Status: Active (revised 2026-02-08)

## Overview

Phase 2 makes the runner and coordinator aware of multi-turn persistent executor processes.
The runner must route resume turns to existing processes (instead of spawning new ones),
detect turn completion via stdout NDJSON (instead of process exit), and report session
lifecycle status changes to the coordinator. The coordinator must accept new session
statuses (`idle`, `failed`), route stop commands by session_id, and fix the existing bug
where `report_run_failed()` does not update session status.

Five architecture documents define the changes. This plan organizes them into 3
implementation phases where each phase produces a working, testable system.

---

## Architecture Documents

| # | Document | Scope | Primary Components |
|---|----------|-------|-------------------|
| 1 | `REGISTRY-REDESIGN.md` | Session-primary process registry | Runner: registry.py |
| 2 | `STOP-COMMAND-REDESIGN.md` | Stop commands flow as session_id | Coordinator + Runner |
| 3 | `SESSION-STATUS-REDESIGN.md` | 7 session statuses, idle/failed | Coordinator + Runner |
| 4 | `NDJSON-PROTOCOL-SIMPLIFICATION.md` | Remove run_id from executor NDJSON | Executor: sdk_client.py |
| 5 | `EXECUTOR-SESSION-ID-SCOPE.md` | No changes for Phase 2 | None |

### Superseded Documents

`PHASE2-RUNNER-ARCHITECTURE.md` was the original design draft. It has been superseded in
two areas:

- **Section 1 (Registry — Dual Index)**: Superseded by `REGISTRY-REDESIGN.md`. The
  dual-index design (`_runs` + `_session_processes`) is replaced by session-primary
  indexing (`_sessions` + `_run_index`).
- **Section 4 (Supervisor stdout reader)**: The code sample reads `msg["run_id"]` from the
  NDJSON message. This contradicts `NDJSON-PROTOCOL-SIMPLIFICATION.md` and
  `REGISTRY-REDESIGN.md`, which specify using `entry.current_run_id` from the registry.

The profile/executor sections (lifecycle field, `send_turn`, `send_shutdown` method
signatures) remain valid, **except** `send_turn()` must NOT include `run_id` in the message
(see NDJSON-PROTOCOL-SIMPLIFICATION.md).

---

## Consistency Check

The 5 architecture documents were reviewed for contradictions.

### 1. Naming Inconsistency (STOP-COMMAND vs REGISTRY)

**STOP-COMMAND-REDESIGN.md** section 3.4 references `get_session_process()`,
`remove_session_process()`, `remove_run()`, and `entry.run_id`.
**REGISTRY-REDESIGN.md** defines `get_session()`, `remove_session()`, `clear_run()`,
and `entry.current_run_id`.

**Resolution**: Use REGISTRY-REDESIGN.md names exclusively. STOP-COMMAND-REDESIGN.md
code samples use older naming from the superseded dual-index design. Follow the intent
of the stop command doc, not its code samples.

### 2. `send_turn()` Format (PHASE2-RUNNER-ARCHITECTURE vs NDJSON-PROTOCOL-SIMPLIFICATION)

PHASE2-RUNNER-ARCHITECTURE.md section 2 shows:
```python
msg = json.dumps({"type": "turn", "run_id": run.run_id, "parameters": run.parameters})
```

NDJSON-PROTOCOL-SIMPLIFICATION.md (authoritative) shows:
```json
{ "type": "turn", "parameters": { "prompt": "Add auth" } }
```

**Resolution**: Implement `send_turn()` WITHOUT `run_id` from the start. The executor
should never see or echo `run_id`. The runner owns run_id mapping via the registry.

### 3. `report_completed` Session Status Signal

SESSION-STATUS-REDESIGN.md recommends the runner include `session_status` in the
completion report body (`{"session_status": "idle"}` or `{"session_status": "finished"}`).
The current `report_completed` API sends `{"runner_id": "...", "status": "success"}`.
The coordinator currently hardcodes `session.status = "finished"`.

**Resolution**: Extend `report_completed()` to include `session_status` field. Coordinator
reads it and uses it instead of hardcoding "finished". Done in Phase C (coordinator changes).

### 4. No Other Contradictions Found

All 5 documents agree on: session_id as primary key, stop flows as session_id, `idle`
status semantics, bind call kept as-is, executor_session_id stored but not used for resume.

---

## Implementation Phases

### Phase A: Registry Rewrite + Profile + Executor Spawner + All Callers

**Scope**: Rewrite the registry to session-primary indexing. Update ALL callers (poller,
supervisor) to use new method names. Add `lifecycle` field to executor profiles. Modify
`executor.py` (runner-level) for conditional stdin handling and new `send_turn()`/
`send_shutdown()` methods. `send_turn()` sends WITHOUT `run_id` per
NDJSON-PROTOCOL-SIMPLIFICATION.md.

**Documents**: REGISTRY-REDESIGN.md (all sections), PHASE2-RUNNER-ARCHITECTURE.md
(profile/executor sections only, NOT registry section)

**Files Changed**:

| File | Change |
|------|--------|
| `servers/agent-runner/lib/registry.py` | Complete rewrite: `ProcessRegistry` with `SessionProcess` dataclass, `_sessions` + `_run_index`, all 8 methods per REGISTRY-REDESIGN.md |
| `servers/agent-runner/lib/executor.py` | Add `lifecycle` to `ExecutorProfile` (default `"one_shot"`), conditional stdin (`flush` for persistent, `close` for one-shot), `send_turn()` (no run_id), `send_shutdown()`, `is_persistent` property |
| `servers/agent-runner/lib/poller.py` | Update all registry calls: `add_run()` -> `register_session()`, `get_run()` -> `get_session_by_run()`, `remove_run()` -> `remove_session()`. Stop handler: `get_run(run_id)` -> `get_session_by_run(run_id)`. No behavioral change yet. |
| `servers/agent-runner/lib/supervisor.py` | Update all registry calls: `get_all_runs()` -> `get_all_sessions()`, `remove_run()` -> `remove_session()`. Iteration changes from `run_id, running_run` to `session_id, entry`. Completion handler accesses `entry.current_run_id`. No behavioral change yet. |
| `servers/agent-runner/agent-runner` | Update import: `RunningRunsRegistry` -> `ProcessRegistry`. Update instantiation: `RunningRunsRegistry()` -> `ProcessRegistry()`. |
| `servers/agent-runner/profiles/claude-sdk-executor.json` | Add `"lifecycle": "persistent"` |

**What Does NOT Change**: No new multi-turn behavior. Poller still spawns a new process
for every run (both start and resume). Supervisor still detects completion via process
exit only. No coordinator changes. No executor (sdk_client.py) changes.

**Acceptance Criteria**:
1. `ProcessRegistry` implements all 8 methods: `register_session()`, `get_session()`, `get_session_by_run()`, `swap_run()`, `clear_run()`, `remove_session()`, `get_all_sessions()`, `count()`
2. `SessionProcess` dataclass has fields: `process`, `session_id`, `started_at`, `persistent`, `current_run_id`
3. `ExecutorProfile` parses `lifecycle` field (defaults to `"one_shot"`)
4. `RunExecutor.is_persistent` returns True for persistent profiles
5. `_execute_with_payload()` keeps stdin open (newline + flush) for persistent, closes for one-shot
6. `send_turn()` writes `{"type": "turn", "parameters": {...}}` to stdin (no `run_id`)
7. `send_shutdown()` writes `{"type": "shutdown"}` to stdin
8. Poller calls `register_session()` instead of `add_run()`, etc.
9. Supervisor iterates `get_all_sessions()` keyed by `session_id`
10. **All 46 existing tests pass** (one-shot behavioral path unchanged, just method names differ)

**Risk**: Low. Method renames in callers are mechanical. The persistent lifecycle path
is not exercised by existing tests (no test spawns a persistent executor yet). One-shot
path is identical in behavior.

**Estimated Scope**: ~200 lines changed/added across 5 files.

---

### Phase B: Multi-Turn Core + NDJSON Simplification

**Scope**: The poller learns to route resume turns to existing persistent processes. The
supervisor gains stdout reader threads for persistent processes and splits exit handling
into one-shot vs persistent paths. The executor's NDJSON protocol is simplified (remove
`run_id` passthrough from `sdk_client.py`). A minimal echo executor is created for
runner-level integration tests.

**Documents**: REGISTRY-REDESIGN.md (consumer usage section 4), NDJSON-PROTOCOL-SIMPLIFICATION.md

**IMPORTANT**: The stdout reader uses `entry.current_run_id` from the registry, NOT
`msg["run_id"]` from the NDJSON message. This follows REGISTRY-REDESIGN.md section 4,
which supersedes PHASE2-RUNNER-ARCHITECTURE.md section 4.

**Files Changed**:

| File | Change |
|------|--------|
| `servers/agent-runner/lib/poller.py` | `_handle_run()`: if `resume_session` and persistent process exists, route via `swap_run()` + `send_turn()`. New `_route_resume()` method. Resume-while-busy guard: reject if `entry.current_run_id is not None`. Start flow passes `persistent=self.executor.is_persistent` to `register_session()`. |
| `servers/agent-runner/lib/supervisor.py` | `_check_sessions()` replaces `_check_runs()`. `_stdout_reader_loop()` thread per persistent process (started by poller or supervisor after registration). `_report_turn_complete(session_id)` looks up `current_run_id` from registry, reports completed, calls `clear_run()`. `_handle_persistent_exit()` vs `_handle_oneshot_exit()`. `_reported_runs` dedup set with explicit lock. Idle process exit: log + registry cleanup only (coordinator reporting added in Phase C). |
| `servers/agent-runner/executors/claude-sdk-executor/lib/sdk_client.py` | Remove 4 lines: `initial_run_id` extraction (line 395), `"run_id": initial_run_id` in turn_complete (line 450), `turn_run_id` extraction (line 477), `"run_id": turn_run_id` in turn_complete (line 507). Net: -4 lines. |

**Dependencies**: Phase A (registry, executor spawner, profile lifecycle must be in place)

**Acceptance Criteria**:
1. `_handle_run()` for `start_session` spawns process, registers via `register_session()`, starts stdout reader thread if persistent
2. `_handle_run()` for `resume_session` on persistent session routes to existing process via `get_session()` + `swap_run()` + `send_turn()`
3. **Resume-while-busy guard**: If `entry.current_run_id is not None` when resume arrives, reject with explicit error (no queuing, no overlapping turns)
4. Resume for non-existent session fails explicitly with error message (no fallback, no new process spawned)
5. Supervisor stdout reader thread reads NDJSON from persistent process stdout
6. `_report_turn_complete()` uses registry `current_run_id` (NOT message run_id), reports completed, calls `clear_run(session_id)`
7. One-shot process exit still reports completed/failed as before (`_handle_oneshot_exit`)
8. Persistent process exit with active run (`current_run_id is not None`) reports failed via `_handle_persistent_exit()`
9. Persistent process exit while idle (`current_run_id is None`) logs warning and calls `remove_session()` only (coordinator reporting deferred to Phase C)
10. `_reported_runs` dedup set with explicit lock prevents double-reporting between stdout reader and process poll loop
11. Executor `turn_complete` messages no longer contain `run_id` field
12. Executor `turn` messages no longer require or read `run_id` field
13. **All 46 existing tests still pass** (one-shot behavior unchanged)
14. New runner-level multi-turn test validates: start -> turn_complete -> resume -> turn_complete -> shutdown -> process exits cleanly

**Note on idle process exit (criteria #9)**: Between Phase B and Phase C, when an idle
persistent process exits, the runner can only log and clean up the registry. The coordinator
endpoint for reporting idle process exit (`POST /runner/sessions/{session_id}/status`) does
not exist until Phase C. This is acceptable for initial development -- the degenerate case
of an idle process exiting during development is non-critical.

**Note on session status during Phase B**: After Phase B, the coordinator still hardcodes
`session.status = "finished"` on turn completion (it does not know about `idle` yet). This
means multi-turn sessions will show `finished` status after each turn until Phase C fixes
it. Phase B tests should verify runner behavior (registry state, turn routing) only, not
coordinator session status.

**Test infrastructure**: Create a minimal "echo executor" that implements the NDJSON
protocol (reads invocation + turn messages from stdin, writes `turn_complete` to stdout,
responds to shutdown) without making Claude API calls. This enables fast, deterministic
runner-level integration tests.

**Risk**: Medium. Three threads (poller, supervisor poll loop, stdout reader) access the
registry concurrently. The `_reported_runs` dedup set with explicit lock handles the race
between `turn_complete` processing and process exit detection. Integration test coverage
is critical.

**Estimated Scope**: ~250 lines changed/added across 3 files + echo executor + tests.

---

### Phase C: Coordinator + Runner Protocol Changes

**Scope**: Coordinator learns new session statuses (`idle`, `failed`), accepts
`session_status` in run completion reports, fixes the `report_run_failed()` bug,
changes stop command protocol from `run_id` to `session_id`, and adds the
`POST /runner/sessions/{session_id}/status` endpoint for idle process exit reporting.
Runner protocol changes (api_client, poller stop handler, supervisor reporting) are
made atomically with coordinator changes.

**Documents**: SESSION-STATUS-REDESIGN.md, STOP-COMMAND-REDESIGN.md

**Coordinator Files Changed**:

| File | Change |
|------|--------|
| `servers/agent-coordinator/main.py` | `_stop_run()`: pass `session_id` to stop queue instead of `run_id`. `stop_run()`: delegate to `stop_session()`. `stop_session()`: handle `idle` state (same as `running`). `report_run_completed()`: read `session_status` from request body, use it instead of hardcoding `"finished"`. `report_run_failed()`: update session status to `"failed"` (bug fix). `report_run_started()`: transition session `idle` -> `running` on resume. `poll_for_runs()`: return `{"stop_sessions": [...]}` instead of `{"stop_runs": [...]}`. `GET /sessions/{session_id}/result`: allow `idle` status. New endpoint: `POST /runner/sessions/{session_id}/status` for idle process exit. |
| `servers/agent-coordinator/services/stop_command_queue.py` | Comment update: `run_ids` -> `session_ids` in `pending_stops` docstring |
| `servers/agent-coordinator/services/callback_processor.py` | `on_child_completed()`: change `parent_status == "finished"` to `parent_status in ("finished", "idle")` |

**Runner Files Changed** (must match coordinator):

| File | Change |
|------|--------|
| `servers/agent-runner/lib/api_client.py` | `PollResult.stop_sessions` replaces `stop_runs`. `report_completed()` gains `session_status` parameter. New `report_session_status(session_id, status)` method for idle process exit. |
| `servers/agent-runner/lib/poller.py` | Iterate `result.stop_sessions` instead of `result.stop_runs`. `_handle_stop()` takes `session_id` instead of `run_id`, uses `registry.get_session()`. Graceful shutdown for persistent processes: `send_shutdown()` before SIGTERM. |
| `servers/agent-runner/lib/supervisor.py` | `_report_turn_complete()` calls `report_completed(..., session_status="idle")`. One-shot `_handle_oneshot_exit()` calls `report_completed(..., session_status="finished")`. `_handle_persistent_exit()` for idle exit calls `report_session_status(session_id, "finished"/"failed")`. |

**Dependencies**: Phase B (multi-turn core must work before protocol changes)

**Acceptance Criteria**:
1. `poll_for_runs()` returns `{"stop_sessions": [...]}` instead of `{"stop_runs": [...]}`
2. `_stop_run()` passes `session_id` (not `run_id`) to stop command queue
3. `stop_run(run_id)` delegates to `stop_session(session_id)`
4. `stop_session()` handles `idle` state (sends stop command, transitions to `stopping`)
5. `report_run_completed()` reads `session_status` from request body, sets session to that status (defaults to `"finished"` for backward compatibility with one-shot runners)
6. `report_run_failed()` updates session status to `"failed"` (bug fix -- previously left session as `running`)
7. `report_run_started()` transitions session from `idle` to `running` when a resume turn starts
8. `callback_processor.on_child_completed()` checks `parent_status in ("finished", "idle")`
9. `GET /sessions/{session_id}/result` allows `idle` status (not just `finished`)
10. New `POST /runner/sessions/{session_id}/status` endpoint works for idle process exit reporting
11. Runner `PollResult` uses `stop_sessions` field
12. Runner `report_completed()` sends `session_status` parameter
13. Runner `_handle_stop()` takes `session_id`, uses `registry.get_session()`, sends `shutdown` for persistent before SIGTERM
14. Runner `_handle_persistent_exit()` for idle exit calls `report_session_status()`
15. **All 46 existing tests still pass**
16. Stop command for idle session works correctly (session between turns, no active run)
17. Multi-turn session status lifecycle: `pending` -> `running` -> `idle` -> `running` -> `idle` -> `finished`

**Risk**: Medium. Protocol change (`stop_runs` -> `stop_sessions`) is a breaking change
between coordinator and runner but safe because they deploy atomically (monorepo). Multiple
coordinator endpoints touched -- verify existing one-shot flows are unaffected. The
`session_status` field in `report_completed()` must default to `"finished"` so the one-shot
path continues working without changes.

**Estimated Scope**: ~150 lines changed across coordinator + runner.

---

## Dependency Graph

```
Phase A: Registry + Profile + Executor + All Callers
    |
    v
Phase B: Multi-Turn Core + NDJSON Simplification
    |
    v
Phase C: Coordinator + Runner Protocol Changes
```

**Sequential**: Each phase depends on the previous. No parallelism because:
- Phase B uses Phase A's registry API and executor spawner
- Phase C changes the protocol that Phase B's supervisor and poller consume

**Within Phase C**: Coordinator and runner changes MUST be made together. The stop
protocol rename (`stop_runs` -> `stop_sessions`) is a breaking change -- both sides
must change atomically (same commit, monorepo deployment).

---

## Phase Execution Notes

### Each Phase Is One AI Session

Each phase is designed to be completable in a single AI coding session. The scope is
bounded and the acceptance criteria are testable. At the end of each phase, the system
works correctly and all tests pass.

### Test Strategy

- **Phase A**: Existing 46 integration tests must pass. No new tests needed (method
  renames are mechanical, no behavioral change).
- **Phase B**: Existing 46 tests must pass. Add new runner-level multi-turn tests using
  echo executor (start -> turn_complete -> resume -> turn_complete -> shutdown). Tests
  verify runner behavior (registry state, turn routing), NOT coordinator session status
  (which is still wrong until Phase C).
- **Phase C**: Existing tests may need minor updates for `stop_runs` -> `stop_sessions`
  if any integration tests exercise stop commands (check fixtures). Add tests for idle
  session stop, session status lifecycle.

### Echo Executor for Testing (Phase B)

Create a minimal executor script that:
- Reads `ExecutorInvocation` from stdin line 1
- Immediately writes `turn_complete` to stdout (with configurable delay)
- Reads subsequent NDJSON lines (turn, shutdown) from stdin
- For `turn` messages: writes `turn_complete` to stdout
- For `shutdown`: exits cleanly with code 0
- Exits with configurable return code for error testing

This enables fast, deterministic runner-level tests without Claude API calls.

### What Is NOT In Phase 2

| Item | Reason | Where |
|------|--------|-------|
| Dashboard changes | Separate task (display `idle` and `failed` statuses) | SESSION-STATUS-REDESIGN.md section 8 |
| Chat UI changes | Separate task | SESSION-STATUS-REDESIGN.md section 8 |
| executor_session_id cleanup | Phase 3 optional | EXECUTOR-SESSION-ID-SCOPE.md |
| Legacy claude-code executor deletion | Separate migration task | N/A |
| Idle timeout for persistent processes | Not designed yet | Future |

---

## Risk Notes

1. **Thread safety in supervisor**: Three threads (poller, supervisor poll loop, stdout
   reader) access the registry concurrently. The `_reported_runs` dedup set MUST use an
   explicit lock -- the check-then-act pattern (`if run_id in set ... set.add(run_id)`)
   is NOT atomic even under the GIL if another thread modifies the set between check and
   add. Use a dedicated lock or the registry's existing lock to guard the dedup check.

2. **Stdin pipe handling**: Persistent processes keep stdin open. If the runner crashes
   without sending shutdown, the executor process will hang on `stdin.readline()`. The
   executor already handles this (EOF detection in `_read_stdin_line()`), but verify
   in integration tests.

3. **Stop during turn_complete race**: A stop command may arrive while the stdout reader
   is processing turn_complete. The dedup set (with lock) and registry atomicity handle
   this, but integration test coverage is important.

4. **Protocol rename atomicity**: `stop_runs` -> `stop_sessions` is a breaking change.
   Safe in monorepo but must be committed atomically (coordinator + runner in same commit).

5. **Callback processor `finished` semantics**: The callback processor currently treats
   `finished` as "idle and resumable." After Phase C, `finished` means "permanently done"
   for persistent sessions. The check changes to `in ("finished", "idle")`. One-shot
   executors still use `finished` as the idle-equivalent (process exited, resume spawns
   new process). This dual meaning is semantically correct: `finished` means "session is
   in a state where a callback resume can be created." For one-shot, that is after process
   exit. For persistent, that is `idle`. Both are captured by `in ("finished", "idle")`.

6. **Resume-while-busy**: A resume could arrive while a turn is still executing. The
   poller MUST check `entry.current_run_id is not None` and reject the resume. Without
   this guard, `swap_run()` would succeed but the turn message would queue in stdin,
   and `report_started()` would create two simultaneously-RUNNING runs for the same
   session. Phase B includes this guard explicitly.

---

## Review Findings Incorporated

This plan incorporates findings from code review (2026-02-08):

1. **Phase A includes all callers** (poller.py, supervisor.py) -- the registry rewrite
   changes method names, so all callers must be updated in the same phase to avoid
   breaking the build.

2. **`send_turn()` implemented without `run_id` from the start** -- per
   NDJSON-PROTOCOL-SIMPLIFICATION.md (authoritative), the turn message contains
   `{"type": "turn", "parameters": {...}}` with no `run_id` field. This avoids
   implementing it wrong and then removing it later.

3. **Phase C (NDJSON simplification) merged into Phase B** -- the ~10 lines of `run_id`
   removal from `sdk_client.py` are a natural part of the multi-turn core work, since
   Phase B's stdout reader already uses `current_run_id` from the registry rather than
   the NDJSON message.

4. **Resume-while-busy guard** added to Phase B acceptance criteria -- prevents overlapping
   turns on the same session.

5. **Idle process exit handling clarified** -- in Phase B, it is log + registry cleanup
   only. Coordinator reporting is added in Phase C.

6. **`_reported_runs` explicit lock** -- documented as required (not optional) in risk
   notes.

---

## References

| Document | Path |
|----------|------|
| Registry Redesign | `docs/design/claude-agent-sdk-refactor/REGISTRY-REDESIGN.md` |
| Stop Command Redesign | `docs/design/claude-agent-sdk-refactor/STOP-COMMAND-REDESIGN.md` |
| Session Status Redesign | `docs/design/claude-agent-sdk-refactor/SESSION-STATUS-REDESIGN.md` |
| NDJSON Protocol Simplification | `docs/design/claude-agent-sdk-refactor/NDJSON-PROTOCOL-SIMPLIFICATION.md` |
| Executor Session ID Scope | `docs/design/claude-agent-sdk-refactor/EXECUTOR-SESSION-ID-SCOPE.md` |
| Phase 2 Runner Architecture (superseded in parts) | `docs/design/claude-agent-sdk-refactor/PHASE2-RUNNER-ARCHITECTURE.md` |
| Phase 1 Summary | `docs/design/claude-agent-sdk-refactor/PHASE1-IMPLEMENTATION-SUMMARY.md` |
