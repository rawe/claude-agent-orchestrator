# Agent Tags System - Implementation Report

**Date:** 2025-12-11
**Status:** Complete
**Branch:** `feat/agent-visibility` (refactored to tags)

## Summary

Replaced the binary `visibility` field (`public` | `internal` | `all`) with a flexible `tags` array system. This enables multi-dimensional agent filtering while maintaining backward compatibility with the existing external/internal distinction.

## Changes Overview

### Files Modified

| Layer | File | Changes |
|-------|------|---------|
| Backend | `servers/agent-runtime/models.py` | Replace `visibility` with `tags: list[str]` |
| Backend | `servers/agent-runtime/agent_storage.py` | Read/write `tags` from agent.json |
| Backend | `servers/agent-runtime/main.py` | Replace `?context=` with `?tags=` query param |
| MCP | `mcps/agent-orchestrator/libs/constants.py` | Replace visibility headers/env vars |
| MCP | `mcps/agent-orchestrator/libs/core_functions.py` | Replace `get_visibility_context` with `get_filter_tags` |
| MCP | `mcps/agent-orchestrator/libs/api_client.py` | Replace `context` param with `tags` |
| Skills | `ao-list-blueprints` | Replace `--context` with `--tags`, no default |
| Skills | `lib/agent_api.py` | Replace `context` with `tags` param |
| Dashboard | `types/agent.ts` | Replace `visibility` with `tags: string[]` |
| Dashboard | `services/agentService.ts` | Replace context with tags filtering |
| Dashboard | `services/chatService.ts` | Use `?tags=external` for chat |
| Dashboard | `utils/mcpTemplates.ts` | Update header to `X-Agent-Tags` |
| Dashboard | `pages/AgentManager.tsx` | Update to pass `tags` |
| Dashboard | `components/features/agents/AgentTable.tsx` | Replace visibility badge with tags display |
| Dashboard | `components/features/agents/AgentEditor.tsx` | Replace dropdown with TagSelector |
| Dashboard | `components/common/TagSelector.tsx` | **NEW** - Reusable tag input component |
| Dashboard | `components/common/index.ts` | Export TagSelector |

### Agent Configurations Migrated

All 15 agent configurations in `config/agents/*/agent.json` were updated:

| Agent | Old Visibility | New Tags |
|-------|---------------|----------|
| `agent-orchestrator` | `all` | `["external", "internal"]` |
| `agent-orchestrator-external` | `public` | `["external"]` |
| `agent-orchestrator-internal` | `internal` | `["internal"]` |
| `bug-evaluator` | `public` | `["external"]` |
| `ado-agent` | `internal` | `["internal"]` |
| `ado-researcher` | `internal` | `["internal", "research"]` |
| `atlassian-agent` | `internal` | `["internal", "atlassian"]` |
| `browser-tester` | `internal` | `["internal", "testing"]` |
| `confluence-researcher` | `internal` | `["internal", "research", "atlassian"]` |
| `context-store-agent` | `internal` | `["internal"]` |
| `jira-researcher` | `internal` | `["internal", "research", "atlassian"]` |
| `local-codebase-researcher` | `internal` | `["internal", "research"]` |
| `neo4j-agent` | `internal` | `["internal"]` |
| `simple-agent` | `internal` | `["internal"]` |
| `web-researcher` | `internal` | `["internal", "research"]` |

### Documentation Updated

| Document | Status |
|----------|--------|
| `docs/features/agent-management.md` | **NEW** - Comprehensive tags documentation |
| `docs/features/agent-visibility-architecture.md` | Marked as **DEPRECATED** |
| `docs/features/agent-visibility-refinement.md` | **DELETED** |
| `docs/features/agent-visibility-implementation-report.md` | **DELETED** |

## API Changes

### Before (Visibility)

```
GET /agents?context=external  → Agents with visibility in (public, all)
GET /agents?context=internal  → Agents with visibility in (internal, all)
GET /agents                   → All agents (management)
```

### After (Tags)

```
GET /agents?tags=external     → Agents with "external" tag
GET /agents?tags=internal     → Agents with "internal" tag
GET /agents?tags=internal,research → Agents with BOTH tags (AND logic)
GET /agents                   → All agents (management)
```

## Environment/Header Changes

| Before | After |
|--------|-------|
| `X-Agent-Visibility-Context` header | `X-Agent-Tags` header |
| `AGENT_VISIBILITY_CONTEXT` env var | `AGENT_TAGS` env var |

## Key Design Decisions

1. **AND Logic for Multiple Tags**: When filtering by `tags=a,b`, only agents with BOTH tags are returned. This enables precise filtering like "internal research agents for Atlassian".

2. **No Defaults in CLI**: The `ao-list-blueprints` command has no default `--tags` value. Users must explicitly specify tags or get all agents.

3. **Reserved Tags by Convention**: `external` and `internal` have special meaning but are not enforced. Custom tags like `research`, `atlassian`, `testing` can be freely added.

4. **Empty Tags = All Agents**: Agents without tags are visible to all queries. This maintains backward compatibility.

5. **New TagSelector Component**: Created a reusable component for the dashboard that supports:
   - Free-form tag input
   - Enter/comma to add tags
   - Backspace to remove
   - Click to remove individual tags

## Testing Checklist

- [ ] Backend API filtering with single tag
- [ ] Backend API filtering with multiple tags (AND logic)
- [ ] Dashboard Agent Manager displays tags
- [ ] Dashboard Agent Editor saves/loads tags
- [ ] Dashboard Chat page filters to external agents
- [ ] Skills `ao-list-blueprints` with various tag combinations
- [ ] MCP header passing works in HTTP mode
- [ ] Environment variable works in STDIO mode

## Migration Notes

Existing deployments using the old `visibility` field will need to:

1. Update agent configurations to use `tags` instead of `visibility`
2. Update any hardcoded `?context=` API calls to `?tags=`
3. Update MCP configurations to use `X-Agent-Tags` header
4. Update environment variables from `AGENT_VISIBILITY_CONTEXT` to `AGENT_TAGS`

The mapping is straightforward:
- `"visibility": "public"` → `"tags": ["external"]`
- `"visibility": "internal"` → `"tags": ["internal"]`
- `"visibility": "all"` → `"tags": ["external", "internal"]`
