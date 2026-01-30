# MCP Resolution at Coordinator - Implementation Report

## Summary

This report documents the implementation of the MCP Resolution at Coordinator feature.

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
- `servers/agent-runner/agent-runner`

**Files Deleted:**
- `servers/agent-runner/lib/blueprint_resolver.py`

**Changes:**
- Extended `Run` dataclass with `scope` and `resolved_agent_blueprint` fields
- Added `_resolve_runner_placeholders()` method to executor for `${runner.*}` resolution
- Modified `_build_payload()` to use resolved blueprint from run
- Removed `blueprint_resolver` parameter and fallback from executor
- Removed `BlueprintResolver` class entirely (no longer needed)
- Removed `_process_mcp_servers()` function from Claude Code executor (no longer needed)
- Removed `blueprint_resolver` usage from agent-runner main script

### 5. Scope Inheritance for Child Runs

**Files Modified:**
- `servers/agent-coordinator/main.py`

**Changes (commit 026dab2):**
- When a run has `parent_session_id`, look up the parent run's scope
- Merge parent scope as defaults, child scope overrides
- Store merged scope for grandchild inheritance

**Merge Semantics:**
```python
# Parent scope provides defaults, child scope overrides
effective_scope = {**parent_scope, **(run_create.scope or {})}
```

**Example:**
```
Parent Run: scope = {context_id: "ctx-123", tenant: "acme"}
Child Run:  scope = {tenant: "other"}  # overrides tenant
Result:     scope = {context_id: "ctx-123", tenant: "other"}
```

### 6. Tests

**Files Created:**
- `servers/agent-coordinator/tests/test_placeholder_resolver.py` (14 tests)

**Test Coverage:**
- Params, scope, env, runtime placeholder resolution
- Runner placeholder preservation
- Nested structure handling
- Multiple placeholders in single string
- Mixed sources in same blueprint
- Original blueprint mutation protection

## What Was NOT Implemented

### 1. Validation of Required Config

The design specified a `validate_required_config()` function to fail fast at run creation if required placeholder values are missing.

**Reason:** Depends on Phase 2 (MCP Server Registry). Validation requires knowing which config values are required, which is defined by the `config_schema` in the registry. Without the registry, there's no way to know which values are mandatory.

This will be implemented in Phase 2 as part of the registry reference resolution.

### 3. MCP Server Registry

The design document described a full MCP Server Registry with named server templates, compositions, and version management.

**Reason:** The core requirement was placeholder resolution. The registry pattern adds complexity that can be added later if needed.

### 4. Additional Placeholder Sources

Future sources like `${webhook.X}` and `${secret.X}` were not implemented.

**Reason:** These require additional infrastructure.

## Problems Encountered and Solutions

### 1. Run ID Generation Timing

**Problem:** The `${runtime.run_id}` placeholder requires the run_id, but run_id was generated inside `add_run()`.

**Solution:** Added `generate_run_id()` function and modified `add_run()` to accept an optional pre-generated run_id.

## Testing Instructions

```bash
# Run Coordinator tests
cd servers/agent-coordinator && uv run --with pytest pytest tests/test_placeholder_resolver.py -v

# Run Runner tests
cd servers/agent-runner && uv run --with pytest --with httpx -- python -m pytest tests/ -v
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
| `servers/agent-runner/lib/blueprint_resolver.py` | Deleted |
| `servers/agent-runner/executors/claude-code/lib/claude_client.py` | Modified |
| `servers/agent-runner/agent-runner` | Modified |

## Phase 1 Status

**Phase 1 is COMPLETE.** All planned features have been implemented:

1. ✅ PlaceholderResolver service
2. ✅ Run model extension with scope and resolved_agent_blueprint
3. ✅ Coordinator resolves blueprint before storing run
4. ✅ Runner uses resolved blueprint, only resolves `${runner.*}`
5. ✅ Scope inheritance for child runs

**Deferred to Phase 2:**
- Validation of required config (requires `config_schema` from registry)
