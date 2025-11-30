# Migration Index

## Goal

Transform the Agent Orchestrator Framework from its current organic structure into the clean, modular architecture defined in [ARCHITECTURE.md](./ARCHITECTURE.md).

## Core Strategy

**The system must work after every package.**

Each package is a self-contained change that:
- Moves or modifies specific components
- Updates all dependent references
- Leaves the system fully functional

No package leaves the system in a broken state. You can pause the migration at any package boundary.

---

## Target Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for:
- Terminology (Agent Blueprint, Agent, Agent Session, etc.)
- Component descriptions (Agent Runtime, Agent Registry, Context Store)
- Target project structure
- Component interactions and data flow

---

## Migration Packages

### Phase 1: Reorganization (Packages 01-08)

Structure changes only. No behavior changes. System works identically, just with cleaner organization.

| # | Package | Summary |
|---|---------|---------|
| 01 | [Context Store Server](./01-context-store-server.md) | Extract document server from plugin → `/servers/context-store/` |
| 02 | [Context Store Plugin](./02-context-store-plugin.md) | Rename document-sync plugin → `/plugins/context-store/` |
| 03 | [Agent Registry](./03-agent-registry.md) | Move agent backend → `/servers/agent-registry/` |
| 04 | [Agent Runtime](./04-agent-runtime.md) | Move observability backend → `/servers/agent-runtime/` |
| 05 | [Orchestrator Plugin](./05-orchestrator-plugin.md) | Rename agent-orchestrator plugin → `/plugins/orchestrator/` |
| 06 | [MCP Server](./06-mcp-server.md) | Move MCP server → `/interfaces/agent-orchestrator-mcp-server/` |
| 07 | [Dashboard](./07-dashboard.md) | Rename frontend → `/dashboard/` |
| 08 | [Cleanup](./08-cleanup.md) | Delete deprecated components, verify structure |

**After Phase 1:** Clean structure matching [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure), same functionality.

---

### Phase 2: New Functionality (Packages 09-10)

Add agent spawning to server, convert commands to thin HTTP clients.

| # | Package | Summary |
|---|---------|---------|
| 09 | [Agent Runtime Spawner](./09-agent-runtime-spawner.md) | Add Claude Agent SDK logic to Agent Runtime server |
| 10 | [Thin Client Commands](./10-thin-client-commands.md) | Convert ao-* commands to HTTP clients |

**After Phase 2:** Full target architecture - servers handle all logic, commands are thin clients.

---

## Execution Order

Packages must be executed in order (01 → 02 → ... → 10).

Dependencies:
- Package 02 depends on 01 (plugin references server)
- Package 04 depends on 03 (dashboard refs updated incrementally)
- Package 06 depends on 05 (MCP server references command paths)
- Package 10 depends on 09 (commands need server endpoints to exist)

---

## Progress Tracking

| Package | Status | Date |
|---------|--------|------|
| 01 - Context Store Server | ✅ Complete | 2025-11-30 |
| 02 - Context Store Plugin | ✅ Complete | 2025-11-30 |
| 03 - Agent Registry | ✅ Complete | 2025-11-30 |
| 04 - Agent Runtime | ✅ Complete | 2025-11-30 |
| 05 - Orchestrator Plugin | ✅ Complete | 2025-11-30 |
| 06 - MCP Server | ✅ Complete | 2025-11-30 |
| 07 - Dashboard | ✅ Complete | 2025-11-30 |
| 08 - Cleanup | ⬜ Not Started | |
| 09 - Agent Runtime Spawner | ⬜ Not Started | |
| 10 - Thin Client Commands | ⬜ Not Started | |

Status: ⬜ Not Started | 🟡 In Progress | ✅ Complete
