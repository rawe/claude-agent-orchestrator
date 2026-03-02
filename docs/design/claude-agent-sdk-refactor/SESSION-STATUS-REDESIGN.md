# Session Status Redesign for Multi-Turn Architecture

## Status: Proposal (Phase 2)

## 1. Problem Statement

The current session status model was designed for one-shot executors where "process exit = run done = session done." Multi-turn breaks this assumption: a session's process stays alive across multiple turns, and the session is _not_ done when a single turn completes.

Two new states are needed:
1. **Between turns**: The executor process is alive and idle, waiting for the next turn. The session is resumable.
2. **Session truly done**: All turns are complete, the process has exited cleanly, and no more turns are expected.

The current "finished" status conflates these two states: when the supervisor sees process exit (one-shot) or when a run completes (multi-turn turn), both result in "finished." But for multi-turn, a completed turn should leave the session in an "idle" state, not "finished."

---

## 2. Current Session Statuses

### Where Defined

Session status is a **free-form string** in the `sessions.status` column (SQLite TEXT). There is no enum or constraint in the database or coordinator models. Statuses are set by:

| Status | Set By | When | Where |
|--------|--------|------|-------|
| `pending` | `create_session()` | Session created, before executor binds | `database.py:326` |
| `running` | `bind_session_executor()` | Executor binds (first turn starts) | `database.py:394` |
| `running` | `insert_session()` | Legacy path (upsert) | `database.py:141` |
| `finished` | `report_run_completed()` | Runner reports run completed (process exit 0) | `main.py:1602` |
| `failed` | `report_run_failed()` (session not updated!) | Runner reports failure | `main.py:1674` (only updates **run** status, not session) |
| `stopping` | `_stop_run()` | Stop command issued | `main.py:480` |
| `stopped` | `report_run_stopped()` | Runner confirms stop | `main.py:1739` |
| `stopped` | `stop_session()` fallback | No active run, session marked stopped | `main.py:528,540` |

### Current State Machine

```
                        ┌────────────┐
                        │  pending   │  (session created, awaiting executor)
                        └─────┬──────┘
                              │ bind_session_executor()
                              v
                        ┌────────────┐
              ┌─────────│  running   │──────────┐
              │         └─────┬──────┘          │
              │               │                 │
              │ stop_session() │                 │ report_run_failed()
              │               │                 │ (NOTE: session status
              v               │                 │  not actually updated!)
        ┌────────────┐        │                 │
        │  stopping  │        │                 │
        └─────┬──────┘        │                 │
              │               │                 │
              │ report_stopped│ report_completed│
              v               v                 v
        ┌────────────┐  ┌────────────┐    ┌──────────┐
        │  stopped   │  │  finished  │    │ (running) │ ← bug: stays running on failure
        └────────────┘  └────────────┘    └──────────┘
```

### Observations

1. **`finished` is ambiguous**: Used for both "turn done" and "session done" — but in one-shot mode these are the same thing.
2. **`failed` is never set on the session**: `report_run_failed()` updates the _run_ status to FAILED but does **not** call `update_session_status_and_broadcast()`. The session stays in `running` forever. This is a bug.
3. **No `idle` state**: There is no way to represent "process alive, waiting for next turn."
4. **Callback processor depends on `finished`**: `callback_processor.on_child_completed()` checks `parent_status == "finished"` to decide if the parent is idle and can receive a callback (line 107 of `callback_processor.py`). This means "finished" currently means "idle and resumable."

---

## 3. New Session Status Model

### Design Principle

Session statuses should describe the **session's state from the outside** (coordinator/client perspective), not the internal executor process state. The key question a client asks is: "Can I send another turn to this session?"

### Status Definitions

| Status | Meaning | Process Alive? | Accepts New Turns? | Terminal? |
|--------|---------|---------------|-------------------|-----------|
| `pending` | Session created, executor not yet bound | No | No | No |
| `running` | A turn is actively executing | Yes | No (busy) | No |
| `idle` | **NEW.** Turn completed, process alive, waiting for next turn | Yes | **Yes** | No |
| `stopping` | Stop command issued, awaiting confirmation | Yes | No | No |
| `finished` | Session completed naturally. No more turns expected. | No | No | **Yes** |
| `stopped` | Session forcefully terminated by stop command | No | No | **Yes** |
| `failed` | Session died due to error (crash, non-zero exit) | No | No | **Yes** |

