# Test: Child Agent (Sync Mode)

Verify that an orchestrator agent can spawn a child agent in synchronous mode.

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

### Step 1: Verify agent blueprint is available

```bash
curl -s http://localhost:8765/agents | python -m json.tool
```

Should include `agent-orchestrator` in the list.

### Step 2: Create orchestrator session

```bash
curl -X POST http://localhost:8765/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "session_name": "test-orchestrator-001",
    "agent_name": "agent-orchestrator",
    "prompt": "Start a child agent with session name test-child-001. The child should just say hello and exit.",
    "project_dir": "."
  }'
```

### Step 3: Observe WebSocket events

Watch ws-monitor for:
1. Parent session events (test-orchestrator-001)
2. Child session events (test-child-001)

## Expected Events

### Parent Session Start
```json
{"type": "session_created", "session": {"session_name": "test-orchestrator-001", "agent_name": "agent-orchestrator", ...}}
```

### Child Session Created
```json
{"type": "session_created", "session": {"session_name": "test-child-001", "parent_session_name": "test-orchestrator-001", ...}}
```

### Child Session Complete
```json
{"type": "event", "data": {"event_type": "session_stop", "session_name": "test-child-001", "exit_code": 0, ...}}
```

## Verification Checklist

- [ ] Parent session created with `agent_name: "agent-orchestrator"`
- [ ] Child session created with `parent_session_name` set to parent
- [ ] Child session completes successfully
- [ ] Parent session completes successfully

## Troubleshooting

### MCP server not reachable
- Verify MCP server is running: `curl http://localhost:9500/mcp`
- Check port matches `agent.mcp.json` config (9500)

### Agent blueprint not found
- Verify blueprint is copied (see `tests/README.md` → "Agent Blueprints")
- Check runtime logs for agent loading errors

### Child agent not starting
- Check MCP server logs for errors
- Verify `AGENT_SESSION_NAME` header is passed correctly