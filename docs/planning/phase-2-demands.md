# Phase 2: Runner Capabilities and Demands (ADR-011)

## Overview

Implement capability/demand matching to route runs to appropriate runners. Adds `tags` capability to runners and demand matching logic for run claiming.

## Components Affected

### Agent Coordinator (`servers/agent-coordinator/`)

| File | Changes |
|------|---------|
| `models.py` | Add `RunnerDemands` model; add `demands` to `Agent`; add `additional_demands` to `RunCreate` |
| `services/runner_registry.py` | Add `tags: list[str]` to `RunnerInfo` |
| `services/run_queue.py` | Add `demands` and `timeout_at` to `Run`; add `capabilities_satisfy_demands()` |
| `agent_storage.py` | Read `demands` from `agent.json` |
| `main.py` | Update claim logic to filter by demands; add timeout handling |

### Agent Runner (`servers/agent-runner/`)

| File | Changes |
|------|---------|
| `lib/api_client.py` | Add `tags` to `register()`; add demands to `Run` dataclass |
| `lib/config.py` | Add `tags` configuration |

### MCP Server (`mcps/agent-orchestrator/`)

| File | Changes |
|------|---------|
| `libs/api_client.py` | Add `additional_demands` to `create_run()` |
| `libs/core_functions.py` | Pass `additional_demands` to API |
| `libs/schemas.py` | Add `additional_demands` to tool schemas |

### Plugin CLI (`plugins/orchestrator/`)

| File | Changes |
|------|---------|
| `skills/orchestrator/commands/lib/run_client.py` | Add `additional_demands` parameter |

### Agent Blueprints

| Location | Changes |
|----------|---------|
| `.agent-orchestrator/agents/*/agent.json` | Add optional `demands` section |

## Implementation Order

1. **Models and types**
   - Add `RunnerDemands` to `models.py`
   - Add `demands` to `Run` in `run_queue.py`

2. **Runner registration with tags**
   - Add `tags` to `RunnerInfo`
   - Update `/runner/register` endpoint
   - Update agent-runner client

3. **Blueprint demands**
   - Update `agent_storage.py` to read `demands`

4. **Run creation with demands**
   - Load blueprint demands on run creation
   - Implement additive merge for `additional_demands`
   - Store merged demands on `Run`

5. **Claim logic with matching**
   - Add `capabilities_satisfy_demands()` function
   - Update `claim_run()` to filter by matching

6. **No-match timeout**
   - Add `timeout_at` to runs
   - Background task to fail timed-out runs

7. **Client updates**
   - MCP server, plugins

## Dependencies

**Phase 1 must be complete:**
- Runner properties (hostname, project_dir, executor_type) available
- Deterministic runner_id derivation working

## Verification

1. Runner with matching tags claims run
2. Runner without required tags cannot claim
3. Run times out if no matching runner
4. Additive merge never overrides blueprint demands
