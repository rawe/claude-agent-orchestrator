---
description: Run all integration tests (setup, execute all cases, teardown)
---

# Run All Integration Tests

Complete test suite execution with automatic setup and teardown.

See `tests/README.md` for full documentation.

## Your Task

### Phase 1: Setup

1. **Reset the database**: `./tests/scripts/reset-db`

2. **Start services** in background:
   - Agent Coordinator: `cd servers/agent-coordinator && uv run python -m main`
   - Agent Launcher: `./servers/agent-launcher/agent-launcher -x test-executor`
   - WebSocket Monitor: `./tests/tools/ws-monitor`

3. **Verify** all services are running and healthy

### Phase 2: Execute Test Cases

For each test case in `tests/integration/` (in alphabetical order):

1. Read the test case documentation
2. Execute the test steps (curl commands, etc.)
3. Capture WebSocket events
4. Verify against expected events checklist
5. Record pass/fail for each verification item

**Note**: Tests run sequentially in the same database. The database cannot be reset while services are running (coordinator creates tables on startup).

### Phase 3: Teardown

1. Stop all background processes (coordinator, launcher, ws-monitor)
2. Final database cleanup: `./tests/scripts/reset-db`

### Phase 4: Report

Provide a summary:
- Total test cases run
- Passed / Failed counts
- For failures: which checks failed and why
- Any unexpected errors or issues

## Important Notes

- Continue running all tests even if one fails
- Capture all WebSocket output for analysis
- Database can only be reset when services are stopped (requires full restart for isolation)
