# Capabilities System - Work Packages

**Parent Feature:** [Capabilities System](../capabilities-system.md)

## Implementation Order

```
┌─────────────────────────┐
│ 01-capability-storage   │  Foundation: file storage, models, validation
└───────────┬─────────────┘
            │
     ┌──────┴──────┐
     ▼             ▼
┌─────────┐  ┌─────────────────────────┐
│ 02-api  │  │ 03-agent-capabilities   │
└────┬────┘  └───────────┬─────────────┘
     │                   │
     │    ┌──────────────┘
     │    ▼
     │  ┌─────────────────────────┐
     │  │ 04-capability-resolution │  Core merging logic
     │  └───────────┬─────────────┘
     │              │
     ▼              ▼
┌─────────────────────────────────┐
│ 05-dashboard-capability-mgmt    │
└───────────┬─────────────────────┘
            │
            ▼
┌─────────────────────────────────┐
│ 06-dashboard-agent-capabilities │
└─────────────────────────────────┘
```

## Work Packages

| # | Package | Description |
|---|---------|-------------|
| 1 | [capability-storage](./01-capability-storage.md) | File storage, models, validation |
| 2 | [capability-api](./02-capability-api.md) | REST CRUD endpoints |
| 3 | [agent-capabilities-field](./03-agent-capabilities-field.md) | Add capabilities to agent model |
| 4 | [capability-resolution](./04-capability-resolution.md) | Merging logic (core feature) |
| 5 | [dashboard-capability-management](./05-dashboard-capability-management.md) | UI for managing capabilities |
| 6 | [dashboard-agent-capabilities](./06-dashboard-agent-capabilities.md) | Agent form capability selection |

## Parallel Work

- WP2 and WP3 can be done in parallel after WP1
- WP5 can start once WP2 is complete (doesn't need WP4)
- WP6 needs both WP4 and WP5
