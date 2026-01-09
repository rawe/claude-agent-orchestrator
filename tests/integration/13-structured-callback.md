# Test: Structured Callback

Verify that callbacks from child agents include structured result format in the callback message.

## Prerequisites

- Agent Coordinator running
- Agent Runner running with `claude-code` executor
- sse-monitor running
- `agent-orchestrator` blueprint copied (see `tests/README.md`)

## Test Steps

### Step 1: Verify setup

```bash
curl -s http://localhost:8765/agents | grep agent-orchestrator
```

### Step 2: Create orchestrator session

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "agent-orchestrator",
    "parameters": {"prompt": "Start a child agent in callback mode. The child should respond with a greeting message."},
    "project_dir": "."
  }'
```

Note the parent `session_id`.

### Step 3: Wait for child completion and callback

Watch sse-monitor for the callback events on the parent session.

## Expected Callback Format

When the child completes, the parent receives a resume with a callback prompt containing the structured result:

```xml
<agent-callback session="ses_CHILD_ID" status="completed">
## Child Result

[Child's result_text here]

</agent-callback>

Please continue with the orchestration based on this result.
```

**Note:** For AI agents (claude-code), only `result_text` is included. For deterministic agents with structured output, an additional section appears:

```xml
<agent-callback session="ses_CHILD_ID" status="completed">
## Child Result

[Child's result_text here]

## Structured Data

```json
{"key": "value", ...}
```

</agent-callback>

Please continue with the orchestration based on this result.
```

## Verification Steps

### Check parent session events

After completion, check the events for the parent session:

```bash
curl -s http://localhost:8765/sessions/ses_PARENT_ID/events | python -m json.tool
```

Look for the resume message event on the parent. The user message content should contain:
- `<agent-callback session="ses_CHILD_ID" status="completed">`
- `## Child Result` section with the child's `result_text`
- If child had `result_data`, a `## Structured Data` section with JSON

### Alternative: Check via database

```bash
sqlite3 servers/agent-coordinator/.agent-orchestrator/observability.db \
  "SELECT content FROM events WHERE session_id = 'ses_PARENT_ID' AND event_type = 'message' AND role = 'user' ORDER BY timestamp DESC LIMIT 1"
```

## Verification Checklist

- [ ] Child session completes with `result` event
- [ ] Parent session receives callback message
- [ ] Callback contains `<agent-callback>` wrapper
- [ ] Callback contains `## Child Result` section
- [ ] `result_text` from child appears in callback
- [ ] For deterministic agents: `## Structured Data` section appears if `result_data` is not null
- [ ] Parent processes callback and completes successfully

## Difference from Test 05 (Child Agent Callback)

| Aspect | Test 05 | Test 13 (this test) |
|--------|---------|---------------------|
| Focus | Parent-child relationship setup | Callback message format |
| Verifies | execution_mode, parent_session_id | result_text, result_data in callback |
| New fields | N/A | result_text, result_data |

## Cleanup

Run `./tests/scripts/reset-db` before the next test.
