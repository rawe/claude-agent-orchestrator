# Test: Callback on Child Agent Failure

Verify that when a child agent fails, the parent receives a failure callback with error details.

Uses `mode=async_callback` for the child agent per ADR-003.

## Prerequisites

- Agent Coordinator running
- Agent Runner running with `claude-code` executor
- sse-monitor running
- `agent-orchestrator` blueprint copied (see `tests/README.md` → "Agent Blueprints")

## Test Steps

### Step 1: Start parent orchestrator with instruction to spawn failing child

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "agent-orchestrator",
    "parameters": {"prompt": "Start a child agent using the agent_blueprint_name=\"super-fancy-unicorn-agent\" in callback mode. The prompt should be: just say hello. Wait for the callback result."},
    "project_dir": "."
  }'
```

Expected response:
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending"}
```

Note the parent `session_id`.

Note: `super-fancy-unicorn-agent` does not exist and will cause the child to fail.

### Step 2: Wait and observe

The parent will:
1. Call MCP tool `start_agent_session` with non-existent blueprint
2. Child run is created (with a new `session_id`)
3. Executor fails (agent blueprint not found)
4. Parent receives failure callback

### Step 3: Ask parent what happened

Resume the parent session to ask about the failure:

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "resume_session",
    "session_id": "<parent_session_id>",
    "parameters": {"prompt": "What happened with the child agent you tried to start? What was the error?"},
    "project_dir": "."
  }'
```

## Expected Behavior

1. Child run created successfully (run creation passes)
2. Executor fails (blueprint not found → exit code 1)
3. `report_run_failed` called by runner
4. Callback triggered to parent with failure message
5. Parent receives resume with prompt containing:
   - Child session ID and "has failed"
   - Error details

## Verification Checklist

- [ ] Child run shows status `failed` in `/runs/{run_id}`
- [ ] Child session has `parent_session_id` set to parent's `session_id`
- [ ] Parent session was resumed automatically after child failure
- [ ] Parent can explain what error occurred
- [ ] Error message mentions the non-existent agent blueprint

## Key Difference from Success Callback (05)

| Aspect | Success (05) | Failure (07) |
|--------|--------------|--------------|
| Template | `CALLBACK_PROMPT_TEMPLATE` | `CALLBACK_FAILED_PROMPT_TEMPLATE` |
| Header | "has completed" | "has failed" |
| Content | Child result | Error message |
