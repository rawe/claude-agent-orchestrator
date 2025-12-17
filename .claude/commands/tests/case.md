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

### Phase 1: Read Test Case

1. **Find the test case file** at `tests/integration/$ARGUMENTS.md` or `tests/integration/0$ARGUMENTS-*.md`
   - If not found, list available test cases and ask which one to run

2. **Read the test case** prerequisites and determine:
   - Which executor is needed (look for `claude-code` or `test-executor` in prerequisites)
   - Whether MCP server is needed (prerequisites mention "Agent Orchestrator MCP server")
   - Whether agent blueprints need to be copied (prerequisites mention blueprint)

### Phase 2: Copy Agent Blueprints (if needed)

3. **Copy agent blueprints** if the test case prerequisites mention blueprints:
   - See `tests/README.md` → "Agent Blueprints" for copy instructions
   - Blueprints must be copied BEFORE starting the Agent Coordinator

### Phase 3: Setup Services

4. **Run `/tests:setup <executor>`** with the executor identified from the test case prerequisites:
   - If prerequisites mention `claude-code` executor: `/tests:setup claude-code`
   - Otherwise: `/tests:setup` (defaults to `test-executor`)

### Phase 4: Start MCP Server (if needed)

5. **Start MCP server** if the test case prerequisites mention it:
   - See `tests/README.md` → "Agent Orchestrator MCP Server" for instructions

6. **Verify all prerequisites** are satisfied before proceeding

### Phase 5: Execute Test

7. **Execute test steps** as documented in the test case file

8. **Verify expected events** against the checklist in the test case

9. **Report results**:
   - Which checks passed/failed
   - Show relevant WebSocket events received
   - Highlight any discrepancies

Do NOT stop services after the test - they should remain running for additional tests.
