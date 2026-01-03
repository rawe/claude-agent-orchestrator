# Executor Profiles Implementation Guide

Implementation sessions for the Executor Profiles feature.

**Design Document:** [`../executor-profiles.md`](../executor-profiles.md)

## Sessions

| Order | Session | Component | Status |
|-------|---------|-----------|--------|
| 1 | [Executor](./01-executor.md) | `servers/agent-runner/executors/claude-code/` | Pending |
| 2 | [Agent Runner](./02-agent-runner.md) | `servers/agent-runner/` | Pending |
| 3 | [Agent Coordinator](./03-agent-coordinator.md) | `servers/agent-coordinator/` + `config/agents/` | Pending |
| 4 | [Dashboard](./04-dashboard.md) | `dashboard/src/` | Pending |

## Dependency Graph

```
Session 1: Executor
     │
     ▼
Session 2: Agent Runner
     │
     ▼
Session 3: Agent Coordinator
     │
     ▼
Session 4: Dashboard
```

## How to Use

1. Open a new AI coding session
2. Share the relevant session document (e.g., `01-executor.md`)
3. Reference the main design doc for detailed specifications
4. Mark session as complete when definition of done is satisfied

## Quick Reference

### Key Renames
- `executor_type` → `executor_profile` (everywhere)
- `--executor` → `--profile` (CLI)
- Schema 2.0 → 2.1 (invocation)

### New Fields
- `executor_config` in invocation payload
- `executor` object in registration
- `require_matching_tags` boolean

### Files by Session

**Session 1:**
- `servers/agent-runner/executors/claude-code/ao-claude-code-exec`

**Session 2:**
- `servers/agent-runner/lib/invocation.py`
- `servers/agent-runner/lib/executor.py`
- `servers/agent-runner/agent-runner`
- `servers/agent-runner/profiles/*.json`

**Session 3:**
- `servers/agent-coordinator/models.py`
- `servers/agent-coordinator/database.py`
- `servers/agent-coordinator/services/runner_registry.py`
- `servers/agent-coordinator/services/run_queue.py`
- `servers/agent-coordinator/main.py`
- `config/agents/*/agent.json`

**Session 4:**
- `dashboard/src/types/*.ts`
- `dashboard/src/pages/Runners.tsx`
- `dashboard/src/components/features/agents/AgentEditor.tsx`
- `dashboard/src/utils/mcpTemplates.ts`
- `dashboard/src/services/*.ts`
