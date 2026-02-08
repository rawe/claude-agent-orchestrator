# Session Orphan Prevention

Design for preventing and cleaning up orphaned sessions — sessions stuck in non-terminal states (`running`, `idle`, `stopping`) with no live runner to service them.

---

## 1. Problem Statement

When a runner crashes, shuts down ungracefully, or loses connectivity, its sessions remain in non-terminal states in the coordinator database with no process to advance or terminate them. These orphaned sessions consume resources, confuse users (sessions appear active but are unresponsive), and block new runs on the same agent profile. The system currently has no mechanism to detect or recover from this state.

---

## 2. Orphan Scenarios

| # | Scenario | Root Cause | Current Behavior | Impact |
|---|----------|-----------|-----------------|--------|
| 1 | Runner crash (SIGKILL/OOM) | Runner process killed without cleanup | Executor processes and idle sessions left behind | Sessions stuck non-terminal, leaked processes |
| 2 | Executor process hangs | Process stops producing output, doesn't exit | Run appears stuck forever | Session stuck in `running`, user must manually intervene |
| 3 | Coordinator restart | In-memory runner registry lost | DB sessions reference runners that no longer exist | All sessions from all runners appear orphaned |
| 4 | Network partition (runner side) | Runner can't reach coordinator, self-deregisters after retries | Runner deregisters but executor processes may linger | Leaked processes on runner host |
| 5 | Idle session accumulation | Persistent sessions stay alive indefinitely between turns | No timeout on idle sessions | Unbounded resource consumption over time |
| 6 | Stuck "stopping" state | Stop command sent but process doesn't terminate | Session stays in `stopping` forever | Session permanently stuck, blocks cleanup |
| 7 | Graceful shutdown (Ctrl+C) | `Runner.stop()` deregisters but never terminates executor processes | Processes survive runner shutdown | Leaked processes, sessions stuck non-terminal |
| 8 | External deregistration | Dashboard triggers runner deregistration | Same process leak as #7; self-deregistration endpoint skips `fail_runs_on_runner_disconnect()` | Leaked processes, runs not marked failed |

---

## 3. Proposed Mechanisms

| # | Mechanism | Description | Addresses | Complexity | Reliability |
|---|-----------|-------------|-----------|------------|-------------|
| 1 | Graceful Shutdown Cascade | Runner SIGTERM/SIGINT handler terminates all executor processes before deregistering | #4, #7, #8 | Low | HIGH |
| 2 | Self-Deregistration Run Cleanup | Coordinator self-deregistration endpoint calls `fail_runs_on_runner_disconnect()` | #7, #8 | Low | HIGH |
| 3 | Idle Session TTL | Auto-stop sessions idle longer than configurable timeout (requires `last_activity_at` DB column) | #1, #3, #4, #5, #7, #8 | Medium | MEDIUM |
| 4 | Runner Startup Cleanup | Runner kills leftover executor processes from previous runs via PID files | #1, #4, #7 | Medium | LOW-MEDIUM |
| 5 | Coordinator Session Reaper | Background task marks sessions as failed/stopped when their runner is gone | #1, #3, #5, #6, #7, #8 | Medium | MEDIUM-HIGH |
| 6 | Process Watchdog | Runner monitors executor processes for output silence and kills after timeout | #2 | Medium | MEDIUM |
| 7 | Session Max Lifetime | Absolute cap on session existence (e.g. 24 hours) | #2, #5, #6 | Low-Medium | HIGH |

---

## 4. Detailed Analysis

### Mechanism 1: Graceful Shutdown Cascade

**How it works**: When `Runner.stop()` is called (via SIGTERM, SIGINT, or deregistration), iterate over all active sessions and terminate their executor processes before deregistering from the coordinator. Reuse the existing `_handle_stop()` logic in `poller.py:214-267`.

- **Pros**: Pure bug fix. Low complexity (~20 lines). No false-positive risk. Only mechanism covering graceful shutdown.
- **Cons**: Does not help with hard crashes (SIGKILL, OOM).
- **Implementation constraint**: Must kill processes BEFORE stopping the supervisor thread. Call `mark_stopping()` on all sessions first to prevent supervisor race conditions.

### Mechanism 2: Self-Deregistration Run Cleanup

**How it works**: The self-deregistration endpoint at `main.py:1891` currently calls `remove_runner()` but skips `fail_runs_on_runner_disconnect()`, which the lifecycle removal path at `main.py:167` does call. Add the missing call.

- **Pros**: Pure bug fix. ~15 lines. Mirrors existing logic. No false-positive risk.
- **Cons**: Only covers the deregistration code path.
- **Pre-existing gap**: Both self-deregistration AND lifecycle removal miss idle sessions with no active run — those sessions stay in `idle` with a dead runner. The fix should handle idle sessions too.

### Mechanism 3: Idle Session TTL

