# Session 1: Claude Code Executor

**Component:** `servers/agent-runner/executors/claude-code/`

## Objective

Make the Claude Code executor read `executor_config` from the invocation payload and apply it to `ClaudeAgentOptions`, with fallback to current hardcoded defaults.

## Prerequisites

None. This is the first session - the executor is a leaf node with no upstream dependencies.

## Files to Modify

| File | Change |
|------|--------|
| `servers/agent-runner/executors/claude-code/ao-claude-code-exec` | Read `executor_config`, apply to options |

## Current Hardcoded Values

The executor currently hardcodes these settings. They become the **defaults** when `executor_config` is missing or incomplete:

```python
# Current hardcoded values (search for these in the file)
permission_mode = "bypassPermissions"
setting_sources = ["user", "project", "local"]
model = None  # Uses SDK default
```

## Implementation

### 1. Update invocation parsing

The invocation payload will have an optional `executor_config` field:

```python
executor_config: Optional[dict[str, Any]] = None
```

If using a dataclass/model, add this field. If parsing raw JSON, handle the optional key.

### 2. Apply config with defaults

```python
def get_executor_config(invocation) -> dict:
    config = invocation.executor_config or {}
    return {
        "permission_mode": config.get("permission_mode", "bypassPermissions"),
        "setting_sources": config.get("setting_sources", ["user", "project", "local"]),
        "model": config.get("model"),  # None = SDK default
    }
```

### 3. Use in ClaudeAgentOptions

Replace hardcoded values with config values when building `ClaudeAgentOptions`.

## Design Doc References

- **Executor Config Handling**: `docs/design/executor-profiles.md` lines 179-192
- **Invocation Schema**: `docs/design/executor-profiles.md` lines 149-176

## Testing

Create a test invocation JSON and invoke the executor directly:

```bash
# Without config (should use defaults)
echo '{"schema_version":"2.1","mode":"start","session_id":"test","prompt":"hello"}' | \
  uv run --script servers/agent-runner/executors/claude-code/ao-claude-code-exec

# With config
echo '{"schema_version":"2.1","mode":"start","session_id":"test","prompt":"hello","executor_config":{"permission_mode":"default","model":"sonnet"}}' | \
  uv run --script servers/agent-runner/executors/claude-code/ao-claude-code-exec
```

Verify:
- Without `executor_config`: uses current behavior (bypassPermissions, all setting sources)
- With `executor_config`: applies the provided values
- Partial `executor_config`: uses provided values + defaults for missing keys

## Definition of Done

- [ ] Executor reads `executor_config` from invocation payload
- [ ] Missing `executor_config` = current hardcoded behavior (backward compatible)
- [ ] Partial config uses defaults for missing keys
- [ ] Unknown config keys are ignored (forward compatible)
- [ ] Tested with mock invocation payloads
