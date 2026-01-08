# Phase 1: Unified Input Model

**Status:** Implementation Ready
**Depends on:** None (foundation phase)
**Design Reference:** [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Section 2 (Unified Invocation Model)

---

## Objective

Migrate from `prompt: str` to `parameters: dict` across the API, MCP tools, and executor invocation. AI agents continue working with backward-compatible `prompt` sugar.

**End state:** All agents are invoked with `parameters`. For AI agents, `parameters={"prompt": "..."}`. The `prompt` shorthand remains for convenience.

---

## Key Changes

### 1. Coordinator API

**File:** `servers/agent-coordinator/services/run_queue.py`
- `RunCreate` model (lines 63-77): Replace `prompt: str` with `parameters: dict`
- Add `prompt` as optional sugar that converts to `{"prompt": "..."}`
- Validation: Either `parameters` or `prompt` must be provided, not both

**File:** `servers/agent-coordinator/main.py`
- `create_run()` endpoint (lines 1335-1450): Handle both `parameters` and `prompt` sugar
- Normalize to `parameters` before storing

### 2. MCP Tools

**File:** `servers/agent-runner/lib/agent_orchestrator_mcp/tools.py`
- `start_agent_session()` (lines 112-211): Change signature from `prompt: str` to `parameters: dict`
- Keep `prompt: str` as optional sugar parameter
- Update tool description to explain unified model
- `resume_agent_session()` (lines 213-309): Same changes

**File:** `servers/agent-runner/lib/agent_orchestrator_mcp/server.py`
- Tool registrations (lines 119-151): Update parameter handling

### 3. Executor Invocation Schema

**File:** `servers/agent-runner/lib/invocation.py`
- `INVOCATION_SCHEMA` (lines 30-90): Replace `prompt` with `parameters` in schema
- Bump `SCHEMA_VERSION` to "2.2"
- `ExecutorInvocation` dataclass (lines 93-119): Change `prompt: str` to `parameters: dict`
- Add helper property `prompt` that extracts `parameters.get("prompt")`

### 4. Claude-Code Executor

**File:** `servers/agent-runner/executors/claude-code/ao-claude-code-exec`
- `run_start()` (lines 177-237): Extract prompt from `inv.parameters["prompt"]`
- `run_resume()` (lines 240-333): Same extraction

**File:** `servers/agent-runner/executors/claude-code/lib/claude_client.py`
- `run_claude_session()` (lines 195-389): No change needed (already receives prompt string)

---

## Backward Compatibility

The `prompt` sugar ensures zero breaking changes:

```python
# Old way (still works)
start_agent_session(agent_name="researcher", prompt="Research X")

# New way (preferred)
start_agent_session(agent_name="researcher", parameters={"prompt": "Research X"})
```

Coordinator normalizes `prompt` to `parameters={"prompt": ...}` before processing.

---

## Implicit Schema for AI Agents

AI agents without explicit `parameters_schema` use this implicit schema:

```json
{
  "type": "object",
  "required": ["prompt"],
  "properties": {
    "prompt": { "type": "string", "minLength": 1 }
  }
}
```

This is a convention, not stored anywhere. Phase 3 will use it for validation.

---

## Files to Modify

| File | Change |
|------|--------|
| `servers/agent-coordinator/services/run_queue.py` | `RunCreate.prompt` → `RunCreate.parameters` + sugar |
| `servers/agent-coordinator/main.py` | `create_run()` handles both, normalizes to parameters |
| `servers/agent-runner/lib/invocation.py` | Schema v2.2, `parameters` field, helper property |
| `servers/agent-runner/lib/agent_orchestrator_mcp/tools.py` | MCP tools use `parameters` + `prompt` sugar |
| `servers/agent-runner/executors/claude-code/ao-claude-code-exec` | Extract prompt from parameters dict |

---

## Acceptance Criteria

1. **API accepts parameters:**
   ```bash
   curl -X POST /runs -d '{"agent_name": "researcher", "parameters": {"prompt": "Test"}}'
   # Returns: 201 Created
   ```

2. **API accepts prompt sugar:**
   ```bash
   curl -X POST /runs -d '{"agent_name": "researcher", "prompt": "Test"}'
   # Returns: 201 Created (normalized to parameters internally)
   ```

3. **MCP tool works with both:**
   ```python
   # Both invocations work identically
   start_agent_session("researcher", parameters={"prompt": "Test"})
   start_agent_session("researcher", prompt="Test")
   ```

4. **Executor receives parameters:**
   - Invocation payload contains `parameters: {"prompt": "..."}` not `prompt: "..."`
   - Claude-code executor extracts prompt and executes successfully

5. **Existing tests pass:** All current AI agent tests continue working

---

## Testing Strategy

1. Unit test `RunCreate` model with both `prompt` and `parameters`
2. Integration test `create_run()` endpoint with both formats
3. Integration test MCP `start_agent_session` with both formats
4. End-to-end test: AI agent execution with `parameters={"prompt": "..."}`
5. Regression test: Existing AI agent workflows unchanged

---

## References

- [ADR-010](../adr/ADR-010-coordinator-generated-session-ids.md) - Session ID generation
- [deterministic-agents-implementation.md](./deterministic-agents-implementation.md) - Section 2
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System overview
