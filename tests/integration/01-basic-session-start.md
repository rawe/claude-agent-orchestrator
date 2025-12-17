# Test: Basic Session Start

Verify that starting a new session produces the correct sequence of WebSocket events.

## Prerequisites

- Database reset: `./tests/scripts/reset-db`
- Agent Coordinator running
- Agent Launcher running with `-x test-executor`
- ws-monitor running

## Test Steps

### Step 1: Create a start_session run

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "session_name": "test-basic-001",
    "prompt": "Hello, this is a test message",
    "project_dir": "."
  }'
```

Expected response:
```json
{"run_id":"run_...","status":"pending","message":"Run queued"}
```

### Step 2: Wait for execution

The launcher should pick up the run within a few seconds. Watch the launcher terminal for:
```
[INFO] poller: Received run run_... (start_session)
[INFO] executor: Starting session test-basic-001 with agent test-agent
```

### Step 3: Observe WebSocket events

Watch the ws-monitor output.

## Expected Events (in order)

1. **session_created**
   ```json
   {"type": "session_created", "session": {"session_id": "<uuid>", "session_name": "test-basic-001", "status": "running", "agent_name": null, ...}}
   ```

2. **message (user)**
   ```json
   {"type": "event", "data": {"event_type": "message", "session_id": "<uuid>", "session_name": "test-basic-001", "role": "user", "content": [{"type": "text", "text": "Hello, this is a test message"}], ...}}
   ```

3. **message (assistant)**
   ```json
   {"type": "event", "data": {"event_type": "message", "session_id": "<uuid>", "session_name": "test-basic-001", "role": "assistant", "content": [{"type": "text", "text": "<response from executor>"}], ...}}
   ```
   - With `test-executor`: `"[TEST-EXECUTOR] Received: Hello, this is a test message"`
   - With `claude-code`: Actual Claude response

4. **session_updated**
   ```json
   {"type": "session_updated", "session": {"session_id": "<uuid>", "session_name": "test-basic-001", "status": "finished", ...}}
   ```

5. **session_stop**
   ```json
   {"type": "event", "data": {"event_type": "session_stop", "session_id": "<uuid>", "session_name": "test-basic-001", "exit_code": 0, "reason": "completed", ...}}
   ```

## Verification Checklist

- [ ] All 5 events received in correct order (session_created, user message, assistant message, session_updated, session_stop)
- [ ] `session_id` is consistent across all events
- [ ] `session_name` is "test-basic-001" in all events
- [ ] User message content matches the prompt sent
- [ ] Assistant message received (content depends on executor type)
- [ ] session_stop has exit_code 0 and reason "completed"
- [ ] Timestamps are sequential (each event timestamp >= previous)

## Cleanup

The session data is stored in:
- Database: `servers/agent-coordinator/.agent-orchestrator/observability.db`
- Test executor: `servers/agent-launcher/executors/test-executor/.test-executor-data/test-basic-001.json`

Run `./tests/scripts/reset-db` before the next test.