### Key Semantic Changes

| Status | Old Meaning | New Meaning |
|--------|-------------|-------------|
| `finished` | Run completed (overloaded: both "idle" and "done") | Session is **permanently** done. Process has exited. |
| `idle` | Did not exist | Process is alive, ready for the next turn |
| `failed` | Only on run, never on session | Set on **both** run and session when process crashes |

### State Machine

```
                        ┌────────────┐
                        │  pending   │
                        └─────┬──────┘
                              │ executor binds
                              v
                        ┌────────────┐
              ┌─────────│  running   │◄──────────┐
              │         └──┬──────┬──┘           │
              │            │      │              │ resume_session turn dispatched
              │            │      │              │
              │ stop       │      │         ┌────┴─────┐
              │ issued     │      │         │   idle   │ (persistent only)
              │            │      │         └────┬─────┘
              v            │      │              │
        ┌──────────┐       │      │              │ stop issued
        │ stopping │       │      │              │ (or idle timeout/shutdown)
        └────┬─────┘       │      │              v
             │             │      │       ┌──────────┐
             │ confirmed   │      │       │ stopping │ (if from idle)
             v             │      │       └────┬─────┘
        ┌──────────┐       │      │            │
        │ stopped  │◄──────┘      │            │
        └──────────┘  crash while │            │
                      stopping    │            │
                                  │            │
             turn_complete────────┤            │
             (persistent)         │            │
                    │             │            │
                    v             v            v
              ┌──────────┐  ┌──────────┐ ┌──────────┐
              │   idle   │  │ finished │ │ stopped  │
              └──────────┘  └──────────┘ └──────────┘
                                  ▲
                                  │
                  process_exit────┘ (from idle: clean shutdown/timeout)
                  (one-shot: exit 0)
                  (persistent: shutdown then exit 0)
```

### Valid Transitions

| From | To | Trigger | Who |
|------|----|---------|-----|
| `pending` | `running` | `bind_session_executor()` | Coordinator (on executor bind) |
| `running` | `idle` | `turn_complete` NDJSON (persistent executor) | Runner supervisor (stdout reader) |
| `running` | `finished` | Process exit with code 0 (one-shot executor) | Runner supervisor (process poll) |
| `running` | `failed` | Process exit with non-zero code | Runner supervisor (process poll) |
| `running` | `stopping` | Stop command issued | Coordinator (on stop request) |
| `running` | `stopped` | Crash during stopping | Runner supervisor |
| `idle` | `running` | Resume turn dispatched to executor | Runner (poller routes resume) |
| `idle` | `finished` | Clean shutdown (idle timeout, explicit shutdown) | Runner supervisor (process exit after shutdown) |
| `idle` | `stopping` | Stop command issued while idle | Coordinator (on stop request) |
| `idle` | `failed` | Process crash while idle | Runner supervisor (process poll) |
| `stopping` | `stopped` | Runner confirms stop | Runner (report_stopped) |
| `stopping` | `stopped` | Process exit while stopping | Runner supervisor |

### Invalid/Impossible Transitions

| From | To | Why |
|------|----|-----|
| `pending` | `idle` | Cannot be idle without ever running |
| `finished` | any | Terminal state |
| `stopped` | any | Terminal state |
| `failed` | any | Terminal state |
| `idle` | `idle` | No-op (already idle) |

---

## 4. Lifecycle Mode Differences

| Behavior | One-Shot (`lifecycle: "one_shot"`) | Persistent (`lifecycle: "persistent"`) |
|----------|-----------------------------------|----------------------------------------|
| Turn completion | Process exit (code 0) | `turn_complete` on stdout |
| Session status after turn | `finished` (terminal) | `idle` (non-terminal) |
| Resume possible? | No (process exited) | Yes (process alive, write to stdin) |
| Process exit meaning | Normal completion | Crash (if active run) or clean shutdown (if idle) |
| Uses `idle` status? | **No** | **Yes** |
| Uses `finished` status? | Yes (= session done) | Yes (after clean shutdown from idle) |

