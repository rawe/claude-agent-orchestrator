# Registry Redesign: Session-Primary Process Tracking

## Status: Proposal (Phase 2)

## 1. Problem

The current `RunningRunsRegistry` is keyed by `run_id`:

```python
_runs: dict[str, RunningRun]  # run_id -> RunningRun{process, started_at, run_id, session_id}
```

This breaks in multi-turn because:

| Problem | Why it breaks |
|---------|---------------|
| Stop arrives as `session_id` (per `STOP-COMMAND-REDESIGN.md`) | No way to look up process by session_id without scanning |
| Resume routing needs session_id lookup | Poller must find existing process for `resume_session` runs |
| Stdout reader needs session_id -> current_run_id | `turn_complete` has no run_id (per `NDJSON-PROTOCOL-SIMPLIFICATION.md`) |
| Between turns, no active run_id | Process alive but no run — impossible to represent when keyed by run_id |

---

## 2. New Design

### Data Model

```python
@dataclass
class SessionProcess:
    """A live executor process serving a session."""
    process: subprocess.Popen
    session_id: str
    started_at: datetime
    persistent: bool = False           # one_shot vs persistent lifecycle
    current_run_id: Optional[str] = None  # active run (None = idle between turns)
```

### Index Structure

```python
class ProcessRegistry:
    _sessions: dict[str, SessionProcess]  # session_id -> SessionProcess (PRIMARY)
    _run_index: dict[str, str]            # run_id -> session_id (SECONDARY)
    _lock: threading.Lock
```

**Primary (`_sessions`)**: Every process is tracked by its session_id. This is the natural key because:
- One process per session (both one-shot and persistent)
- Stop commands arrive as session_id
- Resume routing looks up by session_id
- Stdout reader knows session_id (passed at thread creation)

**Secondary (`_run_index`)**: Lightweight reverse map for the supervisor's `_check_runs()` which iterates all processes and needs to report completion using `run_id`. Avoids scanning `_sessions` to find which session owns a run.

---

## 3. Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `register_session` | `(session_id, process, run_id, persistent=False)` | Register new session + its first run |
| `get_session` | `(session_id) -> SessionProcess \| None` | Look up by session_id |
| `get_session_by_run` | `(run_id) -> SessionProcess \| None` | Look up via run index |
| `swap_run` | `(session_id, new_run_id) -> str \| None` | Atomic: update current_run_id, update run index. Returns old run_id. |
| `clear_run` | `(session_id) -> str \| None` | Turn complete: set current_run_id=None, remove from run index. Returns cleared run_id. |
| `remove_session` | `(session_id) -> SessionProcess \| None` | Full cleanup: remove from both indexes |
| `get_all_sessions` | `() -> dict[str, SessionProcess]` | Snapshot copy for supervisor polling |
| `count` | `() -> int` | Active session count |

### Method Details

**`register_session(session_id, process, run_id, persistent=False)`**
- Creates `SessionProcess` with `current_run_id=run_id`
- Adds to `_sessions[session_id]`
- Adds to `_run_index[run_id] = session_id`
- Single lock acquisition

**`swap_run(session_id, new_run_id)`**
- Must be atomic (single lock):
  1. Get entry from `_sessions[session_id]`
  2. Remove `_run_index[old_run_id]`
  3. Set `entry.current_run_id = new_run_id`
  4. Add `_run_index[new_run_id] = session_id`
- Prevents window where neither old nor new run_id is indexed

**`clear_run(session_id)`**
- Used by stdout reader when `turn_complete` is received
- Sets `current_run_id = None` (process stays alive, session becomes idle)
- Removes old run_id from `_run_index`

**`remove_session(session_id)`**
- Used on process exit or stop
- Removes from `_sessions`
- If `current_run_id` is set, removes from `_run_index`
- Returns the removed entry (caller needs it for reporting)

---

## 4. Consumer Usage

### Poller: `_handle_run()` — Start

```python
process = self.executor.execute_run(run)
self.registry.register_session(
    run.session_id, process, run.run_id,
    persistent=self.executor.is_persistent)
self.api_client.report_started(self.runner_id, run.run_id)
```

### Poller: `_handle_run()` — Resume (persistent only)

```python
entry = self.registry.get_session(run.session_id)
if entry:
    self.registry.swap_run(run.session_id, run.run_id)
    self.executor.send_turn(entry.process, run)
    self.api_client.report_started(self.runner_id, run.run_id)
    return

# No live process — fail explicitly (no fallback)
self.api_client.report_failed(self.runner_id, run.run_id,
    f"No live executor process for session {run.session_id}")
```

### Poller: `_handle_stop()` — Session-keyed (per STOP-COMMAND-REDESIGN.md)

```python
def _handle_stop(self, session_id: str):
    entry = self.registry.get_session(session_id)
    if not entry:
        return  # already gone

    run_id = entry.current_run_id
    # ... terminate process (graceful shutdown for persistent, SIGTERM for one-shot)
    self.registry.remove_session(session_id)

    if run_id:
        self.api_client.report_stopped(self.runner_id, run_id, signal=signal_used)
```

