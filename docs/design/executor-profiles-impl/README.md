# Executor Profiles Implementation Guide

Implementation sessions for the Executor Profiles feature.

**Design Document:** [`../executor-profiles.md`](../executor-profiles.md)

## Sessions

| Order | Session | Component | Status |
|-------|---------|-----------|--------|
| 1 | [Executor](./01-executor.md) | `servers/agent-runner/executors/claude-code/` | Done |
| 2 | [Agent Runner](./02-agent-runner.md) | `servers/agent-runner/` | Done |
| 3 | [Agent Coordinator](./03-agent-coordinator.md) | `servers/agent-coordinator/` + `config/agents/` | Done |
| 3b | [Runner Client Fixes](./03-agent-coordinator-runner-fixes.md) | `servers/agent-runner/lib/` + executors | Done |
| 4 | [Executor-Runner Communication](./04-executor-runner-communication-refactor.md) | Runner/executor interface | Done |
| 5 | [Dashboard](./05-dashboard.md) | `dashboard/src/` | Pending |

## Dependency Graph

```
Session 1: Executor ✓
     │
     ▼
Session 2: Agent Runner ✓
     │
     ▼
Session 3: Agent Coordinator ✓
     │
     ├──► Session 3b: Runner Client Fixes ✓
     │         │
     │         ▼
     │    Session 4: Executor-Runner Communication Refactor ✓
     │
     ▼
Session 5: Dashboard
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

**Session 4 (Executor-Runner Communication):**
- `servers/agent-runner/agent-runner` (uses RunnerGateway)
- `servers/agent-runner/lib/runner_gateway.py` (new - replaces coordinator_proxy.py)
- `servers/agent-runner/lib/session_client.py` (simplified bind API)
- `servers/agent-runner/executors/claude-code/lib/claude_client.py`
- `servers/agent-runner/executors/test-executor/ao-test-exec`
- `servers/agent-runner/docs/runner-gateway-api.md` (new)

**Session 5 (Dashboard):**
- `dashboard/src/types/*.ts`
- `dashboard/src/pages/Runners.tsx`
- `dashboard/src/components/features/agents/AgentEditor.tsx`
- `dashboard/src/utils/mcpTemplates.ts`
- `dashboard/src/services/*.ts`