---

## 5. Impact: Coordinator

### 5.1 `report_run_completed()` (main.py:1573)

**Current**: Always sets session status to `finished`.

**New**: Must distinguish by lifecycle mode.

```
if lifecycle == "persistent":
    session.status = "idle"        # turn done, process alive
else:
    session.status = "finished"    # one-shot: session done
```

**How does the coordinator know the lifecycle mode?** Two options:

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| A. Runner tells coordinator | New field in `POST /runner/runs/{run_id}/completed` body: `{"session_idle": true}` | Coordinator stays lifecycle-agnostic | New protocol field |
| B. Coordinator infers from executor_type | Look up runner → profile → lifecycle | No protocol change | Coordinator couples to executor details |
| **C. New endpoint** | Runner calls `report_turn_completed()` (distinct from `report_run_completed()`) | Clear semantic separation | New endpoint |

**Recommendation: Option A.** The runner already knows the lifecycle mode. Adding a boolean `session_idle: true` to the completion report is the simplest, most explicit approach. The coordinator does not need to understand lifecycle modes — it just trusts the runner's signal.

Alternative formulation: the runner explicitly reports the desired session status transition:

```json
POST /runner/runs/{run_id}/completed
{
  "runner_id": "lnch_xxx",
  "session_status": "idle"     // or "finished" for one-shot
}
```

This is unambiguous and future-proof. The coordinator applies whatever session status the runner specifies (within allowed transitions).

### 5.2 Callback Processor (callback_processor.py:107)

**Current**: Checks `parent_status == "finished"` to determine if parent is idle.

**New**: Must check for both `"finished"` and `"idle"`:

```python
# Current (line 107):
if parent_status == "finished":

# New:
if parent_status in ("finished", "idle"):
```

But semantically, only `idle` means "alive and can receive a resume." `finished` means "session done." If a child completes and the parent is `finished`, should a callback still be sent? In the current system, yes — because `finished` + callback creates a `resume_session` run, which re-starts the parent.

For multi-turn:
- **Parent `idle`**: Create resume run immediately (parent process is alive and waiting)
- **Parent `finished`**: This means the parent has permanently ended. A callback creates a resume run, but if the parent's executor is persistent and exited cleanly, the resume will fail (no live process). This is correct behavior — `finished` means done.

**Decision**: Change callback check to `parent_status == "idle"`. If a parent is `finished`, its children's callbacks should still be queued (existing behavior) but will only be flushed if the parent transitions back to `idle` (which currently happens via resume). This requires no callback processor changes beyond the status string comparison.

Actually, let's reconsider. In the current one-shot model, "finished" means "turn done, idle, can be resumed." The callback processor was built for this. For one-shot executors, `finished` is still the correct idle state (there is no live process — resume spawns a new one). For persistent executors, `idle` is the correct idle state.

**Corrected decision**: Change the callback processor idle check to:

```python
if parent_status in ("finished", "idle"):
```

This handles both one-shot parents (status = `finished` after their run) and persistent parents (status = `idle` between turns).

### 5.3 `GET /sessions/{session_id}/result` (main.py:391)

**Current**: Returns 400 if `session.status != "finished"`.

**New**: Allow result retrieval for `idle` sessions too (result from the last completed turn):

```python
if session["status"] not in ("finished", "idle"):
    raise HTTPException(status_code=400, detail="Session not finished or idle")
```

### 5.4 Session Status Bug Fix: `report_run_failed()`

**Current**: `report_run_failed()` (main.py:1667) updates run status to FAILED but does **not** update the session status. Session stays `running` forever.

**Fix**: Add session status update:

```python
# After updating run status to FAILED:
if run.session_id:
    await update_session_status_and_broadcast(run.session_id, "failed")
```

### 5.5 `stop_session()` from `idle` state

**Current**: `stop_session()` only handles `running` and `stopping` states.

**New**: Must also handle `idle` state — send stop command to terminate the idle process:

