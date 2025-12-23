# Work Package 1: Blueprint Resolution & Schema 2.0 Integration

## Introduction

Move blueprint fetching and placeholder resolution from the executor to the Agent Runner. Implement Schema 2.0 which passes a fully resolved `agent_blueprint` to the executor instead of just `agent_name`. This enables the Runner to inject dynamic values (like MCP server URLs) before spawning executors.

**Reference:** `docs/architecture/mcp-runner-integration-mvp.md`

## What To Do

1. **Create `BlueprintResolver`** - See MVP section "BlueprintResolver (`lib/blueprint_resolver.py`)" (lines 454-498)
   - Fetches blueprint from Coordinator via `GET /agents/{name}`
   - Implements `resolve_placeholders()` per "Placeholder Resolution" section (lines 258-337)

2. **Update `ExecutorInvocation`** - See MVP section "ExecutorInvocation (`lib/invocation.py`)" (lines 569-583)
   - Add `agent_blueprint: Optional[dict]` field
   - Bump to `SCHEMA_VERSION = "2.0"`
   - Keep backward compat with schema 1.0

3. **Modify `RunExecutor`** - See MVP section "RunExecutor (`lib/executor.py`)" (lines 519-565)
   - Inject `BlueprintResolver` dependency
   - Fetch and resolve blueprint before spawning
   - Build schema 2.0 payload with `agent_blueprint`

4. **Update `ao-claude-code-exec`** - See MVP section "ao-claude-code-exec (Executor)" (lines 585-608)
   - If `agent_blueprint` present: use it directly (no Coordinator call)
   - If only `agent_name`: fall back to fetching (schema 1.0 compat)

## Files

| Action | Path |
|--------|------|
| CREATE | `servers/agent-runner/lib/blueprint_resolver.py` |
| MODIFY | `servers/agent-runner/lib/invocation.py` |
| MODIFY | `servers/agent-runner/lib/executor.py` |
| MODIFY | `servers/agent-runner/executors/claude-code/ao-claude-code-exec` |

## TODO Checklist

- [ ] Implement `BlueprintResolver` class with `resolve()` and `resolve_placeholders()` methods
- [ ] Add placeholder resolution for `${AGENT_ORCHESTRATOR_MCP_URL}` and `${AGENT_SESSION_ID}`
- [ ] Update `ExecutorInvocation` dataclass with `agent_blueprint` field and schema 2.0
- [ ] Add schema version detection (support both 1.0 and 2.0)
- [ ] Modify `RunExecutor.__init__` to accept `blueprint_resolver` and `mcp_server_url`
- [ ] Modify `RunExecutor.execute_run` to resolve blueprint before spawning
- [ ] Update executor to use `agent_blueprint` directly when present
- [ ] Maintain backward compatibility with schema 1.0 in executor

## Testing Checklist

- [ ] Unit: `resolve_placeholders()` correctly replaces `${AGENT_ORCHESTRATOR_MCP_URL}` in nested mcp_servers config
- [ ] Unit: `resolve_placeholders()` correctly replaces `${AGENT_SESSION_ID}` in headers
- [ ] Unit: Placeholders without matching values pass through unchanged
- [ ] Unit: `ExecutorInvocation` parses schema 2.0 with `agent_blueprint`
- [ ] Unit: `ExecutorInvocation` parses schema 1.0 with `agent_name` (backward compat)
- [ ] Integration: Run with blueprint containing placeholders -> executor receives resolved URLs
- [ ] Integration: Executor uses `agent_blueprint` directly without Coordinator API call
- [ ] Integration: All existing integration tests pass (use standalone MCP server URL for now)

## Documentation Updates

Update the following documentation to reflect Schema 2.0 changes:

| File | What to Update |
|------|----------------|
| `servers/agent-runner/executors/README.md` | Update invocation schema example (lines 40-52): change `schema_version` to `"2.0"`, add `agent_blueprint` object, mark `agent_name` as deprecated |
| `servers/agent-runner/README.md` | Update "Run Types" section (lines 125-131): add `agent_blueprint` parameter, note that blueprint resolution now happens in Runner |
| `docs/agent-coordinator/RUN_EXECUTION_FLOW.md` | Update "Phase 3: Run Execution" (lines 136-166): document that Runner fetches and resolves blueprint before spawning executor |