### Supervisor: `_check_runs()` — Process exit detection

```python
sessions = self.registry.get_all_sessions()
for session_id, entry in sessions.items():
    return_code = entry.process.poll()
    if return_code is not None:
        if entry.persistent:
            self._handle_persistent_exit(session_id, entry, return_code)
        else:
            self._handle_oneshot_exit(session_id, entry, return_code)
```

**One-shot exit**: `entry.current_run_id` is always set. Report completed/failed. Remove session.

**Persistent exit**: Process crashed or shut down.
- If `current_run_id` is set: active run was in progress -> report failed
- If `current_run_id` is None: process was idle -> report session finished/failed (via new `POST /runner/sessions/{session_id}/status` endpoint, per `SESSION-STATUS-REDESIGN.md`)
- Either way: `remove_session(session_id)`

### Supervisor: Stdout reader (new, one thread per persistent process)

```python
def _stdout_reader_loop(self, session_id: str, process: subprocess.Popen):
    for line in iter(process.stdout.readline, ''):
        msg = json.loads(line.strip())
        if msg.get("type") == "turn_complete":
            self._report_turn_complete(session_id)

def _report_turn_complete(self, session_id: str):
    entry = self.registry.get_session(session_id)
    if not entry or not entry.current_run_id:
        return
    run_id = entry.current_run_id
    if run_id in self._reported_runs:
        return  # dedup
    self._reported_runs.add(run_id)
    self.registry.clear_run(session_id)  # run done, process stays
    self.api_client.report_completed(self.runner_id, run_id,
        session_status="idle")  # per SESSION-STATUS-REDESIGN.md
```

**Key**: The stdout reader knows `session_id` because it was passed when the thread was created. It reads `current_run_id` from the registry — no run_id needed from the NDJSON message.

---

## 5. One-Shot Compatibility

One-shot processes (procedural executor) work identically:

| Aspect | One-shot behavior |
|--------|-------------------|
| `register_session()` | `persistent=False` |
| `current_run_id` | Always set (never cleared) |
| `clear_run()` | Never called (no stdout reader) |
| Process exit | `_handle_oneshot_exit()` reads `current_run_id`, reports completed/failed |
| `remove_session()` | Cleans up everything |

No behavioral change for one-shot executors. Only the index structure differs.

---

## 6. Thread Safety

Three threads access the registry concurrently:

| Thread | Reads | Writes |
|--------|-------|--------|
| Poller | `get_session()` | `register_session()`, `swap_run()` |
| Supervisor poll loop | `get_all_sessions()` | `remove_session()` |
| Stdout reader (per process) | `get_session()` | `clear_run()` |

**Safety guarantees**:
- `get_all_sessions()` returns a **copy** — supervisor iterates safely while others modify
- Each method acquires `_lock` independently — all dict operations are atomic
- `swap_run()` is a single lock acquisition (remove old + set new + add new)
- `_reported_runs: set` in supervisor prevents double-reporting between stdout reader and poll loop

**Race: stdout reader `clear_run()` vs supervisor `remove_session()`**:
Order doesn't matter. If `clear_run()` runs first, the run is cleared and reported. Then `remove_session()` cleans up the session (no run to double-report). If `remove_session()` runs first, the session is gone. Then `clear_run()` returns None (session not found). The `_reported_runs` dedup set prevents either from reporting twice.

---

## 7. Migration

| Current method | New equivalent | Notes |
|---------------|---------------|-------|
| `add_run(run_id, session_id, process)` | `register_session(session_id, process, run_id)` | Args reordered, session_id is primary |
| `get_run(run_id)` | `get_session_by_run(run_id)` | Returns `SessionProcess` (different type) |
| `remove_run(run_id)` | `clear_run(session_id)` or `remove_session(session_id)` | Semantic split: clear run vs remove everything |
| `get_all_runs()` | `get_all_sessions()` | Keys change from run_id to session_id |
| `count()` | `count()` | Counts sessions, not runs |

All callers are in 3 files: `poller.py`, `supervisor.py`, and the new stdout reader code. No external consumers.

---

## References

| Document | Relevance |
|----------|-----------|
| `STOP-COMMAND-REDESIGN.md` | Stop uses session_id — registry must support session lookup |
| `NDJSON-PROTOCOL-SIMPLIFICATION.md` | No run_id in turn_complete — stdout reader uses registry for run_id |
| `SESSION-STATUS-REDESIGN.md` | `idle` status, `session_status` in completion report |
| `EXECUTOR-SESSION-ID-SCOPE.md` | Bind stays unchanged, executor_session_id stored but not used for resume |
| `PHASE2-RUNNER-ARCHITECTURE.md` | Original dual-index proposal (superseded by this document) |
