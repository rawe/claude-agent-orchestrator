# Work Package 6: Dashboard Agent Capability Selection

**Parent Feature:** [Capabilities System](../capabilities-system.md)
**Depends On:** [04-capability-resolution](./04-capability-resolution.md), [05-dashboard-capability-management](./05-dashboard-capability-management.md)

## Goal

Update agent edit form to allow selecting capabilities.

## Scope

- Multi-select dropdown for capabilities in agent form
- Display selected capabilities as chips/tags
- Show merged preview (optional enhancement)

## Key Decisions

- Capabilities shown in multi-select dropdown
- Order determined by selection order (or alphabetical for simplicity)
- Selected capabilities saved to agent on form submit

## Starting Points

- `dashboard/src/pages/AgentEditPage.tsx` - agent edit form
- `dashboard/src/components/` - for existing form components

## Acceptance

- Agent edit form has capabilities multi-select
- Selected capabilities saved and persisted
- Agent loads correctly with capabilities merged
