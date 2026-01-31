# ADR-019: MCP Server Registry

**Status:** Accepted
**Date:** 2026-01-27
**Decision Makers:** Architecture Review

## Context

MCP server configurations (URLs, authentication, scoping) need to be managed across multiple agents and capabilities. Without centralization:
- Same URL duplicated in multiple agent/capability configs
- URL changes require editing multiple files
- No schema documenting what configuration each server accepts
- No way to define defaults at registry level

## Decision

Introduce a centralized MCP Server Registry with config schemas and inheritance.

### Registry Entry

MCP servers are defined once in the registry with URL and config schema:

```json
{
  "id": "context-store",
  "name": "Context Store",
  "url": "http://localhost:9501/mcp",
  "config_schema": {
    "context_id": {"type": "string", "required": true},
    "workflow_id": {"type": "string", "required": false}
  },
  "default_config": {
    "context_id": "default"
  }
}
```

### Reference Syntax

Agents and capabilities reference registry entries by ID with config overrides:

```json
{
  "mcpServers": {
    "docs": {
      "ref": "context-store",
      "config": {
        "context_id": "${scope.context_id}"
      }
    }
  }
}
```

### Config Inheritance Chain

Configuration flows through an inheritance chain (later overrides earlier):

```
1. Registry defaults     {"context_id": "default"}
           │
           ▼
2. Capability config     {"context_id": "shared-context"}
           │
           ▼
3. Agent config          {"context_id": "${scope.context_id}"}
           │
           ▼
4. Placeholder resolution {"context_id": "ctx-123"}
```

### Config-to-Headers Mapping

Config keys map directly to HTTP headers. The executor transforms `config` to `headers` for the MCP client:

```
Registry/Agent format:   {"config": {"context_id": "ctx-123"}}
Claude Code format:      {"headers": {"context_id": "ctx-123"}}
```

## Rationale

### Why a Registry?

1. **Single source of truth** - URL defined once, referenced everywhere
2. **Config schemas** - UI can render forms based on schema
3. **Validation** - Required fields validated at run creation
4. **Environment separation** - Change URLs in one place for dev/prod

### Why Inheritance?

1. **Defaults** - Registry provides sensible defaults
2. **Capability context** - Capabilities can configure for their use case
3. **Agent overrides** - Agents can specialize further
4. **Explicit precedence** - Later levels always override earlier

### Why Config → Headers?

HTTP MCP servers receive configuration as HTTP headers (transport-level). Config keys map directly to header names, keeping the registry simple and transport-agnostic.

### Alternatives Considered

**Alternative 1: No registry, inline URLs**
- Rejected: Leads to duplication and inconsistency

**Alternative 2: Registry without inheritance**
- Rejected: Would require specifying all config at agent level

**Alternative 3: Complex merge strategies**
- Rejected: Simple "last wins" is predictable and sufficient

## Consequences

### Positive

- MCP server URLs defined once, easy to change
- Config schemas enable form generation
- Required config validated at run creation
- Clear inheritance chain reduces duplication

### Negative

- Additional indirection (ref lookup)
- Registry must be consulted during blueprint resolution

### Neutral

- HTTP MCP servers use registry refs

## References

- [ADR-018: Centralized Placeholder Resolution](./ADR-018-centralized-placeholder-resolution.md)
