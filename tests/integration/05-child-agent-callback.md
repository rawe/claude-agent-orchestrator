# Test: Child Agent with Callback

Verify that an orchestrator agent can spawn a child agent in callback mode (`mode=async_callback`) with parent-child relationship.

**Note**: As of ADR-003, `parent_session_id` is always set for child sessions regardless of execution mode. The `execution_mode` field controls callback behavior.

## Prerequisites

- Agent Coordinator running
- Agent Runner running with `claude-code` executor
- sse-monitor running
- Agent Orchestrator MCP server running on port 9500:
  ```bash
  uv run --script mcps/agent-orchestrator/agent-orchestrator-mcp.py --http-mode --port 9500
  ```
- `agent-orchestrator` blueprint copied (see `tests/README.md` → "Agent Blueprints")

## Test Steps

### Step 1: Verify setup

```bash
curl -s http://localhost:8765/agents | grep agent-orchestrator
```

### Step 2: Create orchestrator session with callback mode

```bash
curl -X POST http://localhost:8765/runs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "agent_name": "agent-orchestrator",
    "prompt": "Start a child agent in callback mode. The child should just say hello and exit.",
    "project_dir": "."
  }'
```

Expected response:
```json
{"run_id":"run_...","session_id":"ses_...","status":"pending"}
```

Note the `session_id` - this is the parent session.

Note: The key difference is **"in callback mode"** in the prompt.

### Step 3: Wait for completion

Both parent and child sessions should complete. The parent will be resumed after the child completes.

### Step 4: Verify parent-child relationship

```bash
curl -s http://localhost:8765/sessions | python -m json.tool | grep -B2 -A8 "parent_session_id"
```

## Expected Behavior

1. Parent session starts
2. Parent calls MCP tool with `mode=async_callback`
3. Child session created with `parent_session_id` set and `execution_mode=async_callback`
4. Parent session pauses (waiting for callback)
5. Child executes and completes
6. Parent session resumes with callback message
7. Parent receives child result and completes

## Verification Checklist

- [ ] Child session has `parent_session_id` set to parent's `session_id`
- [ ] Child session has `execution_mode` set to `async_callback`
- [ ] Both session IDs follow format `ses_...`
- [ ] Parent receives callback message: "The child agent session ... has completed"
- [ ] Parent session resumes after child completes
- [ ] Both sessions complete successfully

## Difference from Sync Mode (04-child-agent-sync)

| Aspect | Sync Mode | Callback Mode |
|--------|-----------|---------------|
| `execution_mode` | `sync` | `async_callback` |
| `parent_session_id` | Set to parent | Set to parent |
| Parent waits | Blocks during call | Pauses, resumes on callback |
| Use case | Quick tasks | Long-running child tasks |