```python
if session_status == "idle":
    # Session is idle — stop command kills the process
    # Same flow as stopping a running session
    await update_session_status_and_broadcast(session_id, "stopping")
    stop_command_queue.add_stop(runner_id, session_id)
```

### 5.6 MCP Tools: `get_agent_session_result` (tools.py:426)

**Current**: Gates result retrieval on `status != "finished"`.

**New**: Allow result retrieval for `idle` sessions:

```python
if status not in ("finished", "idle"):
    # No result available yet
```

### 5.7 `report_run_started()` — `idle` to `running` transition

**Current**: `report_run_started()` (main.py:1536) only updates run status to RUNNING. Does not touch session status.

**New**: Also transition session from `idle` to `running` when a resume turn starts:

```python
if run.session_id:
    session = get_session_by_id(run.session_id)
    if session and session["status"] == "idle":
        await update_session_status_and_broadcast(run.session_id, "running")
```

### 5.8 Summary of Coordinator Changes

| Location | Change | Impact |
|----------|--------|--------|
| `report_run_completed()` | Set session to `idle` or `finished` based on runner signal | Medium |
| `report_run_started()` | Transition session `idle` -> `running` on resume | Small |
| `callback_processor.on_child_completed()` | Check `status in ("finished", "idle")` | Trivial |
| `report_run_failed()` | Set session status to `failed` (bug fix) | Small |
| `GET /sessions/{session_id}/result` | Allow `idle` status | Trivial |
| MCP tools `get_agent_session_result` | Allow `idle` status | Trivial |
| `stop_session()` | Handle `idle` state (same as `running`) | Small |
| `update_session_status_and_broadcast()` | No structural change (already generic) | None |
| Database schema | No change (status is already TEXT) | None |

---

## 6. Impact: Runner

### 6.1 Supervisor: Two Completion Signals

| Executor lifecycle | Signal | Supervisor action | Reports to coordinator |
|-------------------|--------|-------------------|----------------------|
| `one_shot` | `process.poll() == 0` | `report_completed(session_status="finished")` | Run COMPLETED, session `finished` |
| `one_shot` | `process.poll() != 0` | `report_failed(...)` | Run FAILED, session `failed` |
| `persistent` | `turn_complete` on stdout | `report_completed(session_status="idle")` | Run COMPLETED, session `idle` |
| `persistent` | `process.poll() != 0` (active run) | `report_failed(...)` | Run FAILED, session `failed` |
| `persistent` | `process.poll() == 0` (idle, shutdown) | Session cleanup only | Session `finished` |
| `persistent` | `process.poll() != 0` (idle, crash) | Session cleanup only | Session `failed` |

### 6.2 Idle Process Exit (New Case)

When a persistent process exits while idle (no active run), the supervisor must update the session status:

- **Exit code 0** (clean shutdown, idle timeout): Report session `finished`
- **Non-zero exit** (crash): Report session `failed`

This requires a new coordinator endpoint or extending an existing one to allow session status updates without a run_id:

**Option**: `POST /runner/sessions/{session_id}/status` — runner reports session-level status changes.

```json
POST /runner/sessions/{session_id}/status
{
  "runner_id": "lnch_xxx",
  "status": "finished"   // or "failed"
}
```

This endpoint is only used for the "idle process exit" case where there is no active run to report against.

### 6.3 Poller: Resume Sets `running`

When the poller routes a resume turn to an existing process, it reports `started` to the coordinator. The coordinator's `report_run_started()` should transition the session from `idle` to `running`.

**Current `report_run_started()`**: Only updates run status to RUNNING, does not touch session status.

**New**: Also update session status:

```python
# In report_run_started():
if run.session_id:
    session = get_session_by_id(run.session_id)
    if session and session["status"] == "idle":
        await update_session_status_and_broadcast(run.session_id, "running")
```

### 6.4 Summary of Runner Changes

| Location | Change | Impact |
|----------|--------|--------|
| Supervisor: `_report_turn_complete()` | Include `session_status: "idle"` in completion report | Small |
| Supervisor: `_handle_completion()` (one-shot) | Include `session_status: "finished"` in completion report | Small |
| Supervisor: `_handle_persistent_exit()` | Report session `finished` or `failed` for idle process exit | Medium |
| Poller: `_handle_run()` (start) | No change (session already goes `pending` -> `running` on bind) | None |

