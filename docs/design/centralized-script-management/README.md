# Centralized Script Management

**Status:** Design Phase
**Created:** 2025-01-24

## Problem Statement

Procedural scripts are currently bundled locally with runners, creating operational challenges:
- No central visibility into available scripts
- Script updates require manual deployment to each runner
- Cannot manage scripts through the Dashboard

## Solution

Scripts become a **first-class primitive** stored in the Coordinator:
- Scripts define execution logic and parameters
- Procedural agents reference scripts
- Scripts are distributed to runners via sync commands

## Phases

### Phase 1: Scripts as Foundation for Procedural Agents

Scripts are stored in the Coordinator and used as the foundation for procedural agents. Autonomous agents invoke procedural agents via the orchestrator MCP.

**Status:** Design complete

### Phase 2: Scripts as Capabilities for Autonomous Agents

Scripts are synced to autonomous runners and exposed as skills, enabling local execution with filesystem access.

**Status:** Future consideration

## Documents

| Document | Description |
|----------|-------------|
| [Phase 1: Scripts and Procedural Agents](./phase-1-scripts-and-procedural-agents.md) | Script model, procedural agents, distribution mechanism |
| [Phase 2: Scripts as Capabilities](./phase-2-scripts-as-capabilities.md) | Local execution for autonomous agents (future) |
| [Open Questions](./open-questions.md) | Unresolved design questions |
| [Implementation References](./implementation-references.md) | Key documents and code locations for implementation |

## Scope Summary

### Phase 1 (Current)

- Script storage in Coordinator (folder per script)
- Script model: name, description, script file, parameters schema, demand tags
- Procedural agents reference scripts
- Script sync via long-poll commands
- Dashboard management for scripts and procedural agents

### Phase 2 (Future)

- Script sync to autonomous runners
- Scripts as capabilities/skills
- Local filesystem access for scripts
- System prompt injection for script usage
