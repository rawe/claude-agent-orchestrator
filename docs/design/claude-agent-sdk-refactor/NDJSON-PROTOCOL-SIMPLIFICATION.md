# NDJSON Protocol Simplification: Remove run_id from Executor Protocol

## Status: Decision Record (Phase 2)

## Context

The NDJSON protocol between runner and executor currently passes `run_id` in three places:

1. **Initial invocation**: `metadata.run_id` (turn 1)
2. **Turn request**: `{"type": "turn", "run_id": "run_002", ...}` (turn N)
3. **Turn complete**: `{"type": "turn_complete", "run_id": "...", ...}` (response)

The executor reads `run_id` from input and echoes it unchanged to `turn_complete`. All 7
occurrences of `run_id` in `sdk_client.py` are pure passthrough:

| Line | Code | Purpose |
|------|------|---------|
| 395 | `initial_run_id = initial_invocation.metadata.get("run_id", "")` | Read from input |
| 450 | `"run_id": initial_run_id` | Echo to turn_complete |
| 477 | `turn_run_id = msg.get("run_id", "")` | Read from input |
| 507 | `"run_id": turn_run_id` | Echo to turn_complete |

The executor never uses `run_id` for any internal purpose. It does not pass it to the SDK,
does not include it in session events (which are session_id-addressed), and does not use it
for error handling or logging.

### Why run_id was there

The original protocol design assumed the runner needed a correlation ID in `turn_complete` to
know which run just finished. This seemed reasonable when the protocol was designed in isolation.

### Why it is unnecessary

The NDJSON protocol is **strictly sequential**: one outstanding turn at a time, enforced by
the `ClaudeSDKClient`'s blocking `query()` + `receive_response()` pattern. The runner always
knows which run is active because it sent the turn request. There is no interleaving, no
out-of-order completion, and no ambiguity about which turn produced which `turn_complete`.

The Phase 2 registry design (`PHASE2-RUNNER-ARCHITECTURE.md`) already tracks
`current_run_id` per session. The runner sets this when it routes a turn and clears it when
it receives `turn_complete`. The executor is redundantly echoing information the runner
already has.

## Decision: Option C -- Executor is session-pure, runner owns run_id mapping

Remove `run_id` from the NDJSON protocol entirely. The executor subprocess operates in a
session-pure context: it knows `session_id` and nothing else about the coordinator's run
lifecycle.

**Separation of concerns**:
- **Executor**: Owns the Claude SDK session. Knows `session_id`. Sends session events
  (bind, messages, result) via HTTP. Receives prompts, returns results.
- **Runner**: Owns run lifecycle. Knows `run_id`, `session_id`, and which process serves
  which session. Maps `turn_complete` to the current active `run_id` via the registry.

## Before / After Message Formats

### Initial Invocation (stdin, line 1)

```json
// BEFORE
{
  "schema_version": "2.2",
  "mode": "start",
  "session_id": "ses_abc123",
  "parameters": { "prompt": "Hello" },
  "metadata": { "run_id": "run_001" }
}

// AFTER
{
  "schema_version": "2.2",
  "mode": "start",
  "session_id": "ses_abc123",
  "parameters": { "prompt": "Hello" }
}
```

`metadata.run_id` removed. The `metadata` object may still exist for future extensibility
but no longer carries `run_id`.

### Turn Request (stdin, subsequent lines)

```json
// BEFORE
{ "type": "turn", "run_id": "run_002", "parameters": { "prompt": "Add auth" } }

// AFTER
{ "type": "turn", "parameters": { "prompt": "Add auth" } }
```

### Turn Complete (stdout)

```json
// BEFORE
{ "type": "turn_complete", "run_id": "run_001", "result": "Done." }

// AFTER
{ "type": "turn_complete", "result": "Done." }
```

### Shutdown (unchanged)

```json
{ "type": "shutdown" }
```

## Changes Required

### Executor side (removals only)

**`executors/claude-sdk-executor/lib/sdk_client.py`**:

Remove 4 lines in `run_multi_turn_session()`:
- Line 395: `initial_run_id = initial_invocation.metadata.get("run_id", "")`  -- delete
- Line 450: `"run_id": initial_run_id,`  -- delete from turn_complete dict
- Line 477: `turn_run_id = msg.get("run_id", "")`  -- delete
- Line 507: `"run_id": turn_run_id,`  -- delete from turn_complete dict

No new code. Net change: -4 lines.

### Runner side (Phase 2 implementation)

**`lib/supervisor.py`** -- stdout reader for persistent processes:

When the stdout reader receives `turn_complete`, it looks up the active `run_id` from the
registry instead of reading it from the message:

```python
def _report_turn_complete(self, session_id: str) -> None:
    entry = self.registry.get_session(session_id)
    if not entry or not entry.current_run_id:
        return  # no active run (already reported or race)
    run_id = entry.current_run_id
    # ... report completed, remove run from registry
```

The stdout reader thread is started per-process and already knows `session_id` (passed at
thread creation time). It does not need `run_id` from the message.

**`lib/registry.py`** -- `current_run_id` field:

The registry's session entry tracks `current_run_id`, set by the poller when routing a turn
and cleared by the supervisor when processing `turn_complete`. This field is the single
source of truth for which run is active on a session.

### Runner payload (no change needed)

**`lib/executor.py`** -- `_build_payload()` (line 248-286):

This function already does not include `run_id` in the payload. Finding #1 (run_id dropped
at payload construction) is dissolved: there was never a need to pass it.

## Relationship to NDJSON-PROTOCOL-REFERENCE.md

`NDJSON-PROTOCOL-REFERENCE.md` documents the current protocol with `run_id` in all three
message types. After this change is implemented:

1. Remove `metadata.run_id` from the initial invocation example and field table (line 40-41, 54)
2. Remove `run_id` from the turn request example and field table (line 63, 73)
3. Remove `run_id` from the turn_complete example and field table (line 107, 115)
4. Update the "Phase 2 Integration Notes" section (line 173+) to note that the runner
   tracks `run_id` internally

These updates should be made when the code changes land, not before, so the doc matches
the implemented state.
