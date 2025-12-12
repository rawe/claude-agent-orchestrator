# ADR-007: Hybrid Hook Configuration

**Status:** Accepted
**Date:** 2025-12-12
**Decision Makers:** Architecture Review
**Affected Components:** Claude Code Executor

## Context

Claude Agent SDK provides two hook mechanisms:
1. **Programmatic**: Python async functions via `ClaudeAgentOptions(hooks={...})`
2. **File-based**: External commands via `.claude/settings.json`

Question: which to use for the framework?

## Decision

**Hybrid approach** where both coexist and execute together.

### Layering

```
Layer 4: User Local (.local.json)     ← Personal overrides
Layer 3: Project (.claude/settings)   ← Team conventions
Layer 2: User Global (~/.claude)      ← Personal preferences
Layer 1: Programmatic (SDK code)      ← Framework defaults (always-on)
```

All matching hooks execute in parallel. Hooks are merged, not replaced.

### Use Case Assignment

| Use Case | Approach |
|----------|----------|
| Core observability | Programmatic |
| Security policies | Programmatic |
| Project linting | File-Based |
| Personal workflows | File-Based |

## Rationale

### Why Not Single Approach?

**Programmatic only**: Users lose customization flexibility
**File-based only**: No guaranteed framework defaults

**Hybrid**: Framework provides defaults, users retain customization.

## Consequences

### Positive
- Zero-config observability
- User flexibility via config files
- Type safety for framework hooks

### Negative
- Two configuration paths to document
- Potential confusion about which layer executes

## References

- [ClaudeAgentSDK-Hooks-Research.md](../../ClaudeAgentSDK-Hooks-Research.md)
