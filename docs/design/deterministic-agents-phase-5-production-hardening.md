# Phase 5: Production Hardening

**Status:** Implemented
**Depends on:** Phase 4 (Deterministic Executor)
**Design Reference:** [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Section 11

---

## Objective

Handle edge cases and failure scenarios for production reliability: runner disconnection, session orphaning, and blueprint name collisions.

**End state:** The system gracefully handles runner failures, cleans up orphaned sessions, and prevents blueprint naming conflicts.

---

## Key Components

### 1. Runner Disconnect Detection ✅

**Status:** Implemented

**File:** `servers/agent-coordinator/services/runner_registry.py`

Existing heartbeat mechanism (per ADR-006):
- Runner sends heartbeat every 30s
- Coordinator marks runner "stale" after 120s (configurable)
- Coordinator removes runner after 600s (configurable)

When runner is removed:
- Delete bound blueprints (in-memory agent list)
- Fail orphaned runs
- Trigger failure callbacks

### 2. Blueprint Cleanup on Disconnect ✅

**Status:** Implemented

**File:** `servers/agent-coordinator/services/runner_registry.py`

Blueprint cleanup handled by `_remove_runner_agents_unlocked()` called from `update_lifecycle()`.

On runner removal:
1. Remove runner from registry
2. Call `_remove_runner_agents_unlocked(runner_id)` - clears in-memory agent list

### 3. Session Orphan Handling ✅

**Status:** Implemented

**Files:**
- `servers/agent-coordinator/database.py` - `fail_runs_on_runner_disconnect()`
- `servers/agent-coordinator/main.py` - `runner_lifecycle_task()`

When runner is removed with active runs:
1. Query runs with `runner_id` and `status IN ('running', 'claimed')`
2. Mark each run as `status='failed'`
3. Set error: `"Runner disconnected during execution"`
4. Update session status to `'failed'`
5. Broadcast `RUN_FAILED` event via SSE
6. Trigger callbacks for `async_callback` mode runs

### 4. Callback on Orphan ✅

**Status:** Implemented

**Files:**
- `servers/agent-coordinator/main.py` - `runner_lifecycle_task()`
- `servers/agent-coordinator/services/callback_processor.py`

Orphaned sessions trigger failure callbacks:
- Uses `CALLBACK_FAILED_PROMPT_TEMPLATE`
- Parent agent receives failure notification
- Parent can decide whether to retry

**No automatic retry:** The framework does not auto-retry because:
- Task may have had side effects
- Idempotency is application-specific
- Orchestrator should decide retry strategy

### 5. Blueprint Name Collision Handling ✅

**Status:** Implemented (rejection approach)

**Files:**
- `servers/agent-coordinator/services/runner_registry.py` - `AgentNameCollisionError`, `store_runner_agents()`
- `servers/agent-coordinator/main.py` - Error handling in `register_runner()` endpoint

**Approach:** Reject registration on collision (first runner wins)

When a runner tries to register an agent name that's already registered by another runner:
1. Registration is rejected with HTTP 409 Conflict
2. Error includes: agent name, existing runner ID
3. The runner that registered first keeps the name

**Why rejection instead of @suffix:**
- External clients always get predictable behavior (no hidden renaming)
- No ambiguity in routing - each agent name maps to exactly one runner
- Runner and coordinator agree on the name
- Simpler implementation, no complex lookup logic
- Forces users to resolve naming conflicts upfront

**Error response:**
```json
{
  "error": "agent_name_collision",
  "message": "Agent 'web-crawler' is already registered by runner 'lnch_abc123'",
  "agent_name": "web-crawler",
  "existing_runner_id": "lnch_abc123"
}
```

**Note:** Re-registration of the same runner with the same agents is allowed (replaces existing agents).

### 6. Run Failure on Missing Blueprint ✅

**Status:** Implemented (via timeout mechanism)

**File:** `servers/agent-coordinator/services/run_queue.py`

If a run is created for a blueprint that becomes unavailable:
1. Run remains pending (no runner can claim)
2. After timeout: Mark run as failed via `run_timeout_task()` in main.py
3. Error: `"No matching runner available within timeout"`

Note: Fail-fast at run creation time is not implemented (would require checking blueprint existence).

---

## Heartbeat Timeline

```
t=0      Runner registers, blueprints stored
t=30s    Heartbeat received ✓
t=60s    Heartbeat received ✓
t=120s   No heartbeat → mark "stale" (warning)
...
t=600s   No heartbeat → runner removed
         → Delete blueprints
         → Fail running sessions
         → Trigger failure callbacks
```

---

## Files Modified

| File | Change |
|------|--------|
| `servers/agent-coordinator/database.py` | `fail_runs_on_runner_disconnect()` |
| `servers/agent-coordinator/services/runner_registry.py` | `AgentNameCollisionError`, collision check in `store_runner_agents()`, blueprint cleanup via `_remove_runner_agents_unlocked()` |
| `servers/agent-coordinator/main.py` | `runner_lifecycle_task()` handles orphan runs and callbacks, `register_runner()` handles agent name collisions |

---

## Acceptance Criteria

### Runner Disconnect

1. ✅ **Blueprints removed:**
   - Runner goes offline
   - Blueprints no longer appear in agent list
   - Runs for those blueprints timeout with "No matching runner available within timeout"

2. ✅ **Sessions failed:**
   - Running session on disconnected runner → status='failed'
   - Error message: "Runner disconnected during execution"

3. ✅ **Callbacks triggered:**
   - Parent agent receives failure callback for `async_callback` mode sessions
   - Callback includes error details

### Name Collisions

4. ✅ **First registration wins (rejection approach):**
   - First runner registers `web-crawler` → stored as `web-crawler`
   - Second runner registers `web-crawler` → HTTP 409 rejection with error details

5. ✅ **No ambiguity:**
   - Each agent name maps to exactly one runner
   - External clients always get predictable behavior

### Retry Behavior

6. ✅ **No auto-retry:**
   - Orphaned session stays failed
   - Parent orchestrator can manually retry if desired

---

## Testing Strategy

1. **Disconnect simulation:**
   - Start runner, create running session
   - Stop runner without graceful shutdown
   - Verify: Blueprints removed, session failed, callback triggered

2. **Heartbeat timeout:**
   - Start runner, stop heartbeats (mock)
   - Wait for timeout
   - Verify same cleanup as disconnect

3. **Name collision (rejection):**
   - Register runner A with `web-crawler` → Success
   - Register runner B with `web-crawler` → HTTP 409 rejection
   - Verify: Error includes agent name and existing runner ID
   - Verify: Runner A's `web-crawler` still works

4. **Orphan callback:**
   - Create async_callback session on runner
   - Disconnect runner
   - Verify: Parent receives failure callback

5. **Graceful shutdown:**
   - Runner sends unregister before stopping
   - Verify: Same cleanup, but immediate (no timeout wait)

---

## Orchestrator Retry Pattern

For orchestrators that want to retry on runner failure:

```python
# Parent AI agent callback handler
def handle_callback(result):
    if result.status == "failed" and "Runner disconnected" in result.error:
        if is_idempotent(result.agent_name):
            # Safe to retry
            return start_agent_session(
                agent_name=result.agent_name,
                parameters=result.original_parameters,
                mode="async_callback"
            )
        else:
            # Not safe to retry, escalate to user
            return notify_user(f"Task failed: {result.error}")
```

This is application logic, not framework behavior.

---

## References

- [ADR-006](../adr/ADR-006-runner-heartbeat.md) - Runner heartbeat mechanism
- [ADR-003](../adr/ADR-003-callback-based-async.md) - Callback-based async
- [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Section 11
- [runner_registry.py](../../servers/agent-coordinator/services/runner_registry.py) - Runner lifecycle