**How it works**: Add a `last_activity_at` timestamp column to the sessions table, updated on turn start, turn complete, and status changes. A coordinator background task stops sessions idle beyond a configurable threshold (recommended default: 2-4 hours).

- **Pros**: Addresses slow resource accumulation from long-idle sessions.
- **Cons**: Requires DB schema change. 6+ code paths must update the timestamp correctly. Resume race condition: reaper may stop a session between a user clicking "resume" and the runner receiving it — needs "stop-if-still-idle" semantics rather than unconditional stop.
- **False-positive risk**: Medium.

### Mechanism 4: Runner Startup Cleanup

**How it works**: Runner writes PID files for executor processes. On startup, reads old PID files and kills leftover processes.

- **Pros**: Cleans up leaked processes from hard crashes.
- **Cons**: PID recycling risk is severe — if the PID has been reused by an unrelated process, the runner kills the wrong process. Using process groups reduces but doesn't eliminate risk. Adds filesystem state management.
- **False-positive risk**: HIGH. Unbounded blast radius on wrong-PID kill.

### Mechanism 5: Coordinator Session Reaper

**How it works**: A periodic background task (every 60 seconds) queries for sessions in non-terminal states whose `runner_id` is not in the live runner registry. After a staleness threshold, transitions them to terminal states: `failed` (was `running`), `finished` (was `idle`), `stopped` (was `stopping`).

- **Pros**: Highest coverage (6 of 8 scenarios). Operates at coordinator level — does not depend on runner cooperation. Single most impactful safety net.
- **Cons**: Cannot clean up executor processes on remote runners (coordinator-side only). Requires startup grace period.
- **Critical constraint**: After coordinator restart, ALL sessions look orphaned because the runner registry is in-memory. Must wait a grace period (e.g. 2 minutes) for runners to reconnect before reaping. Use a 15-minute stale threshold for `running`/`idle` sessions, 2-minute threshold for `stopping` sessions.

### Mechanism 6: Process Watchdog

**How it works**: Runner monitors executor stdout for output. If no output for a configurable duration, kills the process.

- **Pros**: Only mechanism addressing scenario #2 (executor hangs).
- **Cons**: Claude Code legitimately goes silent for 10+ minutes during complex operations. Setting a timeout that avoids false positives while catching real hangs is difficult. Rare scenario in practice.
- **False-positive risk**: Medium.

### Mechanism 7: Session Max Lifetime

**How it works**: Absolute time cap on session existence (e.g. 24 hours). Sessions exceeding the cap are forcefully terminated. Can be implemented as an extension to Mechanism 5.

- **Pros**: Simple backstop. Guarantees no session lives forever.
- **Cons**: Blunt instrument. Largely redundant if Mechanisms 3 and 5 work correctly.

---

## 5. Discussion Summary

**Bug fixes vs. safety nets**: The architect proposed 7 mechanisms. The reliability engineer and simplicity advocate agreed that Mechanisms 1 and 2 are pure bug fixes (missing cleanup calls) and are non-controversial. The debate centered on which safety nets to add.

**Mechanism 4 (PID cleanup) rejected**: The reliability engineer flagged PID recycling as a critical risk with unbounded blast radius. The simplicity advocate agreed the risk/reward ratio is wrong given that Mechanisms 1+5 cover the same scenarios more safely.

**Mechanism 3 vs. 5**: The architect proposed both. The simplicity advocate argued that with Mechanism 5 (reaper) handling dead-runner sessions and Mechanism 1 handling shutdown, the remaining gap for Mechanism 3 is narrow: only live-runner idle sessions accumulating over time. That's resource management, not orphan prevention, and can wait until it's observed in practice. The reliability engineer endorsed this, noting the resume race condition adds real design complexity.

