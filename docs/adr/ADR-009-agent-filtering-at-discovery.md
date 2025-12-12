# ADR-009: Agent Filtering at Discovery Time

**Status:** Accepted
**Date:** 2025-12-12
**Decision Makers:** Architecture Review
**Affected Components:** Agent Runtime, Dashboard, ao-list-blueprints

## Context

Different consumers need different agent visibility:
- End users: Only user-facing agents
- Orchestrator framework: Only worker agents
- Management tools: All agents

Question: Filter at discovery time (listing) or execution time (start/resume)?

## Decision

**Filter at discovery time, not execution time.**

### Discovery-Time Filtering
- `GET /agents?tags=<tags>` filters during listing
- `ao-list-blueprints --tags internal` returns filtered results
- If consumer doesn't know about an agent, it cannot request it

### No Execution-Time Filtering
- `ao-start <agent-name>` accepts ANY agent name
- No tag validation at execution
- Assumes client has already performed appropriate filtering

### Tag Logic

- AND logic: agents must have ALL requested tags
- Reserved: `external` (user-facing), `internal` (framework workers)
- Custom domain tags supported

## Rationale

### Why Discovery, Not Execution?

**API-level concern**: Filtering is about what consumer should see, not what it can execute

**Performance**: Discovery happens once, execution happens frequently

**Simplicity**: Commands remain simple (`ao-start <name>`)

**Security model**: This is cooperative filtering for UX, not access control

## Consequences

### Positive
- Clean separation: API filters, commands execute
- Simple command signatures
- Efficient: filter once, execute many

### Negative
- No enforcement at execution (assumes correct behavior)
- Discovery and execution are separate steps

## References

- [agent-management.md](../features/agent-management.md)
