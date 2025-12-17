# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records documenting significant architectural decisions made in the Agent Orchestrator project.

## What is an ADR?

An ADR captures an important architectural decision along with its context and consequences. ADRs help future maintainers understand why decisions were made.

## ADR Format

Each ADR follows this structure:

- **Status:** Proposed | Accepted | Deprecated | Superseded
- **Date:** When the decision was made
- **Context:** What prompted the decision
- **Decision:** What was decided
- **Rationale:** Why this option was chosen
- **Consequences:** Positive, negative, and neutral outcomes

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](./ADR-001-run-session-separation.md) | Run and Session Separation | Accepted | 2025-12-12 |
| [ADR-002](./ADR-002-agent-runner-architecture.md) | Agent Runner Architecture | Accepted | 2025-12-12 |
| [ADR-003](./ADR-003-callback-based-async.md) | Callback-Based Async for Agent Orchestration | Accepted | 2025-12-12 |
| [ADR-004](./ADR-004-session-stop-command.md) | Session Stop Command with Event Signaling | Accepted | 2025-12-12 |
| [ADR-005](./ADR-005-parent-session-context-propagation.md) | Parent Session Context Propagation | Accepted | 2025-12-12 |
| [ADR-006](./ADR-006-runner-registration-health-monitoring.md) | Runner Registration with Health Monitoring | Accepted | 2025-12-12 |
| [ADR-007](./ADR-007-hybrid-hook-configuration.md) | Hybrid Hook Configuration | Accepted | 2025-12-12 |
| [ADR-008](./ADR-008-concurrent-run-execution.md) | Concurrent Run Execution in Agent Runner | Accepted | 2025-12-12 |
| [ADR-009](./ADR-009-agent-filtering-at-discovery.md) | Agent Filtering at Discovery Time | Accepted | 2025-12-12 |

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
