# Production Readiness Checklist

Production readiness assessment for deploying Agent Coordinator to a public domain with multiple concurrent users.

## Context

- **Current state**: Single-user development setup with SQLite (runs, sessions, events all persisted)
- **Target state**: Multi-user production with many sessions/runs per day
- **Authentication**: Already implemented (Auth0 OIDC)

## Priority Levels

| Level | Meaning |
|-------|---------|
| **P0** | Critical - Must address before production |
| **P1** | High - Address before significant user load |
| **P2** | Medium - Address as usage grows |
| **P3** | Low - Nice to have, monitor first |

## Checklist Overview

| ID | Topic | Priority | Status |
|----|-------|----------|--------|
| [PR-001](./PR-001-database-migration.md) | Database Migration (SQLite → PostgreSQL) | P0 | Pending |
| [PR-002](./PR-002-run-queue-durability.md) | Run Queue Simplification (Remove Cache) | P1 | Pending |
| [PR-003](./PR-003-rate-limiting.md) | Rate Limiting & Abuse Protection | P1 | Pending |
| [PR-004](./PR-004-coordinator-scaling.md) | Coordinator Horizontal Scaling | P2 | Pending |
| [PR-005](./PR-005-sse-scalability.md) | SSE Broadcast Scalability | P2 | Pending |
| [PR-006](./PR-006-monitoring.md) | Monitoring & Observability | P1 | Pending |
| [PR-007](./PR-007-runner-load-assessment.md) | Runner Load Assessment (Message Queue?) | P2 | Pending |

## What's NOT Included

Items considered but deemed not critical for initial production:

- **Message queue for run dispatch**: Current long-poll pattern handles load well. Runners wait (not spam). Reassess at 100+ runners.
- **Session data sharding**: SQLite → PostgreSQL handles this. Sharding premature.
- **Kubernetes orchestration**: Deployment tooling, not code changes.
- **CDN for dashboard**: Static assets, standard infrastructure.

## Reading Order

1. Start with this README for overview
2. Read P0 items first (critical blockers)
3. P1 items before launch
4. P2/P3 items as usage grows

## Architecture Reference

See [ARCHITECTURE.md](../ARCHITECTURE.md) for system overview.
