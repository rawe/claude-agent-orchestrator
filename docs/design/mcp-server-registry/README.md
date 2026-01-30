# MCP Server Registry - Design Documents

## Context

This design introduces centralized MCP server configuration management with dynamic placeholder resolution. It solves the problem of scattered MCP configurations, enables run-scoped access control, and provides LLM-invisible parameters for security-sensitive values.

## Key Decisions

1. **Centralized Registry** - MCP server URLs and schemas defined once, referenced by name
2. **Placeholder System** - Five sources: `${params.X}`, `${scope.X}`, `${env.X}`, `${runtime.X}`, `${runner.X}`
3. **Run Scope** - LLM-invisible values inherited by child runs (for context_id, workflow_id, credentials)
4. **Coordinator Resolution** - All placeholders resolved at Coordinator level, except `${runner.*}`
5. **Runner Exception** - Only `${runner.orchestrator_mcp_url}` resolved at Runner (dynamic port)
6. **Resolved Blueprint in Payload** - Runner receives fully resolved agent blueprint, no additional API calls
7. **Immediate Validation** - Missing required values fail at run creation with clear error to caller

## Implementation Order

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: MCP Resolution at Coordinator (PREREQUISITE)          │
│  Document: mcp-resolution-at-coordinator.md                     │
│                                                                 │
│  - Extend Run model with scope and resolved_agent_blueprint     │
│  - Add PlaceholderResolver at Coordinator                       │
│  - Include resolved blueprint in run payload                    │
│  - Simplify Runner (remove BlueprintResolver)                   │
│  - Runner only resolves ${runner.*} placeholders                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2: MCP Server Registry (MAIN FEATURE)                    │
│  Document: mcp-server-registry.md                               │
│                                                                 │
│  - Registry CRUD API and database table                         │
│  - Config schema validation                                     │
│  - Reference syntax in capabilities/agents (ref + config)       │
│  - Config inheritance chain (Registry → Capability → Agent)     │
│  - Dashboard integration                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Phase 1 MUST be completed before Phase 2.** The registry depends on Coordinator-level resolution.

## Documents

| Document | Purpose |
|----------|---------|
| [mcp-resolution-at-coordinator.md](mcp-resolution-at-coordinator.md) | **READ FIRST** - Prerequisite architectural change |
| [mcp-server-registry.md](mcp-server-registry.md) | Main feature design |
| [mcp-resolution-at-coordinator-report.md](mcp-resolution-at-coordinator-report.md) | Implementation report for Phase 1 |

## Implementation Status

### Phase 1: MCP Resolution at Coordinator ✅ Partially Complete

See [mcp-resolution-at-coordinator-report.md](mcp-resolution-at-coordinator-report.md) for details.

**Completed:**
- PlaceholderResolver service with `params`, `scope`, `env`, `runtime` sources
- `${runner.*}` placeholder preservation for Runner-level resolution
- Run model extended with `scope` and `resolved_agent_blueprint`
- Coordinator resolves blueprint before storing run
- Runner uses resolved blueprint, resolves only `${runner.orchestrator_mcp_url}`
- BlueprintResolver removed from Runner (no backwards compatibility fallback)
- `_process_mcp_servers()` removed from Claude Code executor

**Not Yet Implemented:**
- Scope inheritance for child runs
- Validation of required config values at run creation

### Phase 2: MCP Server Registry ❌ Not Started

Waiting for Phase 1 completion.

## Quick Reference

### Placeholder Sources

| Source | Resolved By | Example |
|--------|-------------|---------|
| `params` | Coordinator | `${params.task_id}` - from agent input schema |
| `scope` | Coordinator | `${scope.context_id}` - LLM-invisible, inherited by children |
| `env` | Coordinator | `${env.API_KEY}` - from Coordinator environment |
| `runtime` | Coordinator | `${runtime.run_id}` - framework context |
| `runner` | Runner | `${runner.orchestrator_mcp_url}` - Runner-specific |

### Run Payload (After Phase 1)

```json
{
  "run_id": "run_abc",
  "session_id": "ses_xyz",
  "agent_name": "my-agent",
  "parameters": {"prompt": "..."},
  "scope": {"context_id": "ctx-123"},
  "resolved_agent_blueprint": {
    "name": "my-agent",
    "system_prompt": "...",
    "mcp_servers": {
      "context-store": {
        "url": "http://localhost:9501/mcp",
        "config": {"context_id": "ctx-123"}
      }
    }
  }
}
```

### Scope Inheritance

```
Parent Run (scope: {context_id: "ctx-123"})
    │
    └── spawns child via Orchestrator MCP
            │
            ▼
        Child Run (inherits scope: {context_id: "ctx-123"})
```

## Starting Implementation

1. Read [mcp-resolution-at-coordinator.md](mcp-resolution-at-coordinator.md) completely
2. Implement Phase 1 changes (see "Changes Required" section)
3. Test that resolved blueprint appears in run payload
4. Then proceed to [mcp-server-registry.md](mcp-server-registry.md) for Phase 2
