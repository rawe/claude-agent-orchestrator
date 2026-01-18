# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records documenting significant architectural decisions made in the Agent Orchestrator project.

## What is an ADR?

An ADR captures an important architectural decision along with its context and consequences. ADRs help future maintainers understand why decisions were made.

## ADR Format

Each ADR follows this structure:

- **Status:** Proposed | Accepted | Partially Superseded | Deprecated | Superseded
- **Date:** When the decision was made
- **Context:** What prompted the decision
- **Decision:** What was decided
- **Rationale:** Why this option was chosen
- **Consequences:** Positive, negative, and neutral outcomes

## Index

### Accepted

| ADR | Title | Date | Notes |
|-----|-------|------|-------|
| [ADR-001](./ADR-001-run-session-separation.md) | Run and Session Separation | 2025-12-12 | Partially superseded by ADR-010 |
| [ADR-002](./ADR-002-agent-runner-architecture.md) | Agent Runner Architecture | 2025-12-12 | |
| [ADR-003](./ADR-003-callback-based-async.md) | Callback-Based Async for Agent Orchestration | 2025-12-12 | |
| [ADR-004](./ADR-004-session-stop-command.md) | Session Stop Command with Event Signaling | 2025-12-12 | |
| [ADR-005](./ADR-005-parent-session-context-propagation.md) | Parent Session Context Propagation | 2025-12-12 | |
| [ADR-007](./ADR-007-hybrid-hook-configuration.md) | Hybrid Hook Configuration | 2025-12-12 | |
| [ADR-008](./ADR-008-concurrent-run-execution.md) | Concurrent Run Execution in Agent Runner | 2025-12-12 | |
| [ADR-009](./ADR-009-agent-filtering-at-discovery.md) | Agent Filtering at Discovery Time | 2025-12-12 | |
| [ADR-010](./ADR-010-session-identity-and-executor-abstraction.md) | Session Identity and Executor Abstraction | 2025-12-18 | |
| [ADR-011](./ADR-011-runner-capabilities-and-run-demands.md) | Runner Capabilities and Run Demands | 2025-12-18 | |
| [ADR-012](./ADR-012-runner-identity-and-registration.md) | Runner Identity and Registration | 2025-12-18 | |
| [ADR-013](./ADR-013-websocket-to-sse-migration.md) | WebSocket to SSE Migration | 2025-12-21 | |
| [ADR-014](./ADR-014-callback-message-format.md) | Callback Message Format with XML Tags | 2026-01-06 | |
| [ADR-015](./ADR-015-autonomous-agent-input-schema.md) | Autonomous Agent Input Schema Handling | 2026-01-10 | |
| [ADR-016](./ADR-016-autonomous-agent-output-schema.md) | Autonomous Agent Output Schema | 2026-01-18 | |

### Superseded

| ADR | Title | Superseded By | Date |
|-----|-------|---------------|------|
| [ADR-006](./ADR-006-runner-registration-health-monitoring.md) | Runner Registration with Health Monitoring | ADR-012 | 2025-12-12 |

## Creating a New ADR

1. Copy the template below
2. Name it `ADR-NNN-short-title.md`
3. Add to the index above

### Template

```markdown
# ADR-NNN: Title

**Status:** Proposed
**Date:** YYYY-MM-DD
**Decision Makers:** [Names/Roles]

## Context

[What is the issue that we're seeing that is motivating this decision?]

## Decision

[What is the change that we're proposing and/or doing?]

## Rationale

[Why is this decision being made? What alternatives were considered?]

## Consequences

### Positive
[What becomes easier?]

### Negative
[What becomes harder?]

### Neutral
[What else changes?]

## References

[Links to related documents, issues, or discussions]
```
