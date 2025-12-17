---
description: Stop test services and cleanup
---

# Integration Test Teardown

Stop all test services and clean up the environment.

See `tests/README.md` for full documentation.

## Your Task

1. **Stop background processes**:
   - Stop Agent Coordinator (the uv run python -m main process)
   - Stop Agent Runner (the agent-runner process)
   - Stop WebSocket Monitor (the ws-monitor process)

2. **Reset database**: `./tests/scripts/reset-db`

3. **Verify cleanup**:
   - Confirm port 8765 is free: `lsof -i :8765` should return nothing
   - Confirm no orphan processes

4. **Report** which processes were stopped
