# Callback Flow Test Plan

## Context

You are an AI coding assistant with access to the Agent Orchestrator MCP Server. The infrastructure is running:
- **Agent Runtime API**: `http://localhost:8765`
- **MCP Server**: Available via your MCP tools (agent orchestrator tools)
- **Agent Launcher**: Polling for jobs

**Important limitation**: You are NOT started by the Agent Launcher, so you don't have `AGENT_SESSION_NAME` set. This means you cannot directly test the callback header flow. However, you can test the callback architecture by using an orchestrator agent.

## Documentation References

Read these files for implementation details:
- `docs/implementation-guides/mcp-server-api-refactor.md` - Architecture and API details
- `docs/implementation-guides/mcp-server-api-refactor-report.md` - Implementation status
- `docs/implementation-guides/mcp-server-api-refactor-bugs.md` - Known bugs

## Test Scenario: Callback Flow via Orchestrator Agent

### Objective
Verify that when an orchestrator agent starts a child session with `callback=true`, the child session correctly records the `parent_session_name`.

### Steps

1. **List available blueprints**
   - Use `list_agent_blueprints` MCP tool
   - Confirm `orchestrator` agent exists

2. **Start an orchestrator session**
   ```
   session_name: "test-orchestrator-parent"
   prompt: "Start a child session named 'test-callback-child' with callback=true and prompt 'Say hello'. Then report the result."
   async_mode: false
   ```

3. **Verify the callback relationship**
   - Use Agent Runtime API directly: `GET http://localhost:8765/sessions/by-name/test-callback-child`
   - Check that `parent_session_name` equals `"test-orchestrator-parent"`

4. **Verify parent session name updates on resume**
   - Start another orchestrator session: `"test-orchestrator-parent-2"`
   - Have it resume `test-callback-child` with `callback=true`
   - Verify `parent_session_name` updated to `"test-orchestrator-parent-2"`

### Expected Results

| Check | Expected |
|-------|----------|
| Child session created | `test-callback-child` exists |
| Parent recorded | `parent_session_name = "test-orchestrator-parent"` |
| Parent updated on resume | `parent_session_name = "test-orchestrator-parent-2"` |

### Alternative: Direct Jobs API Test

If no orchestrator blueprint exists, test via Jobs API directly:

```bash
# Create child with parent
curl -X POST http://localhost:8765/jobs \
  -H "Content-Type: application/json" \
  -d '{"type": "start_session", "session_name": "manual-child", "prompt": "Say hello", "parent_session_name": "manual-parent"}'

# Wait for completion, then verify
curl http://localhost:8765/sessions/by-name/manual-child | jq '.session.parent_session_name'
# Expected: "manual-parent"
```

## Cleanup

After testing:
```bash
curl -X DELETE http://localhost:9500/api/sessions
```
