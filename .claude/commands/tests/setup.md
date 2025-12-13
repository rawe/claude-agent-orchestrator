---
description: Setup integration test environment (reset DB, start services)
---

# Integration Test Setup

Prepare the test environment for running integration tests.

See `tests/README.md` for full documentation.

## Your Task

1. **Reset the database** - Run `./tests/scripts/reset-db`

2. **Start Agent Runtime** in background:
   ```bash
   cd servers/agent-runtime && uv run python -m main
   ```

3. **Start Agent Launcher** with test-executor in background:
   ```bash
   ./servers/agent-launcher/agent-launcher -x test-executor
   ```

4. **Start WebSocket Monitor** in background:
   ```bash
   ./tests/tools/ws-monitor
   ```

5. **Verify services** are running:
   - Health check: `curl -s http://localhost:8765/health`
   - Confirm launcher registered (check launcher logs)
   - Confirm ws-monitor connected

6. **Report status** - Tell me which services are running and ready

Keep track of background process IDs so they can be stopped later with `/tests/teardown` or manually.
