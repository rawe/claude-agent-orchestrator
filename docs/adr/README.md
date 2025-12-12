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
| [ADR-001](./ADR-001-job-session-separation.md) | Job and Session Separation | Accepted | 2025-12-12 |

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
