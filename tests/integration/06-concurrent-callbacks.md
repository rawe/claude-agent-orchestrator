# Test: Concurrent Callbacks (Race Condition Detection)

Verify that multiple child agents completing in rapid succession all have their callbacks properly received by the parent agent. This test is designed to detect race conditions where callbacks may be "swallowed" or overwritten.

## Prerequisites

- Agent Runtime running
- Agent Launcher running with `claude-code` executor
- ws-monitor running
- Agent Orchestrator MCP server running on port 9500:
  ```bash
  uv run mcps/agent-orchestrator/agent-orchestrator-mcp.py --http-mode --port 9500
  ```
- `agent-orchestrator` blueprint copied (see `tests/README.md` → "Agent Blueprints")

## Test Design

**Wave-based timing:**
- Wave 1 (5 seconds): 3 agents complete nearly simultaneously
- Wave 2 (10 seconds): 2 agents complete nearly simultaneously

This creates stress on the callback handling system to expose potential race conditions.

## Test Steps

### Step 1: Verify setup

```bash
curl -s http://localhost:8765/agents | grep agent-orchestrator
```

### Step 2: Start parent orchestrator session

```bash
curl -X POST http://localhost:8765/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_session",
    "session_name": "test-concurrent-parent",
    "agent_name": "agent-orchestrator",
    "prompt": "Start 5 child agents in callback mode with these session names and wait times:\n- sleeper-agent-001: wait 5 seconds, then respond \"callback-001\"\n- sleeper-agent-002: wait 5 seconds, then respond \"callback-002\"\n- sleeper-agent-003: wait 5 seconds, then respond \"callback-003\"\n- sleeper-agent-004: wait 10 seconds, then respond \"callback-004\"\n- sleeper-agent-005: wait 10 seconds, then respond \"callback-005\"\n\nEach agent must ONLY run: sleep N && echo \"callback-XXX\"\nDo not respond until you have received all callbacks.",
    "project_dir": "."
  }'
```

### Step 3: Wait for all agents to complete

Monitor ws-monitor for completion events. Expected timeline:
- ~5 seconds: sleeper-agent-001, 002, 003 complete (Wave 1)
- ~10 seconds: sleeper-agent-004, 005 complete (Wave 2)

Wait approximately 60-90 seconds for parent to process all callbacks.

### Step 4: Verify all child sessions completed

```bash
curl -s http://localhost:8765/sessions | python -m json.tool | grep -E "(session_name|status)" | head -20
```

All 5 sleeper-agent sessions should show as completed.

### Step 5: Resume parent to verify received callbacks

This is the critical verification step. Resume the parent session and ask it to check its own conversation history:

```bash
curl -X POST http://localhost:8765/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "resume_session",
    "session_name": "test-concurrent-parent",
    "prompt": "IMPORTANT: Check your conversation history ONLY. Do NOT use any tools or API calls.\n\nList ALL child agent callbacks you received in this session. For each callback, state:\n1. The agent session name\n2. The callback message content\n\nThen confirm: Did you receive callbacks from ALL 5 agents (sleeper-agent-001 through sleeper-agent-005)? Answer YES or NO, and list any missing agents."
  }'
```

### Step 6: Check parent response

Wait for the parent to respond. The response will reveal which callbacks were actually recorded in its conversation history.

## Expected Behavior

### Success Case
1. All 5 child agents complete
2. Parent receives all 5 callbacks in its conversation history
3. Parent confirms: "YES, received callbacks from all 5 agents"

### Failure Case (Race Condition Detected)
1. All 5 child agents complete
2. Parent's history is missing 1 or more callbacks
3. Parent confirms: "NO, missing callbacks from: sleeper-agent-XXX"

## Verification Checklist

- [ ] All 5 sleeper-agent sessions created
- [ ] All 5 sleeper-agent sessions completed (check via API)
- [ ] Parent received callback from sleeper-agent-001
- [ ] Parent received callback from sleeper-agent-002
- [ ] Parent received callback from sleeper-agent-003
- [ ] Parent received callback from sleeper-agent-004
- [ ] Parent received callback from sleeper-agent-005
- [ ] Parent confirms all 5 callbacks in history verification step

## Interpreting Results

### If callbacks are missing:
This indicates a race condition in the callback handling system. Possible causes:
- Session resume overwrites previous resume
- Callback messages not properly queued
- Locking issues in session state management

### Timing analysis:
Note which callbacks are missing. If Wave 1 agents (001-003) are affected more than Wave 2, it suggests concurrent callbacks are being overwritten.

## WebSocket Events to Monitor

```
# Wave 1 completions (~5 sec)
{"type": "event", "data": {"event_type": "session_stop", "session_name": "sleeper-agent-001", ...}}
{"type": "event", "data": {"event_type": "session_stop", "session_name": "sleeper-agent-002", ...}}
{"type": "event", "data": {"event_type": "session_stop", "session_name": "sleeper-agent-003", ...}}

# Wave 2 completions (~10 sec)
{"type": "event", "data": {"event_type": "session_stop", "session_name": "sleeper-agent-004", ...}}
{"type": "event", "data": {"event_type": "session_stop", "session_name": "sleeper-agent-005", ...}}

# Parent resumes (should see 5 resume events)
{"type": "event", "data": {"event_type": "session_start", "session_name": "test-concurrent-parent", ...}}
```

## Troubleshooting

### Parent doesn't spawn all 5 agents
- Check MCP server logs for errors
- Verify agent-orchestrator blueprint has correct MCP configuration

### Parent responds before all callbacks
- Increase wait times (e.g., 10s and 20s instead of 5s and 10s)
- Check if parent prompt is being followed correctly

### Cannot determine callback status
- Check parent session's full conversation via logs
- Look at Agent Launcher logs for callback delivery attempts
