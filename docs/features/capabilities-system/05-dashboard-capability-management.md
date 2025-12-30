# Work Package 5: Dashboard Capability Management

**Status:** Complete
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

## Implementation

### Files Created

- `dashboard/src/types/capability.ts` - TypeScript types (Capability, CapabilitySummary, CapabilityCreate, CapabilityUpdate)
- `dashboard/src/services/capabilityService.ts` - API service for CRUD operations
- `dashboard/src/hooks/useCapabilities.ts` - React hook for capability state management
- `dashboard/src/components/features/capabilities/CapabilityTable.tsx` - List view with search
- `dashboard/src/components/features/capabilities/CapabilityEditor.tsx` - Create/edit modal with markdown preview
- `dashboard/src/pages/Capabilities.tsx` - Main capabilities management page

### Files Modified

- `dashboard/src/router.tsx` - Added `/capabilities` route
- `dashboard/src/pages/index.ts` - Export Capabilities page
- `dashboard/src/components/layout/Sidebar.tsx` - Added navigation item with Puzzle icon
- `dashboard/src/types/index.ts` - Export capability types
- `dashboard/src/services/index.ts` - Export capabilityService
- `dashboard/src/hooks/index.ts` - Export useCapabilities

## Acceptance

- [x] Can list, create, edit, delete capabilities from dashboard
- [x] Form validates required fields
- [x] MCP config editor works (JSON editor with quick-add templates)
