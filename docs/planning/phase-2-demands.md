# Phase 2: Runner Capabilities and Demands (ADR-011)

**Status:** ✅ COMPLETE

## Overview

Implement capability/demand matching to route runs to appropriate runners. Adds `tags` capability to runners and demand matching logic for run claiming.

## Components Affected

### Agent Coordinator (`servers/agent-coordinator/`)

| File | Changes | Status |
|------|---------|--------|
| `models.py` | Add `RunnerDemands` model; add `demands` to `Agent`; add `additional_demands` to `RunCreate` | ✅ |
| `services/runner_registry.py` | Add `tags: list[str]` to `RunnerInfo`; update `register_runner()` | ✅ |
| `services/run_queue.py` | Add `demands` and `timeout_at` to `Run`; add `capabilities_satisfy_demands()`; add `DemandFields` constants | ✅ |
| `agent_storage.py` | Read `demands` from `agent.json` | ✅ |
| `main.py` | Update claim logic to filter by demands; add `run_timeout_task`; add `RUN_NO_MATCH_TIMEOUT` config | ✅ |

### Agent Runner (`servers/agent-runner/`)

| File | Changes | Status |
|------|---------|--------|
| `lib/api_client.py` | Add `tags` to `register()` | ✅ |
| `lib/config.py` | Add `RUNNER_TAGS` env var and `tags` field | ✅ |
| `agent-runner` | Pass tags from config to registration | ✅ |

### MCP Server (`mcps/agent-orchestrator/`)

| File | Changes | Status |
|------|---------|--------|
| `libs/constants.py` | Add `HEADER_ADDITIONAL_DEMANDS`, `ENV_ADDITIONAL_DEMANDS` | ✅ |
| `libs/api_client.py` | Add `additional_demands` to `create_run()` | ✅ |
| `libs/core_functions.py` | Add `get_additional_demands()`; pass to API | ✅ |
| `libs/schemas.py` | Add `additional_demands` to tool schemas | ⏭️ Skipped |

### Plugin CLI (`plugins/orchestrator/`)

| File | Changes | Status |
|------|---------|--------|
| `skills/orchestrator/commands/lib/run_client.py` | Add `additional_demands` parameter | ⏭️ Skipped |

### Agent Blueprints

| Location | Changes | Status |
|----------|---------|--------|
| `.agent-orchestrator/agents/*/agent.json` | Add optional `demands` section | ✅ |

## Implementation Order

1. **Models and types** ✅
   - Add `RunnerDemands` to `models.py`
   - Add `demands` to `Run` in `run_queue.py`

2. **Runner registration with tags** ✅
   - Add `tags` to `RunnerInfo`
   - Update `/runner/register` endpoint
   - Update agent-runner client

3. **Blueprint demands** ✅
   - Update `agent_storage.py` to read `demands`

4. **Run creation with demands** ✅
   - Load blueprint demands on run creation
   - Implement additive merge for `additional_demands`
   - Store merged demands on `Run`

5. **Claim logic with matching** ✅
   - Add `capabilities_satisfy_demands()` function
   - Update `claim_run()` to filter by matching

6. **No-match timeout** ✅
   - Add `timeout_at` to runs
   - Background task to fail timed-out runs

7. **Client updates** ✅ (partial)
   - MCP server: reads `ADDITIONAL_DEMANDS` env var or `X-Additional-Demands` header
   - Plugin CLI: skipped (not needed for core functionality)

## Dependencies

**Phase 1 must be complete:**
- Runner properties (hostname, project_dir, executor_type) available
- Deterministic runner_id derivation working

## Verification

1. Runner with matching tags claims run ✅
2. Runner without required tags cannot claim ✅
3. Run times out if no matching runner ✅
4. Additive merge never overrides blueprint demands ✅

## Integration Tests

- `tests/integration/09-demand-matching-success.md` - Runner with matching tags claims run
- `tests/integration/10-demand-matching-timeout.md` - Run times out when no matching runner

## Configuration

| Env Variable | Default | Description |
|--------------|---------|-------------|
| `RUN_NO_MATCH_TIMEOUT` | 300 (5 min) | Seconds before run fails if no matching runner |
| `RUNNER_TAGS` | (empty) | Comma-separated capability tags for agent-runner |
| `ADDITIONAL_DEMANDS` | (empty) | JSON demands for MCP server (stdio mode) |

| HTTP Header | Description |
|-------------|-------------|
| `X-Additional-Demands` | JSON demands for MCP server (HTTP mode) |