---

## 7. Impact: Executor

**No changes.** The executor already emits `turn_complete` on stdout and exits on shutdown. It is unaware of session statuses — that is entirely a coordinator/runner concern.

---

## 8. Impact: Dashboard

**Requires separate implementation task.** Known locations that need changes:

| File | What | Change Needed |
|------|------|---------------|
| `apps/dashboard/src/types/session.ts:7` | `SessionStatus` TypeScript type | Add `"idle"` and `"failed"` to union |
| `apps/dashboard/src/components/features/sessions/SessionCard.tsx:20-34` | `getStatusAccentColor()` | Add `idle` (suggest: blue) and `failed` (suggest: red) cases |
| `apps/dashboard/src/components/features/sessions/SessionCard.tsx:123` | Stop button visibility | Show for both `running` and `idle` |
| `Badge.tsx:64-72` | `StatusBadge` config | Add `idle` and `failed` badge rendering |
| `apps/dashboard/src/contexts/ChatContext.tsx:417` | User input enable check | Check for `idle` in addition to `finished` |
| `apps/chat-ui/src/types/index.ts` | Chat UI types | Add `idle` and `failed` |

**Not designed here.** Dashboard changes should be a separate task.

---

## 9. Migration

### Database

No schema migration needed. The `sessions.status` column is `TEXT` — it accepts any string value. New statuses (`idle`, `failed`) can be written immediately.

### Backward Compatibility

| Concern | Assessment |
|---------|------------|
| Existing one-shot sessions | Unaffected. They never enter `idle`. Their lifecycle remains: `pending` -> `running` -> `finished`/`stopped`. |
| Existing `finished` sessions in DB | Remain `finished`. This is correct — they are truly done. |
| Dashboard | Must be updated to display `idle` and `failed`. Until updated, `idle` sessions will show as "unknown" (default case in switch). |
| Chat UI | Uses session status for polling. Must recognize `idle` as "can resume." |
| Coordinator API consumers | `GET /sessions/{id}/status` may now return `idle` or `failed`. Clients must handle. |

### Rollout Order

1. **Coordinator** — accept new statuses, update transition logic
2. **Runner** — report new statuses
3. **Dashboard** — display new statuses

Steps 1 and 2 can be deployed together (monorepo). Step 3 can follow.

---

## 10. Complete Status Reference

| Status | Set By | Trigger | Terminal | Process | Resumable |
|--------|--------|---------|----------|---------|-----------|
| `pending` | Coordinator | `create_session()` | No | Not started | No |
| `running` | Coordinator | Executor bind / resume dispatched | No | Alive, executing | No (busy) |
| `idle` | Runner (via coordinator) | `turn_complete` (persistent) | No | Alive, waiting | **Yes** |
| `stopping` | Coordinator | Stop command issued | No | Alive, terminating | No |
| `finished` | Runner (via coordinator) | Process exit 0 (one-shot) or clean shutdown (persistent from idle) | **Yes** | Exited | No |
| `stopped` | Runner (via coordinator) | Stop confirmed | **Yes** | Exited | No |
| `failed` | Runner (via coordinator) | Process crash / non-zero exit | **Yes** | Exited | No |

---

## References

| Document | Relevance |
|----------|-----------|
| `PHASE2-RUNNER-ARCHITECTURE.md` | Supervisor stdout readers, lifecycle modes |
| `STOP-COMMAND-REDESIGN.md` | Stop flows session_id, stopping/stopped transitions |
| `MULTI-TURN-EXECUTOR-ARCHITECTURE.md` | Executor process states, turn_complete protocol |
| `NDJSON-PROTOCOL-REFERENCE.md` | turn_complete message format |
| `callback_processor.py` | Parent idle check (currently `"finished"`) |
| `main.py:1573-1664` | `report_run_completed()` — sets session to `finished` |
| `main.py:1667-1698` | `report_run_failed()` — bug: does not update session status |
