# ADR-017: Procedural Agent Ownership Model

**Status:** Accepted
**Date:** 2026-01-25

## Context

Procedural agents execute deterministic scripts. Before centralized script management, scripts were bundled with runners and registered at startup. With scripts becoming a first-class primitive stored in the Coordinator, we needed to support both:

1. **New model:** Coordinator-managed scripts that are synced to runners
2. **Legacy model:** Runner-bundled scripts for backward compatibility

## Decision

Procedural agents support two ownership models. The **Agent** entity (stored in the Coordinator) uses different fields depending on ownership:

**Coordinator-owned agents** set the `script` field, which references a Script entity managed by the Coordinator. Scripts are synced to runners via the long-poll mechanism.

**Runner-owned agents** set the `command` and `runner_id` fields. The command points to a script bundled with the runner's filesystem. These agents are registered by runners at startup.

| Ownership | Agent Fields | Script Location |
|-----------|--------------|-----------------|
| **Coordinator-owned** | `script` set | `{PROJECT_DIR}/scripts/{name}/` (synced) |
| **Runner-owned** | `command` + `runner_id` set | Runner's local filesystem |

The Procedural Executor resolves execution mode by checking which fields are present on the Agent. The two field patterns are mutually exclusive.

## Rationale

**Why two models?**
- Enables gradual migration from runner-bundled to centralized scripts
- Allows runners to provide specialized local tools that don't need central management
- Maintains backward compatibility with existing deployments

**Why not unify into a single model?**
- Forcing all scripts to be centralized would break existing runner setups
- Some scripts may have runner-specific dependencies or configurations
- Central management adds overhead for simple, runner-specific tools

## Consequences

### Positive
- Clear separation between managed and local scripts
- Existing runner-owned agents continue to work unchanged
- New agents benefit from central management and Dashboard UI

### Negative
- Two code paths in the Procedural Executor
- Potential confusion about which model to use

### Neutral
- Migration from runner-owned to coordinator-owned is manual but straightforward
