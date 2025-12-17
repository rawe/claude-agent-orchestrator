# Test: Session Resume

Verify that resuming an existing session produces the correct sequence of WebSocket events.

## Prerequisites

- Complete test `01-basic-session-start` first (need existing session)
- OR create a session using Step 0 below
- Agent Coordinator running
- Agent Launcher running with `-x test-executor`
- ws-monitor running

## Test Steps

### Step 0: Create initial session (if needed)

Skip this if you just completed `01-basic-session-start` with session "test-basic-001".

```bash
curl -X POST http://localhost:8765/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "session_name": "test-resume-001",
    "prompt": "Initial message",
    "project_dir": "."
  }'
```

Wait for the job to complete (watch launcher logs).

### Step 1: Create a resume_session job

```bash
curl -X POST http://localhost:8765/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "resume_session",
    "session_name": "test-basic-001",
    "prompt": "This is a follow-up message"
  }'
```

Expected response:
```json
{"job_id":"job_...","status":"pending","message":"Job queued"}
```

### Step 2: Wait for execution

Watch the launcher terminal for:
```
[INFO] poller: Received job job_... (resume_session)
[INFO] executor: Resuming session test-basic-001
```

### Step 3: Observe WebSocket events

Watch the ws-monitor output.

## Expected Events (in order)

1. **session_start (resume indicator)**
   ```json
   {"type": "event", "data": {"event_type": "session_start", "session_id": "<same uuid as original session>", "session_name": "test-basic-001", ...}}
   ```

2. **message (user)**
   ```json
   {"type": "event", "data": {"event_type": "message", "session_id": "<uuid>", "session_name": "test-basic-001", "role": "user", "content": [{"type": "text", "text": "This is a follow-up message"}], ...}}
   ```

3. **message (assistant)**
   ```json
   {"type": "event", "data": {"event_type": "message", "session_id": "<uuid>", "session_name": "test-basic-001", "role": "assistant", "content": [{"type": "text", "text": "<response from executor>"}], ...}}
   ```

4. **session_updated**
   ```json
   {"type": "session_updated", "session": {"session_id": "<uuid>", "session_name": "test-basic-001", "status": "finished", ...}}
   ```

5. **session_stop**
   ```json
   {"type": "event", "data": {"event_type": "session_stop", "session_id": "<uuid>", "session_name": "test-basic-001", "exit_code": 0, "reason": "completed", ...}}
   ```

## Verification Checklist

- [ ] All 5 events received in correct order (session_start, user message, assistant message, session_updated, session_stop)
- [ ] `session_id` matches the original session (from start)
- [ ] `session_name` is consistent across all events
- [ ] `last_resumed_at` is set (was `null` before resume)
- [ ] session_start event received (indicates resume)
- [ ] User message content matches the resume prompt
- [ ] Assistant message received (content depends on executor type)
- [ ] session_stop has exit_code 0 and reason "completed"

## Verify Session History

Check the test executor's local data to verify message history:

```bash
cat servers/agent-launcher/executors/test-executor/.test-executor-data/test-basic-001.json | python -m json.tool
```

Expected: Should show all messages (from both start and resume).

## Cleanup

Run `./tests/scripts/reset-db` before the next test.
