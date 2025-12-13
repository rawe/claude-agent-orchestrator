---
description: Run a specific integration test case
argument-hint: <test-name>
---

# Run Integration Test Case

Execute the specified integration test case.

See `tests/README.md` for full documentation and `tests/integration/` for available test cases.

## Input

Test case to run: `$ARGUMENTS`

## Your Task

1. **Find the test case file** at `tests/integration/$ARGUMENTS.md`
   - If not found, list available test cases and ask which one to run

2. **Read the test case** documentation

3. **Verify prerequisites**:
   - Services should be running (from `/tests/setup`)
   - Check: `curl -s http://localhost:8765/health`

4. **Execute test steps** as documented in the test case file:
   - Run curl commands
   - Wait for job completion
   - Observe WebSocket monitor output

5. **Verify expected events** against the checklist in the test case

6. **Report results**:
   - Which checks passed/failed
   - Show relevant WebSocket events received
   - Highlight any discrepancies

Do NOT stop services after the test - they should remain running for additional tests.
