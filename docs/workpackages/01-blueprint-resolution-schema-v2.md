# Work Package 1: Blueprint Resolution & Schema 2.0 Integration

**Status: DONE**

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
   - Executor no longer fetches blueprints from Coordinator API

## Files

| Action | Path |
|--------|------|
| CREATE | `servers/agent-runner/lib/blueprint_resolver.py` |
| MODIFY | `servers/agent-runner/lib/invocation.py` |
| MODIFY | `servers/agent-runner/lib/executor.py` |
| MODIFY | `servers/agent-runner/executors/claude-code/ao-claude-code-exec` |

## TODO Checklist

- [x] Implement `BlueprintResolver` class with `resolve()` and `resolve_placeholders()` methods
- [x] Add placeholder resolution for `${AGENT_ORCHESTRATOR_MCP_URL}` and `${AGENT_SESSION_ID}`
- [x] Update `ExecutorInvocation` dataclass with `agent_blueprint` field and schema 2.0
- [x] Add schema version detection (support both 1.0 and 2.0)
- [x] Modify `RunExecutor.__init__` to accept `blueprint_resolver` and `mcp_server_url`
- [x] Modify `RunExecutor.execute_run` to resolve blueprint before spawning
- [x] Update executor to use `agent_blueprint` directly when present
- [x] Wire up `BlueprintResolver` in agent-runner main script

## Testing Checklist

- [x] Integration: Run with blueprint containing placeholders -> executor receives resolved URLs
- [x] Integration: Executor uses `agent_blueprint` directly without Coordinator API call
- [x] Integration: All existing integration tests pass

## Documentation Updates

- [x] `servers/agent-runner/executors/README.md` - Updated invocation schema to 2.0
- [x] `servers/agent-runner/README.md` - Updated "Run Types" section with `agent_blueprint`
- [x] `docs/agent-coordinator/RUN_EXECUTION_FLOW.md` - Updated "Phase 3: Run Execution" with blueprint resolution details