**Mechanism 6 (watchdog) deferred**: All three agreed that executor hangs (scenario #2) are rare and user-visible. The process watchdog's false-positive risk on legitimately silent Claude Code sessions makes it premature to implement.

---

## 6. Recommended Approach

### Phase 1 -- Implement Now

These three mechanisms together cover ~85% of orphan risk.

| # | Mechanism | Type | Est. Lines | Scenarios Covered |
|---|-----------|------|-----------|-------------------|
| 1 | Graceful Shutdown Cascade | Bug fix | ~20 | #4, #7, #8 |
| 2 | Self-Deregistration Run Cleanup | Bug fix | ~15 | #7, #8 |
| 5 | Coordinator Session Reaper | Safety net | ~60-80 | #1, #3, #5, #6, #7, #8 |

**Rationale**: Mechanisms 1 and 2 close gaps where existing cleanup logic is not being called — these are straightforward bugs. Mechanism 5 is the single highest-coverage safety net, catching any session left behind after a runner disappears. The only scenarios not covered are executor hangs (#2, rare, user-visible) and slow resource accumulation from long-lived idle sessions on live runners (#5 partial).

**Implementation constraints**:
- Mechanism 1: Reuse `_handle_stop()` from `poller.py:214-267`. Kill processes BEFORE stopping supervisor. Call `mark_stopping()` first.
- Mechanism 2: Mirror cleanup block from `runner_lifecycle_task` (`main.py:165-200`) into self-deregistration endpoint (`main.py:1891-1900`). Also handle idle sessions with no active run.
- Mechanism 5: Add 2-minute startup grace period after coordinator start. Check `runner_id` against live registry. Stale thresholds: 15 min for `running`/`idle`, 2 min for `stopping`. Terminal states: `failed` (was running), `finished` (was idle), `stopped` (was stopping).

**Reaper environment variables** (all optional, with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `REAPER_INTERVAL` | `60` | Seconds between reaper task runs |
| `REAPER_GRACE_PERIOD` | `120` | Seconds after coordinator startup before reaping begins (allows runners to reconnect) |
| `REAPER_STALE_RUNNING` | `900` | Seconds a `running` or `idle` session must be orphaned before reaping (15 min) |
| `REAPER_STALE_STOPPING` | `120` | Seconds a `stopping` session must be orphaned before reaping (2 min) |

For testing, use short values: `REAPER_INTERVAL=10 REAPER_GRACE_PERIOD=5 REAPER_STALE_RUNNING=30 REAPER_STALE_STOPPING=15`

### Phase 2 -- Implement If Needed

| # | Mechanism | Trigger |
|---|-----------|---------|
| 3 | Idle Session TTL | Idle session resource accumulation observed in production |
| 7 | Session Max Lifetime | Sessions escaping all other cleanup mechanisms |

---

## 7. Phase 2 Detail: Idle Session TTL

This mechanism is critical for long-running agent runners where idle sessions accumulate over hours/days. Documented here so implementation can begin without re-analysis.

### Problem

Persistent executor sessions stay alive indefinitely after their last turn completes. On a long-running runner, this means unbounded process and memory accumulation. Phase 1's reaper only catches sessions whose runner has disappeared — it does NOT touch idle sessions on live, healthy runners.

### Design

**Coordinator-side TTL enforcement** (not runner-side) — the coordinator is the single source of truth for session state and already runs the reaper background task.

#### DB Schema Change

Add `last_activity_at` column to the sessions table:

```sql
ALTER TABLE sessions ADD COLUMN last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

#### Activity Timestamp Updates

Update `last_activity_at` at these points:
1. **Session bind** (`/sessions/{id}/bind`) — executor binds to session
2. **Run started** (`/runner/runs/{id}/started`) — turn begins
3. **Run completed** (`/runner/runs/{id}/completed`) — turn ends
4. **Event posted** (`/sessions/{id}/events`) — any event activity
5. **Resume dispatched** (run queue dispatches resume) — new turn queued

#### TTL Reaper (extend Mechanism 5)

Add to the existing coordinator reaper task:

```
Every 60 seconds:
  SELECT sessions WHERE status = 'idle'
    AND last_activity_at < NOW() - IDLE_TTL
    AND runner_id IN (live_runners)   -- only reap on live runners

  For each:
    Issue stop command (graceful shutdown via NDJSON)
    Log: "Idle TTL expired for session {id} (idle since {last_activity_at})"
```

#### Configuration

```
IDLE_SESSION_TTL=7200   # seconds, default 2 hours
```

Configurable via environment variable. Reasonable range: 30 min to 24 hours.

#### Resume Race Condition Mitigation

The risk: user clicks "resume" at the same moment the reaper issues a stop.

**Solution**: Stop-if-still-idle semantics. The reaper does NOT send a hard stop. Instead:
1. Reaper checks `status = 'idle'` AND `last_activity_at` is stale
2. Reaper issues a stop command
3. If a resume arrives between the check and the stop reaching the runner, the session will be in `running` state — the runner's poller sees the stop command but the session is mid-turn, so it applies normal running-session stop logic (SIGTERM)
4. This is acceptable: the session was about to be reaped anyway, and the user can retry

Alternatively, the reaper can set a `ttl_expired` flag and let the runner check it before accepting a resume — but this adds complexity for a narrow race window. Start simple.

#### Dashboard Integration

- Add a warning indicator on idle sessions approaching TTL (e.g., > 75% of TTL elapsed)
- Show `last_activity_at` in session details
- Allow manual TTL reset ("keep alive") button if needed later

### Estimated Complexity

- DB migration: ~5 lines
- Timestamp update points: ~20 lines across 5 endpoints
- Reaper extension: ~30 lines
- Configuration: ~5 lines
- **Total: ~60 lines**

---

### Skip

| # | Mechanism | Reason |
|---|-----------|--------|
| 4 | Runner Startup Cleanup | PID recycling risk too high, redundant with #1 + #5 |
| 6 | Process Watchdog | Rare scenario, high false-positive risk, manual stop available |
