# Work Package 5: Dashboard Capability Management

**Parent Feature:** [Capabilities System](../capabilities-system.md)
**Depends On:** [02-capability-api](./02-capability-api.md)

## Goal

Add UI for managing capabilities in the dashboard.

## Scope

- Capability TypeScript types
- Capability service (`capabilityService.ts`)
- Capabilities list page
- Capability create/edit form
- Capability delete with confirmation

## Key Decisions

- New route: `/capabilities`
- Form fields: name, description, text (markdown editor), MCP servers (JSON editor)
- List shows: name, description, MCP server count

## Starting Points

- `dashboard/src/types/agent.ts` - for type patterns
- `dashboard/src/services/agentService.ts` - for service patterns
- `dashboard/src/pages/AgentListPage.tsx` - for list page patterns

## Acceptance

- Can list, create, edit, delete capabilities from dashboard
- Form validates required fields
- MCP config editor works (JSON or form-based)
