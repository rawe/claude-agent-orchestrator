# Work Package 4: Capability Resolution & Merging

**Parent Feature:** [Capabilities System](../capabilities-system.md)
**Depends On:** [01-capability-storage](./01-capability-storage.md), [03-agent-capabilities-field](./03-agent-capabilities-field.md)

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

## Starting Points

- `servers/agent-coordinator/agent_storage.py` - `get_agent()` function
- Feature doc merging rules section

## Acceptance

- Agent API returns merged system_prompt and mcp_servers
- Capability texts appended in declaration order
- Error raised on MCP server name conflict
- Error raised on missing capability reference
- Existing agents without capabilities unchanged
