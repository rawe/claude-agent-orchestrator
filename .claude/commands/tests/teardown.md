---
description: Stop test services and cleanup
---

# Integration Test Teardown

Stop all test services and clean up the environment.

See `tests/README.md` for full documentation.

## Your Task

1. **Stop background processes** (check your tracked tasks first):
   - Use `/tasks` to list active background shells you started during testing
   - Use `KillShell` tool to stop each active background task by ID
   - This should include:
     - Agent Coordinator (`uv run python -m main`)
     - Agent Runner (`agent-runner`)
     - SSE Monitor (`sse-monitor`)
     - MCP Server (`agent-orchestrator-mcp`) if started for testing

2. **Cleanup any remaining processes** (only if background tasks didn't cover them):
   - Check: `lsof -i :8765` - kill any remaining processes on that port
   - Check: `pgrep -af "python -m main|agent-runner|sse-monitor|agent-orchestrator-mcp"`

3. **Reset database**: `./tests/scripts/reset-db`

4. **Verify cleanup**:
   - Confirm port 8765 is free: `lsof -i :8765` should return nothing
   - Confirm no orphan test processes

5. **Report** which processes/tasks were stopped
