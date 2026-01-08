# Phase 5: Production Hardening

**Status:** Implementation Ready
**Depends on:** Phase 4 (Deterministic Executor)
**Design Reference:** [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Section 11

---

## Objective

Handle edge cases and failure scenarios for production reliability: runner disconnection, session orphaning, and blueprint name collisions.

**End state:** The system gracefully handles runner failures, cleans up orphaned sessions, and prevents blueprint naming conflicts.

---

## Key Components

### 1. Runner Disconnect Detection

**File:** `servers/agent-coordinator/services/runner_registry.py`

Existing heartbeat mechanism (per ADR-006):
- Runner sends heartbeat every 30s
- Coordinator marks runner "stale" after 90s
- Coordinator marks runner "offline" after 180s

**Extend for blueprint cleanup:**
- When runner goes offline: Delete bound blueprints
- Emit event for blueprint removal (SSE broadcast)

### 2. Blueprint Cleanup on Disconnect

**File:** `servers/agent-coordinator/database.py`

Add cleanup function:
```python
def delete_runner_blueprints(runner_id: str) -> int:
    """Delete all blueprints bound to a runner. Returns count deleted."""
```

**File:** `servers/agent-coordinator/services/runner_registry.py`

On runner offline transition:
1. Mark runner offline
2. Call `delete_runner_blueprints(runner_id)`
3. Broadcast blueprint removal events

### 3. Session Orphan Handling

**File:** `servers/agent-coordinator/services/runner_registry.py`

When runner goes offline with running sessions:

1. Query sessions with `runner_id` and `status='running'`
2. Mark each session as `status='failed'`
3. Set error: `"Runner disconnected during execution"`
4. Trigger callbacks for `async_callback` mode sessions

**Failure event:**
```json
{
  "session_id": "ses_abc123",
  "status": "failed",
  "error": "Runner disconnected during execution",
  "result_text": null
}
```

### 4. Callback on Orphan

**File:** `servers/agent-coordinator/services/callback_processor.py`

Orphaned sessions trigger failure callbacks:
- Use `CALLBACK_FAILED_PROMPT_TEMPLATE` (lines 47-53)
- Parent agent receives failure notification
- Parent can decide whether to retry

**No automatic retry:** The framework does not auto-retry because:
- Task may have had side effects
- Idempotency is application-specific
- Orchestrator should decide retry strategy

### 5. Blueprint Name Collision Handling

**File:** `servers/agent-coordinator/main.py` or `database.py`

When multiple runners register blueprints with the same name:

| Registration Order | Stored Name |
|--------------------|-------------|
| First `web-crawler` | `web-crawler` |
| Second `web-crawler` (runner `lnch_abc123`) | `web-crawler@lnch_abc123` |

**Implementation:**
1. On blueprint insert, check if name exists
2. If exists and different runner: Append `@{runner_id}` suffix
3. Store both original name and stored name
4. Runner is unaware of suffix (uses original name internally)

**Lookup logic:**
- First try exact match
- Then try `{name}@{runner_id}` for the requesting runner
- Error if ambiguous (same name from multiple runners, no qualifier)

### 6. Run Failure on Missing Blueprint

**File:** `servers/agent-coordinator/services/run_queue.py`

If a run is created for a blueprint that becomes unavailable:
1. Run remains pending (no runner can claim)
2. After timeout: Mark run as failed
3. Error: `"No runner available for blueprint: {name}"`

Consider: Fail-fast if blueprint doesn't exist at run creation time.

---

## Heartbeat Timeline

```
t=0      Runner registers, blueprints stored
t=30s    Heartbeat received ✓
t=60s    Heartbeat received ✓
t=90s    No heartbeat → mark "stale" (warning)
t=120s   No heartbeat
t=150s   No heartbeat
t=180s   No heartbeat → mark "offline"
         → Delete blueprints
         → Fail running sessions
         → Trigger failure callbacks
```

---

## Files to Modify

| File | Change |
|------|--------|
| `servers/agent-coordinator/database.py` | `delete_runner_blueprints()`, orphan session query |
| `servers/agent-coordinator/services/runner_registry.py` | Blueprint cleanup, session orphan handling |
| `servers/agent-coordinator/services/callback_processor.py` | Handle orphan failure callbacks |
| `servers/agent-coordinator/main.py` | Name collision handling on registration |

---

## Acceptance Criteria

### Runner Disconnect

1. **Blueprints removed:**
   - Runner goes offline
   - Blueprints no longer appear in agent list
   - Runs for those blueprints fail with "blueprint unavailable"

2. **Sessions failed:**
   - Running session on disconnected runner → status='failed'
   - Error message indicates runner disconnect

3. **Callbacks triggered:**
   - Parent agent receives failure callback
   - Callback includes error details

### Name Collisions

4. **First registration wins:**
   - First runner registers `web-crawler` → stored as `web-crawler`
   - Second runner registers `web-crawler` → stored as `web-crawler@runner_id`

5. **Qualified name works:**
   ```bash
   curl -X POST /runs -d '{"agent_name": "web-crawler@lnch_abc123", ...}'
   # Routes to specific runner
   ```

6. **Unqualified name routes correctly:**
   - If only one `web-crawler` exists → routes to it
   - If multiple exist → error "ambiguous blueprint name"

### Retry Behavior

7. **No auto-retry:**
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

3. **Name collision:**
   - Register runner A with `web-crawler`
   - Register runner B with `web-crawler`
   - Verify: Both stored with different names
   - Verify: Lookup by qualified name works

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
