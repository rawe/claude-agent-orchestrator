# Test: Callback on Child Agent Failure

Verify that when a child agent fails, the parent receives a failure callback with error details.

## Prerequisites

- Agent Runtime running
- Agent Launcher running with `claude-code` executor
- ws-monitor running
- Agent Orchestrator MCP server running on port 9500:
  ```bash
  uv run mcps/agent-orchestrator/agent-orchestrator-mcp.py --http-mode --port 9500
  ```
- `agent-orchestrator` blueprint copied (see `tests/README.md` → "Agent Blueprints")

## Test Steps

### Step 1: Start parent orchestrator with instruction to spawn failing child

```bash
curl -X POST http://localhost:8765/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "session_name": "test-parent-fail-cb",
    "agent_name": "agent-orchestrator",
    "prompt": "Start a child agent session with session_name=\"test-child-fail\" using the agent_blueprint_name=\"super-fancy-unicorn-agent\" in callback mode. The prompt should be: just say hello. Wait for the callback result.",
    "project_dir": "."
  }'
```

Note: `super-fancy-unicorn-agent` does not exist and will cause the child to fail.

### Step 2: Wait and observe

The parent will:
1. Call MCP tool `start_agent_session` with non-existent blueprint
2. Child job is created
3. Executor fails (agent blueprint not found)
4. Parent receives failure callback

### Step 3: Ask parent what happened

Resume the parent session to ask about the failure:

```bash
curl -X POST http://localhost:8765/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "resume_session",
    "session_name": "test-parent-fail-cb",
    "prompt": "What happened with the child agent you tried to start? What was the error?",
    "project_dir": "."
  }'
```

## Expected Behavior

1. Child job created successfully (job creation passes)
2. Executor fails (blueprint not found → exit code 1)
3. `report_job_failed` called by launcher
4. Callback triggered to parent with failure message
5. Parent receives resume with prompt containing:
   - `"test-child-fail" has failed`
   - Error details

## Verification Checklist

- [ ] Child job shows status `failed` in `/jobs/{job_id}`
- [ ] Parent session was resumed automatically after child failure
- [ ] Parent can explain what error occurred
- [ ] Error message mentions the non-existent agent blueprint

## Key Difference from Success Callback (05)

| Aspect | Success (05) | Failure (07) |
|--------|--------------|--------------|
| Template | `CALLBACK_PROMPT_TEMPLATE` | `CALLBACK_FAILED_PROMPT_TEMPLATE` |
| Header | "has completed" | "has failed" |
| Content | Child result | Error message |
