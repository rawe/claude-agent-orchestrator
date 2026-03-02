# Stop Command Redesign: session_id as Primary Key

## Status: Proposal (Phase 2)

## 1. Context

### The Problem

The stop command currently flows as a `run_id` through every layer:

```
Client -> POST /sessions/{session_id}/stop   (session_id entry point)
       -> coordinator resolves run_id         (internal translation)
       -> stop_command_queue.add_stop(runner_id, run_id)
       -> poll response: {"stop_runs": ["run_xxx"]}
       -> runner: registry.get_run(run_id) -> process.terminate()
       -> runner: report_stopped(runner_id, run_id)
```

This worked when 1 process = 1 run. Multi-turn breaks this: 1 process serves N runs
for a single session. The run-keyed registry cannot find the process when a stop
arrives for a session whose original run is already completed.

### Why Stop = Session Termination

Three constraints make stop a permanent, session-level operation:

1. **SDK limitation**: `--resume` + `--input-format stream-json` is not a supported
   CLI combination (GitHub #16712). Once the executor process dies, the SDK session
   cannot be restarted. The `executor_session_id` stored in the sessions table is
   useless after process death.

2. **Multi-turn architecture**: The `ClaudeSDKClient` instance lives in-process.
   Killing the process destroys the client, the conversation context, and all
   in-flight state. There is no recovery path.

3. **Client perspective**: Clients track `session_id` (stable across the conversation).
   They may not know the `current_run_id` because it changes with each turn.

**Therefore**: Stop means "abort this session permanently." The primary key must be
`session_id`, not `run_id`.

### Current Implementation Touchpoints

| Location | File | Current ID | Line |
|----------|------|-----------|------|
| Stop entry (session) | `coordinator/main.py` | `session_id` -> resolves `run_id` | 485-549 |
| Stop entry (run) | `coordinator/main.py` | `run_id` directly | 2102-2113 |
| Stop service | `coordinator/main.py` `_stop_run()` | `run_id` in queue | 421-482 |
| Stop command queue | `coordinator/services/stop_command_queue.py` | `set[run_id]` | 17, 41-52 |
| Poll response | `coordinator/main.py` `poll_for_runs()` | `{"stop_runs": [...]}` | 1439-1443 |
| Runner poll parse | `runner/lib/api_client.py` | `PollResult.stop_runs` | 89, 256 |
| Runner poll loop | `runner/lib/poller.py` | iterates `run_id`s | 114-116 |
| Runner stop handler | `runner/lib/poller.py` `_handle_stop()` | `registry.get_run(run_id)` | 166-203 |
| Runner report back | `runner/lib/api_client.py` `report_stopped()` | `run_id` in URL | 313-320 |
| Coordinator receive | `coordinator/main.py` `report_run_stopped()` | `run_id` in URL | 1701-1741 |

---

## 2. Scope Decision

**Recommendation: Include in Phase 2.**

### Cost Analysis

| Option | Work | Risk | Debt |
|--------|------|------|------|
| **Defer** (workaround: runner does `run_id` -> `session_id` lookup locally) | ~5 lines in poller | Low | Leaves misaligned protocol; every future multi-turn feature must work around it |
| **Include in Phase 2** | ~20 lines changed across 5 files | Low | Clean protocol from day one |

### Rationale

1. **Same code paths**: The registry rekey (task #136) already touches `registry.py`,
   `poller.py`, and `supervisor.py`. Stop handling is in the same files. Doing both
   in one pass avoids re-reading and re-testing the same code twice.

2. **Protocol clarity**: Changing the poll response from `stop_runs` to `stop_sessions`
   now (before any multi-turn runner is deployed) means zero backward-compatibility
   concerns. If deferred, we ship a protocol we know is wrong and have to manage a
   migration later.

3. **Minimal incremental cost**: The stop_command_queue is already ID-agnostic
   (`set[str]`). Only callers and consumers change. ~20 lines total.

4. **Prerequisite for correct multi-turn stop**: Without this change, a stop command
   for a session between turns (no active run_id in registry) would be silently
   ignored. That is a correctness bug, not just a code smell.

**Decision**: Include in Phase 2. No workaround needed.

---

## 3. Changes Required

### 3.1 Coordinator REST API

#### `POST /sessions/{session_id}/stop` -- Primary (no change to URL)

Already exists. Internal logic changes:

**Current** (`_stop_run()` line 467):
```python
stop_command_queue.add_stop(run.runner_id, run.run_id)
```

**New**:
```python
stop_command_queue.add_stop(run.runner_id, run.session_id)
```

The `_stop_run()` function still needs the run object (to get `runner_id` and to
update run status to STOPPING). The only change is what goes into the queue.

#### `POST /runs/{run_id}/stop` -- Convenience wrapper (simplified)

**Current** (line 2102-2113):
```python
async def stop_run(run_id: str):
    run = run_queue.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return await _stop_run(run)
```

**New**:
```python
async def stop_run(run_id: str):
    run = run_queue.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return await stop_session(run.session_id)  # delegate to session stop
```

This ensures a single code path. Both endpoints converge on `stop_session()`.

#### Response format -- No change

Both endpoints already return `session_id` in the response. No API-facing changes
for clients.

### 3.2 Coordinator Internal Changes

#### Stop command queue (`services/stop_command_queue.py`)

**No structural change.** The queue is already ID-agnostic:

```python
pending_stops: set[str] = field(default_factory=set)  # was: run_ids, now: session_ids
```

Only the comment changes. `add_stop(runner_id, id_str)` and
`get_and_clear(runner_id) -> list[str]` work identically regardless of what
the strings represent.

#### `_stop_run()` service function

One line changes: `run.run_id` -> `run.session_id` in the `add_stop()` call.

Run and session status transitions remain unchanged:
- `run.status` -> `STOPPING`
- `session.status` -> `stopping`

Both are set by `_stop_run()` before the stop command is queued. The runner's
report-back later transitions them to STOPPED/stopped.

### 3.3 Coordinator -> Runner Poll Protocol

**Breaking change to field name.** Safe because both components are in the monorepo
and deployed together.

| Direction | Current | New |
|-----------|---------|-----|
| Coordinator response | `{"stop_runs": ["run_xxx"]}` | `{"stop_sessions": ["ses_xxx"]}` |
| Runner parser | `data["stop_runs"]` | `data["stop_sessions"]` |
| PollResult field | `stop_runs: list[str]` | `stop_sessions: list[str]` |

#### Backward compatibility

Not needed. The coordinator and runner are in the same monorepo and always deployed
as a pair. There is no independent versioning. The field rename is atomic across
a single deployment.

### 3.4 Runner Changes

#### `PollResult` model (`api_client.py` line 84-99)

```python
# Current:
stop_runs: list[str] = None     # Run IDs to stop

# New:
stop_sessions: list[str] = None  # Session IDs to stop
```

#### `poll_run()` parser (`api_client.py` line 255-257)

```python
# Current:
if "stop_runs" in data:
    return PollResult(stop_runs=data["stop_runs"])

# New:
if "stop_sessions" in data:
    return PollResult(stop_sessions=data["stop_sessions"])
```

#### Poll loop (`poller.py` line 113-117)

```python
# Current:
if result.stop_runs:
    for run_id in result.stop_runs:
        self._handle_stop(run_id)

# New:
if result.stop_sessions:
    for session_id in result.stop_sessions:
        self._handle_stop(session_id)
```

#### `_handle_stop()` (`poller.py` line 166-203)

This is the most significant runner-side change. The method now takes `session_id`
and uses the Phase 2 registry's `get_session_process()` method for lookup.

```python
def _handle_stop(self, session_id: str) -> None:
    """Stop a session by terminating its executor process."""
    entry = self.registry.get_session_process(session_id)

    if not entry:
        logger.debug(f"Stop command for session {session_id} ignored - no live process")
        return

    run_id = entry.run_id  # current active run_id (may be None if between turns)

    logger.info(f"Stopping session {session_id} (run={run_id}, pid={entry.process.pid})")

    signal_used = "SIGTERM"

    try:
        # For persistent processes: try graceful shutdown first
        if entry.persistent:
            try:
                self.executor.send_shutdown(entry.process)
                entry.process.wait(timeout=5)
                signal_used = "shutdown"
            except Exception:
                pass  # Fall through to SIGTERM

        # SIGTERM path (or first attempt for one-shot)
        if entry.process.poll() is None:
            entry.process.terminate()
            try:
                entry.process.wait(timeout=5)
            except Exception:
                entry.process.kill()
                signal_used = "SIGKILL"
                logger.warning(f"Session {session_id} did not respond to SIGTERM, sent SIGKILL")

        # Clean up registry
        if run_id:
            self.registry.remove_run(run_id)
        self.registry.remove_session_process(session_id)

        # Report back using run_id (coordinator reporting API is run-addressed)
        if run_id:
            try:
                self.api_client.report_stopped(self.runner_id, run_id, signal=signal_used)
                logger.info(f"Session {session_id} stopped (run={run_id}, signal={signal_used})")
            except Exception as e:
                logger.error(f"Failed to report stopped for run {run_id}: {e}")
        else:
            # Session was idle between turns (no active run)
            # No run to report on -- the session is just gone
            logger.info(f"Idle session {session_id} stopped (no active run)")

    except Exception as e:
        logger.error(f"Error stopping session {session_id}: {e}")
```

**Key insight**: The runner reports back to the coordinator using `run_id` (from
`entry.run_id`) because the coordinator's `POST /runner/runs/{run_id}/stopped`
endpoint is run-addressed. This is correct -- the coordinator updates both the
run and session status from that endpoint. If the session is idle (no active run),
there is nothing to report; the session cleanup happens when the coordinator
detects the runner has no active run for that session.

#### Registry dependency

This change depends on the Phase 2 registry (task #136) providing:
- `get_session_process(session_id) -> RunningRun | None`
- `remove_session_process(session_id)`
- `RunningRun.run_id` reflecting the current active run (or None if between turns)

---

## 4. End-to-End Flow

```
Client                    Coordinator                    Runner
  |                           |                             |
  |-- POST /sessions/         |                             |
  |     ses_xxx/stop -------->|                             |
  |                           |                             |
  |                           |-- get_session(ses_xxx)      |
  |                           |-- get_run_by_session_id     |
  |                           |     (ses_xxx) -> run_yyy    |
  |                           |-- run_yyy.runner_id         |
  |                           |     -> rnr_zzz              |
  |                           |                             |
  |                           |-- run_yyy.status = STOPPING |
  |                           |-- session.status = stopping |
  |                           |-- stop_command_queue        |
  |                           |   .add_stop(rnr_zzz,       |
  |                           |     ses_xxx)                |
  |                           |                             |
  |<-- {ok: true,             |                             |
  |     session_id: ses_xxx,  |                             |
  |     status: stopping} ----|                             |
  |                           |                             |
  |                           |<-- GET /runner/runs --------|
  |                           |   (long-poll for rnr_zzz)   |
  |                           |                             |
  |                           |-- {"stop_sessions":         |
  |                           |     ["ses_xxx"]} ---------->|
  |                           |                             |
  |                           |   _handle_stop("ses_xxx")   |
  |                           |   registry.get_session_process(ses_xxx)
  |                           |     -> entry{process, run_id: run_yyy}
  |                           |   send_shutdown (if persistent)
  |                           |   process.terminate()       |
  |                           |   registry.remove_run(run_yyy)
  |                           |   registry.remove_session_process(ses_xxx)
  |                           |                             |
  |                           |<-- POST /runner/runs/       |
  |                           |     run_yyy/stopped --------|
  |                           |                             |
  |                           |-- run_yyy.status = STOPPED  |
  |                           |-- session.status = stopped  |
  |                           |-- broadcast SSE             |
  |                           |-- if async_callback:        |
  |                           |     notify parent           |
```

---

## 5. Implementation Steps

| # | Step | Component | Depends on | Parallelizable |
|---|------|-----------|------------|----------------|
| 1 | Registry rekey (task #136) | Runner | -- | Yes (independent) |
| 2 | Stop command queue: change comment | Coordinator | -- | Yes |
| 3 | `_stop_run()`: pass `session_id` to queue | Coordinator | Step 2 | Yes |
| 4 | `stop_run()` endpoint: delegate to `stop_session()` | Coordinator | Step 3 | Yes |
| 5 | Poll response: `stop_sessions` field name | Coordinator | Step 3 | Yes |
| 6 | `PollResult` + `poll_run()`: parse `stop_sessions` | Runner | Step 5 | No (must match coordinator) |
| 7 | `_handle_stop()`: take `session_id`, use registry | Runner | Steps 1, 6 | No |
| 8 | Poll loop: iterate `stop_sessions` | Runner | Step 6 | Yes (with step 7) |

**Critical path**: Steps 1 -> 7 (registry must exist before stop handler can use it).

**Coordinator steps** (2-5) can all be done in one commit.
**Runner steps** (6-8) depend on coordinator step 5 and registry step 1.

Steps 2-5 are coordinator-only; steps 6-8 are runner-only. They can be developed
in parallel but must be deployed together (monorepo, single deployment).

---

## 6. Risk Assessment

### Breaking Changes

| Change | Scope | Mitigation |
|--------|-------|------------|
| Poll field `stop_runs` -> `stop_sessions` | Coordinator <-> Runner protocol | Monorepo: deployed atomically. No external consumers. |
| `_handle_stop()` signature | Runner internal | Same file, same PR. |
| `PollResult.stop_runs` -> `stop_sessions` | Runner internal | Same file, same PR. |

**No external API changes.** The `POST /sessions/{session_id}/stop` and
`POST /runs/{run_id}/stop` endpoints keep the same URLs and response shapes.

### Edge Cases

| Scenario | Current behavior | New behavior | Notes |
|----------|-----------------|--------------|-------|
| Stop arrives after process already exited | `registry.get_run(run_id)` returns None, stop ignored | `registry.get_session_process(ses_id)` returns None, stop ignored | Same outcome, different lookup |
| Stop for non-existent session | `stop_session()` returns 404 | Unchanged | Coordinator checks session existence first |
| Stop while session is idle between turns | Not possible today (single-turn) | `entry.run_id` is None; process terminated, no run to report | New case for multi-turn; session cleaned up silently |
| Stop for PENDING run (not yet claimed) | Run marked STOPPED directly, no runner signal | Unchanged | Coordinator handles this before reaching the queue |
| Two rapid stops for same session | Second `add_stop()` is a set-add (idempotent) | Unchanged | `set[session_id]` deduplicates |
| Stop during `turn_complete` processing | Possible race: stdout reader reports completed, stop arrives | Runner uses dedup set (`_reported_runs`); stop finds no entry in registry, ignored | Already handled by Phase 2 supervisor design |

### Rollback Plan

If this change causes issues after deployment:
1. Revert the single commit that renames the protocol field
2. Both coordinator and runner revert atomically (monorepo)
3. No data migration needed (stop commands are transient, not persisted)

---

## References

| Document | Relevance |
|----------|-----------|
| `PHASE2-RUNNER-ARCHITECTURE.md` | Registry dual-index design, supervisor stdout readers |
| `NDJSON-PROTOCOL-REFERENCE.md` | `{"type": "shutdown"}` message spec |
| `MULTI-TURN-DESIGN.md` | Original multi-turn architecture |
| ADR-010 | Session ID semantics (coordinator-generated) |
| ADR-011 | Run demands and affinity routing |
