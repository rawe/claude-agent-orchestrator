---
description: Setup integration test environment (reset DB, start services)
argument-hint: [executor]
---

# Integration Test Setup

Prepare the test environment for running integration tests.

See `tests/README.md` for full documentation.

## Input

Executor type: `$ARGUMENTS`

If no executor specified, default to `test-executor`.

Valid executors:
- `test-executor` - Simple echo executor for fast, deterministic tests (default)
- `claude-code` - Real Claude AI executor for end-to-end validation

## Your Task

1. **Reset the database** - Run `./tests/scripts/reset-db`

2. **Start Agent Coordinator** in background:
   ```bash
   cd servers/agent-coordinator && uv run python -m main
   ```

3. **Start Agent Runner** with the specified executor in background:
   ```bash
   ./servers/agent-runner/agent-runner -x <executor>
   ```
   Use `test-executor` if no executor was specified, otherwise use the provided executor.

4. **Start SSE Monitor** in background:
   ```bash
   ./tests/tools/sse-monitor
   ```

5. **Verify services** are running:
   - Health check: `curl -s http://localhost:8765/health`
   - Confirm runner registered (check runner logs)
   - Confirm sse-monitor connected

6. **Report status** - Tell me which services are running and ready

Keep track of background process IDs so they can be stopped later with `/tests/teardown` or manually.
