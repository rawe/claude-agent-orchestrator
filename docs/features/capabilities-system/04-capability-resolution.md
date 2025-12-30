# Work Package 4: Capability Resolution & Merging

**Parent Feature:** [Capabilities System](../capabilities-system.md)
**Depends On:** [01-capability-storage](./01-capability-storage.md), [03-agent-capabilities-field](./03-agent-capabilities-field.md)
**Status:** Complete

## Goal

Implement the core logic that resolves and merges capabilities when loading an agent.

## Scope

- Capability resolution when `GET /agents/{name}` is called
- System prompt merging (agent prompt + capability texts in declaration order)
- MCP servers merging (capabilities + agent-level)
- Conflict detection (error on duplicate MCP server names)
- Missing capability validation (error if referenced capability doesn't exist)

## Key Decisions

- Separator between prompt sections: `\n\n---\n\n`
- MCP server name conflicts: raise error (no silent override)
- Missing capability: raise error (agent fails to load)
- Resolution happens at read time, not write time
- `GET /agents/{name}` returns resolved agent by default
- `GET /agents/{name}?raw=true` returns unresolved agent (for dashboard editing)

## Implementation

### Files Modified

1. **`servers/agent-coordinator/agent_storage.py`** - Added capability resolution:
   - `CAPABILITY_SEPARATOR` - Constant `"\n\n---\n\n"` for joining prompts
   - `CapabilityResolutionError` - Base exception class
   - `MissingCapabilityError` - Raised when capability doesn't exist
   - `MCPServerConflictError` - Raised on duplicate MCP server names
   - `_resolve_agent_capabilities(agent)` - Core resolution logic
   - Updated `get_agent(name, resolve=True)` - Resolves by default, `resolve=False` for raw

2. **`servers/agent-coordinator/main.py`** - Updated API endpoint:
   - `GET /agents/{name}` now accepts `?raw=true` query parameter
   - Returns 422 Unprocessable Entity on resolution errors

### Resolution Logic

```python
def _resolve_agent_capabilities(agent: Agent) -> Agent:
    # 1. Start with agent's system_prompt
    # 2. For each capability in order:
    #    - Error if capability doesn't exist
    #    - Append capability.text to system_prompt parts
    #    - Merge capability.mcp_servers (error on name conflict)
    # 3. Add agent-level mcp_servers last (error on name conflict)
    # 4. Return Agent with merged values
```

### API Behavior

| Request | Response |
|---------|----------|
| `GET /agents/my-agent` | Resolved agent with merged system_prompt and mcp_servers |
| `GET /agents/my-agent?raw=true` | Raw agent with original system_prompt, mcp_servers, and capabilities list |
| Missing capability | 422 with "Capability resolution failed: {name} not found" |
| MCP server conflict | 422 with "MCP server name conflict: '{name}' defined in {sources}" |

## Acceptance

- [x] Agent API returns merged system_prompt and mcp_servers
- [x] Capability texts appended in declaration order
- [x] Error raised on MCP server name conflict
- [x] Error raised on missing capability reference
- [x] Existing agents without capabilities unchanged
- [x] `?raw=true` parameter for dashboard compatibility
