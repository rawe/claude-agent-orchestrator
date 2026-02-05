# Claude Agent SDK Executor Refactoring

Refactoring the Claude Code executor for better separation of concerns and maintainability.

## Status

**In Progress** | Started: 2026-02-05

## Goals

1. **Separation of Concerns**: Split monolithic `claude_client.py` (~660 lines) into focused modules
2. **Testability**: Make individual components unit-testable
3. **Maintainability**: Clear boundaries between SDK interaction, session management, and validation
4. **Zero Regression**: All integration tests must pass after each step

## Current Structure

```
executors/claude-agent-sdk/
├── ao-claude-code-exec       # Entry point (~380 lines)
│   ├── CLI handling (typer)
│   ├── JSON payload parsing
│   └── Route to start/resume
└── lib/
    └── claude_client.py      # Everything else (~660 lines)
        ├── Output schema validation
        ├── MCP server transformation
        ├── Executor config handling
        ├── SDK hook functions
        └── Session execution (async)
```

## Target Structure

```
executors/claude-agent-sdk/
├── ao-claude-code-exec       # Entry point (minimal, ~100 lines)
└── lib/
    ├── __init__.py
    ├── cli.py                # CLI handling, help text
    ├── executor.py           # Main executor logic (start/resume)
    ├── sdk_client.py         # Claude SDK wrapper (async session)
    ├── session_events.py     # Session binding and event emission
    ├── output_schema.py      # JSON schema validation & retry
    └── mcp_transform.py      # MCP server format transformation
```

## Refactoring Strategy

Each step runs the full integration test suite to verify no regression.

### Step 1: Baseline Verification
- [ ] Run tests against copied executor
- [ ] Verify all 49 tests pass
- [ ] Document any failures

### Step 2: Use SDK Native Structured Outputs
**Key simplification**: Replace ~100 lines of custom output schema handling with SDK's built-in support.

Current (custom):
```python
# Enrich system prompt with schema instructions
# Extract JSON from response text manually
# Validate using jsonschema
# Retry manually if validation fails
```

New (SDK native):
```python
options = ClaudeAgentOptions(
    output_format={"type": "json_schema", "schema": output_schema}
)
# Access: message.structured_output
```

- [ ] Remove: `OutputSchemaValidationError`, `ValidationResult`, `validate_against_schema`
- [ ] Remove: `extract_json_from_response`, `enrich_system_prompt_with_output_schema`
- [ ] Remove: `build_validation_error_prompt`, manual retry loop
- [ ] Add `output_format` to `ClaudeAgentOptions`
- [ ] Use `message.structured_output` in result handling
- [ ] Run tests

### Step 3: Extract MCP Transform Module
- [ ] Create `lib/mcp_transform.py`
- [ ] Move: `transform_mcp_servers_for_claude_code`
- [ ] Update imports
- [ ] Run tests

### Step 4: Extract Executor Config Module
- [ ] Create `lib/executor_config.py` (local, not shared)
- [ ] Move: `ClaudeConfigKey`, `EXECUTOR_CONFIG_DEFAULTS`, `get_claude_config`
- [ ] Update imports
- [ ] Run tests

### Step 5: Extract Session Events Module
- [ ] Create `lib/session_events.py`
- [ ] Move: Hook context management, `post_tool_hook`, event emission logic
- [ ] Update imports
- [ ] Run tests

### Step 6: Simplify SDK Client
- [ ] Rename `claude_client.py` to `sdk_client.py`
- [ ] Clean up after extractions
- [ ] Ensure only SDK interaction remains
- [ ] Run tests

### Step 7: Refactor Entry Point
- [ ] Extract CLI handling to `lib/cli.py`
- [ ] Simplify `ao-claude-code-exec` to minimal dispatch
- [ ] Run tests

### Step 8: Final Cleanup
- [ ] Review all modules for consistency
- [ ] Add missing type hints
- [ ] Final test run
- [ ] Update CHANGELOG

## Testing Command

```bash
cd servers/agent-runner

# Test the new executor
EXECUTOR_UNDER_TEST=executors/claude-agent-sdk/ao-claude-code-exec \
  uv run --with pytest pytest tests/integration/ -v

# Compare with original (should both pass)
EXECUTOR_UNDER_TEST=executors/claude-code/ao-claude-code-exec \
  uv run --with pytest pytest tests/integration/ -v
```

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-05 | Copy executor to `claude-agent-sdk/` | Parallel development, test both versions |
| 2026-02-05 | Step-by-step extraction | Minimize risk, verify after each change |

## Related

- [Executor Integration Testing](../executor-integration-testing/README.md) - Test infrastructure
- [CHANGELOG](../../../servers/agent-runner/executors/claude-agent-sdk/CHANGELOG.md) - Detailed change log
