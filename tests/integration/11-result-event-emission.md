# Test: Result Event Emission

Verify that executors emit a `result` event after session completion, containing structured output.

## Prerequisites

- Database reset: `./tests/scripts/reset-db`
- Agent Coordinator running
- Agent Runner running with `-x test-executor` profile
- sse-monitor running

## Test Steps

### Step 1: Create a start_session run

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "parameters": {"prompt": "Hello, this is a test message"},
    "project_dir": "."
  }'
```

Expected response:
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending","message":"Run queued"}
```

Note the `session_id` for verification.

### Step 2: Wait for execution

The runner should pick up the run within a few seconds.

### Step 3: Observe WebSocket events

Watch the sse-monitor output for the `result` event.

## Expected Events (in order)

1. **session_created** (status: pending)
2. **run_start**
3. **session_updated** (status: running)
4. **message (user)**
5. **message (assistant)**
6. **result** (NEW - structured output event)
   ```json
   {
     "type": "event",
     "data": {
       "event_type": "result",
       "session_id": "ses_...",
       "timestamp": "...",
       "result_text": "[TEST-EXECUTOR] Received: Hello, this is a test message",
       "result_data": null
     }
   }
   ```
   Note: `result_data` is `null` for AI agents (test-executor, claude-code). It will contain structured JSON for deterministic agents.

7. **session_updated** (status: finished)
8. **run_completed**

## Verification Checklist

- [ ] `result` event is received after message events and before run_completed
- [ ] `result` event has `event_type: "result"`
- [ ] `result` event has `result_text` containing the assistant's output
- [ ] `result` event has `result_data: null` (for test-executor/claude-code)
- [ ] `session_id` in result event matches the session
- [ ] `timestamp` is present and valid ISO format

## Verify via Database

Check the events table directly:

```bash
sqlite3 servers/agent-coordinator/.agent-orchestrator/observability.db \
  "SELECT event_type, result_text, result_data FROM events WHERE session_id = 'ses_...' AND event_type = 'result'"
```

Expected output:
```
result|[TEST-EXECUTOR] Received: Hello, this is a test message|
```

## Cleanup

Run `./tests/scripts/reset-db` before the next test.
