# MCP Resolution at Coordinator - Implementation Report

## Summary

This report documents the implementation of the MCP Resolution at Coordinator feature as specified in `docs/design/mcp-server-registry/mcp-resolution-at-coordinator.md`.

## What Was Implemented

### 1. Run Model Extension

**Files Modified:**
- `servers/agent-coordinator/services/run_queue.py`
- `servers/agent-coordinator/database.py`

**Changes:**
- Added `scope` field to `RunCreate` for LLM-invisible context
- Added `scope` and `resolved_agent_blueprint` fields to `Run` model
- Added database columns for persistence (with migration support)
- Updated `add_run()` to accept and store these new fields
- Added `generate_run_id()` function to generate run IDs early for placeholder resolution

### 2. PlaceholderResolver Service

**Files Created:**
- `servers/agent-coordinator/services/placeholder_resolver.py`

**Features:**
- Supports placeholder sources: `params`, `scope`, `env`, `runtime`
- Preserves `${runner.*}` placeholders (resolved at Runner level)
- Handles nested dicts and lists
- Non-mutating (returns new dict)

**Placeholder Format:**
- `${params.X}` - From run parameters
- `${scope.X}` - From run scope (LLM-invisible)
- `${env.X}` - From Coordinator environment variables
- `${runtime.session_id}` - Current session ID
- `${runtime.run_id}` - Current run ID
- `${runner.*}` - NOT resolved (passed to Runner)

### 3. Coordinator create_run() Update

**Files Modified:**
- `servers/agent-coordinator/main.py`

**Changes:**
- Generate run_id early (before blueprint resolution)
- Create PlaceholderResolver with context from request
- Resolve agent blueprint before storing run
- Pass resolved blueprint to `run_queue.add_run()`

### 4. Runner/Executor Updates

**Files Modified:**
- `servers/agent-runner/lib/api_client.py`
- `servers/agent-runner/lib/executor.py`
- `servers/agent-runner/executors/claude-code/lib/claude_client.py`

**Changes:**
- Extended `Run` dataclass with `scope` and `resolved_agent_blueprint`
- Added `_resolve_runner_placeholders()` method to executor
- Modified `_build_payload()` to use resolved blueprint from run
- Falls back to blueprint_resolver for backward compatibility
- Claude Code executor's `_process_mcp_servers()` updated with comments about new flow

### 5. Tests

**Files Created:**
- `servers/agent-coordinator/tests/test_placeholder_resolver.py` (14 tests)

**Files Modified:**
- `servers/agent-runner/tests/test_executor.py` (added 7 tests, fixed existing tests)
- `servers/agent-runner/pyproject.toml` (created for test dependencies)

**Test Coverage:**
- Params, scope, env, runtime placeholder resolution
- Runner placeholder preservation
- Nested structure handling
- Multiple placeholders in single string
- Mixed sources in same blueprint
- Original blueprint mutation protection
- Runner placeholder resolution at executor level

## What Was NOT Implemented

### 1. MCP Server Registry

The design document described a full MCP Server Registry with:
- Named server templates stored in the registry
- Server compositions (referencing templates by name)
- Version management

**Reason:** The core requirement was placeholder resolution, which was implemented. The registry pattern adds complexity that can be added later if needed.

### 2. Additional Placeholder Sources

The design mentioned potential future sources like:
- `${webhook.X}` - External webhook data
- `${secret.X}` - Secret manager integration

**Reason:** These require additional infrastructure and were marked as future work.

### 3. Validation and Error Handling

Limited validation for:
- Unresolved placeholders (kept as-is, no warning)
- Circular placeholder references
- Placeholder syntax errors

**Reason:** The simple approach of keeping unresolved placeholders as-is allows for gradual adoption and debugging.

### 4. UI Integration

The design mentioned dashboard support for:
- Viewing scope values
- Debugging placeholder resolution

**Reason:** This requires frontend changes and can be added incrementally.

## Problems Encountered and Solutions

### 1. Run ID Generation Timing

**Problem:** The `${runtime.run_id}` placeholder requires the run_id, but run_id was generated inside `add_run()`.

**Solution:** Added `generate_run_id()` function and modified `add_run()` to accept an optional pre-generated run_id.

### 2. Test Environment Dependencies

**Problem:** Runner tests couldn't find `httpx` module because no `pyproject.toml` existed for agent-runner.

**Solution:** Created `pyproject.toml` for agent-runner with httpx and pytest dependencies.

### 3. Executor Path in Tests

**Problem:** Test fixtures created a "test-exec" file but the executor expected the default path structure.

**Solution:** Fixed test fixtures to create executors at the correct path.

## Backward Compatibility

The implementation maintains full backward compatibility:

1. **No `scope` provided:** Runs work exactly as before
2. **No `resolved_agent_blueprint`:** Executor falls back to blueprint_resolver
3. **Legacy placeholders:** `${VAR_NAME}` still resolved by Claude Code executor

## Testing Instructions

```bash
# Run Coordinator tests
cd servers/agent-coordinator && uv run pytest tests/test_placeholder_resolver.py -v

# Run Runner tests
cd servers/agent-runner && uv sync && uv run python -m pytest tests/test_executor.py -v
```

## Files Changed Summary

| File | Change Type |
|------|------------|
| `servers/agent-coordinator/services/run_queue.py` | Modified |
| `servers/agent-coordinator/services/placeholder_resolver.py` | Created |
| `servers/agent-coordinator/database.py` | Modified |
| `servers/agent-coordinator/main.py` | Modified |
| `servers/agent-coordinator/tests/test_placeholder_resolver.py` | Created |
| `servers/agent-runner/lib/api_client.py` | Modified |
| `servers/agent-runner/lib/executor.py` | Modified |
| `servers/agent-runner/executors/claude-code/lib/claude_client.py` | Modified |
| `servers/agent-runner/tests/test_executor.py` | Modified |
| `servers/agent-runner/pyproject.toml` | Created |
