# ADR-018: Centralized Placeholder Resolution

**Status:** Accepted
**Date:** 2026-01-27
**Decision Makers:** Architecture Review

## Context

MCP server configurations require dynamic values at runtime—session IDs, API keys, scoping parameters. These values come from different sources: agent input parameters, run-scoped context, environment variables, and framework runtime context.

Resolution must happen somewhere. The options are:
1. Coordinator (centralized, at run creation)
2. Runner (distributed, at execution time)
3. Both (split responsibilities)

## Decision

Centralize placeholder resolution at the Coordinator level with a unified placeholder syntax. The Runner resolves only the single placeholder it must handle.

### Placeholder Sources

| Source | Syntax | Resolved By | Description |
|--------|--------|-------------|-------------|
| `params` | `${params.X}` | Coordinator | Agent input parameters |
| `scope` | `${scope.X}` | Coordinator | Run scope (LLM-invisible values) |
| `env` | `${env.X}` | Coordinator | Coordinator's environment variables |
| `runtime` | `${runtime.X}` | Coordinator | Framework context (session_id, run_id) |
| `runner` | `${runner.X}` | **Runner** | Runner-specific values |

### Resolution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Coordinator (run creation)                                      │
│                                                                  │
│  1. Load agent blueprint                                         │
│  2. Resolve ${params.*}, ${scope.*}, ${env.*}, ${runtime.*}      │
│  3. Preserve ${runner.*} placeholders (for Runner)               │
│  4. Validate required values present                             │
│  5. Store resolved blueprint in run                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Run payload includes resolved_agent_blueprint
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Runner (execution)                                              │
│                                                                  │
│  1. Receive run with pre-resolved blueprint                      │
│  2. Resolve ONLY ${runner.orchestrator_mcp_url}                  │
│  3. Pass to executor                                             │
└─────────────────────────────────────────────────────────────────┘
```

### The `runner` Exception

The `${runner.orchestrator_mcp_url}` placeholder cannot be resolved at Coordinator because only the Runner knows the dynamic port of its embedded Orchestrator MCP server. The `runner.` prefix signals this is NOT resolved by Coordinator.

## Rationale

### Why Centralize at Coordinator?

1. **Immediate validation** - Missing required values fail at run creation with clear error to caller
2. **No additional API calls** - Runner receives self-contained run payload
3. **Centralized secrets** - Environment variables read from Coordinator, not Runner
4. **Simplified Runner** - Only resolves the one placeholder it must handle

### Why Not Full Centralization?

The Orchestrator MCP server is embedded in the Runner and uses a dynamic port. The Coordinator cannot know this port, so `${runner.orchestrator_mcp_url}` must remain Runner-resolved.

### Alternatives Considered

**Alternative 1: Resolution at Runner**
- Rejected: Requires additional API calls, delayed validation, secrets distributed to Runners

**Alternative 2: Fully centralize (no exceptions)**
- Rejected: Orchestrator MCP dynamic port unknown to Coordinator

**Alternative 3: Different placeholder syntax for Runner**
- Rejected: Consistent `${source.key}` syntax is clearer; `runner.` prefix distinguishes sufficiently

## Consequences

### Positive

- Run creation fails fast on missing required values
- Runner is simpler (no additional API calls for blueprint)
- Secrets stay on Coordinator (not distributed to Runners)
- Single location for placeholder resolution logic

### Negative

- Two-phase resolution (Coordinator + Runner) adds complexity
- `${runner.*}` is a special case developers must understand

### Neutral

- Run payload includes resolved blueprint (larger payload)

## References

- [ADR-005: Parent Session Context Propagation](./ADR-005-parent-session-context-propagation.md)
