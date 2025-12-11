# Agent Visibility Architecture - Implementation Report

> **Date**: 2025-12-11

## Summary

Successfully implemented the two-level agent visibility system as specified in the [architecture document](./agent-visibility-architecture.md). The feature allows agents to be configured with `visibility` settings (`public`, `internal`, `all`) that control where they can be discovered.

## Changes Made

### Backend (servers/agent-runtime)

| File | Changes |
|------|---------|
| `models.py` | Added `visibility` field to `AgentCreate`, `AgentUpdate`, and `Agent` models. Type: `Literal["public", "internal", "all"]` with default `"all"` |
| `agent_storage.py` | Updated `_read_agent_from_dir()` to read visibility from agent.json, `create_agent()` to write visibility, and `update_agent()` to handle visibility updates |
| `main.py` | Extended `GET /agents` endpoint with `context` query parameter. Filtering: `external` → public+all, `internal` → internal+all, `None` → all agents |

### MCP Server (mcps/agent-orchestrator)

| File | Changes |
|------|---------|
| `libs/constants.py` | Added `HEADER_AGENT_VISIBILITY_CONTEXT` and `ENV_AGENT_VISIBILITY_CONTEXT` constants |
| `libs/core_functions.py` | Added `get_visibility_context()` function. Updated `list_agent_blueprints_impl()` to accept `http_headers` and filter by context |
| `libs/api_client.py` | Updated `list_agents()` to support optional `context` parameter |
| `libs/server.py` | Updated `list_agent_blueprints` tool to pass HTTP headers for context filtering |

### Skills (plugins/orchestrator)

| File | Changes |
|------|---------|
| `commands/ao-list-blueprints` | Added `--context` / `-c` flag (default: "internal"). Updated help text and examples |
| `commands/lib/agent_api.py` | Updated `list_agents_api()` to accept and use context parameter |

### Dashboard (dashboard/src)

| File | Changes |
|------|---------|
| `types/agent.ts` | Added `AgentVisibility` type, `visibility` field to interfaces, and `VISIBILITY_OPTIONS` constant |
| `services/agentService.ts` | Added `VisibilityContext` type. Updated `getAgents()` to support optional context parameter |
| `services/chatService.ts` | Updated `listBlueprints()` to use `context=external` filter |
| `components/features/agents/AgentTable.tsx` | Added `VisibilityBadge` component with icons. Added visibility column to the agent table |
| `components/features/agents/AgentEditor.tsx` | Added visibility field to form with dropdown selector and help text |
| `pages/AgentManager.tsx` | Updated `handleSaveAgent()` to include visibility in updates |
| `utils/mcpTemplates.ts` | Added `X-Agent-Visibility-Context` header to agent-orchestrator-http template |

### Documentation

| File | Changes |
|------|---------|
| `docs/features/agent-visibility-architecture.md` | Updated status from "DRAFT - Not yet implemented" to "IMPLEMENTED" |

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Default visibility: `"all"` | Backward compatibility - existing agents remain visible everywhere |
| Context filtering at API level | Clean separation - API handles filtering, consumers just specify context |
| External default for MCP | When no context specified, defaults to `"external"` (safe for Claude Desktop) |
| Internal default for skills | `ao-list-blueprints` defaults to `"internal"` (typical orchestrator use case) |

## Filtering Logic

```
┌─────────────────┬──────────────┬──────────────┬────────────────┐
│ visibility      │ context=     │ context=     │ context=       │
│                 │ external     │ internal     │ none (mgmt)    │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ public          │ Shown        │ Hidden       │ Shown          │
│ internal        │ Hidden       │ Shown        │ Shown          │
│ all             │ Shown        │ Shown        │ Shown          │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ + status filter │ active only  │ active only  │ all statuses   │
└─────────────────┴──────────────┴──────────────┴────────────────┘
```

## UI Changes

### Agent Manager Table
- New "Visibility" column with colored badges:
  - **Public** (blue, Globe icon): Entry-point agents for external clients
  - **Internal** (orange, Lock icon): Worker agents for orchestrator framework
  - **All** (green, Layers icon): Utility agents for both contexts

### Agent Editor
- New "Visibility" dropdown field with three options
- Help text explaining each visibility option

## Testing Recommendations

1. **Create agents with each visibility type** and verify they appear correctly in the Agent Manager
2. **Test Chat page** - should only show `public` and `all` visibility agents
3. **Test MCP tool** `list_agent_blueprints` - verify it respects the visibility context header
4. **Test skill** `ao-list-blueprints --context external` vs `ao-list-blueprints --context internal`
5. **Verify backward compatibility** - existing agents without `visibility` field should default to `"all"`

## Files Modified (Full List)

```
servers/agent-runtime/models.py
servers/agent-runtime/agent_storage.py
servers/agent-runtime/main.py
mcps/agent-orchestrator/libs/constants.py
mcps/agent-orchestrator/libs/core_functions.py
mcps/agent-orchestrator/libs/api_client.py
mcps/agent-orchestrator/libs/server.py
plugins/orchestrator/skills/orchestrator/commands/ao-list-blueprints
plugins/orchestrator/skills/orchestrator/commands/lib/agent_api.py
dashboard/src/types/agent.ts
dashboard/src/services/agentService.ts
dashboard/src/services/chatService.ts
dashboard/src/components/features/agents/AgentTable.tsx
dashboard/src/components/features/agents/AgentEditor.tsx
dashboard/src/pages/AgentManager.tsx
dashboard/src/utils/mcpTemplates.ts
docs/features/agent-visibility-architecture.md
```
