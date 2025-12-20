# Test: Session Resume

Verify that resuming an existing session produces the correct sequence of WebSocket events.

## Prerequisites

- Complete test `01-basic-session-start` first (need existing session)
- OR create a session using Step 0 below
- Agent Coordinator running
- Agent Runner running with `-x test-executor`
- ws-monitor running

## Test Steps

### Step 0: Create initial session (if needed)

Skip this if you just completed `01-basic-session-start`.

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "prompt": "Initial message",
    "project_dir": "."
  }'
```

Wait for the run to complete and note the `session_id` from the response (format: `ses_...`).

### Step 1: Create a resume_session run

Use the `session_id` from Step 0 or from test 01:

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "resume_session",
    "session_id": "<session_id_from_previous_run>",
    "prompt": "This is a follow-up message"
  }'
```

Expected response:
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending","message":"Run queued"}
```

Note: The `session_id` in the response should match the one you provided.

### Step 2: Wait for execution

Watch the runner terminal for:
```
[INFO] poller: Received run run_... (resume_session)
[INFO] executor: Resuming session ses_...
```

### Step 3: Observe WebSocket events

Watch the ws-monitor output.

## Expected Events (in order)

1. **session_updated** (status: running, resume indicator)
   ```json
   {"type": "session_updated", "session": {"session_id": "ses_...", "status": "running", ...}}
   ```

2. **session_start** (resume event)
   ```json
   {"type": "event", "data": {"event_type": "session_start", "session_id": "ses_...", ...}}
   ```

3. **message (user)**
   ```json
   {"type": "event", "data": {"event_type": "message", "session_id": "ses_...", "role": "user", "content": [{"type": "text", "text": "This is a follow-up message"}], ...}}
   ```

4. **message (assistant)**
   ```json
   {"type": "event", "data": {"event_type": "message", "session_id": "ses_...", "role": "assistant", "content": [{"type": "text", "text": "<response from executor>"}], ...}}
   ```

5. **session_updated** (status: finished)
   ```json
   {"type": "session_updated", "session": {"session_id": "ses_...", "status": "finished", ...}}
   ```

6. **session_stop**
   ```json
   {"type": "event", "data": {"event_type": "session_stop", "session_id": "ses_...", "exit_code": 0, "reason": "completed", ...}}
   ```

## Verification Checklist

- [ ] All events received in correct order
- [ ] `session_id` matches the original session (from start)
- [ ] `session_id` is consistent across all events
- [ ] `last_resumed_at` is set (was `null` before resume)
- [ ] session_start event received (indicates resume)
- [ ] User message content matches the resume prompt
- [ ] Assistant message received (content depends on executor type)
- [ ] session_stop has exit_code 0 and reason "completed"
- [ ] `executor_session_id` from original session is used for resume

## Verify Session History

Check the test executor's local data to verify message history:

```bash
cat servers/agent-runner/executors/test-executor/.test-executor-data/<session_id>.json | python -m json.tool
```

Expected: Should show all messages (from both start and resume).

## Cleanup

Run `./tests/scripts/reset-db` before the next test.
