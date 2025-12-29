# Work Package 3: Agent Capabilities Field

**Parent Feature:** [Capabilities System](../capabilities-system.md)
**Depends On:** [01-capability-storage](./01-capability-storage.md)

## Goal

Extend the agent model to support capability references.

## Scope

- Add `capabilities: list[str]` field to Agent model
- Update agent storage to read/write capabilities from `agent.json`
- Update agent API to accept capabilities on create/update

## Key Decisions

- Field is optional, defaults to empty list
- Stored in `agent.json` alongside other metadata
- No validation of capability existence at this stage (that's in WP4)

## Starting Points

- `servers/agent-coordinator/models.py` - Agent model
- `servers/agent-coordinator/agent_storage.py` - agent.json handling

## Acceptance

- Agents can have `capabilities` array in `agent.json`
- API accepts and returns capabilities field
- Existing agents without capabilities continue to work
