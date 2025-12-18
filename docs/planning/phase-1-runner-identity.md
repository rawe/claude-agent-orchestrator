# Phase 1: Runner Identity (ADR-012)

**Status: COMPLETED**

## Overview

Implement deterministic runner ID derivation from runner properties (hostname, project_dir, executor_type) to enable automatic reconnection recognition, with lifecycle management (online/stale/removed states).

## Components Affected

### Agent Coordinator (`servers/agent-coordinator/`)

| File | Changes |
|------|---------|
| `services/runner_registry.py` | Add `derive_runner_id()` function; require hostname/project_dir/executor_type; add `status` field to `RunnerInfo`; handle reconnection |
| `main.py` | Update `RunnerRegisterRequest` to require properties; add background task for stale detection/cleanup |

### Agent Runner (`servers/agent-runner/`)

| File | Changes |
|------|---------|
| `lib/api_client.py` | Make hostname/project_dir/executor_type required in `register()` |

### Dashboard (`dashboard/src/`)

| File | Changes |
|------|---------|
| `types/runner.ts` | Status now comes from server (not computed client-side) |

## Implementation Order

1. **ID derivation function**
   - Add `derive_runner_id(hostname, project_dir, executor_type) -> str` to `runner_registry.py`
   - Format: `lnch_{sha256_hash[:12]}`

2. **Update RunnerInfo model**
   - Add `status: Literal["online", "stale"]`
   - Make hostname, project_dir, executor_type required

3. **Modify register_runner()**
   - Derive runner_id from properties
   - If runner exists with same ID: reconnection (update status to online)
   - If new: create record

4. **Update RunnerRegisterRequest**
   - Change hostname, project_dir, executor_type from Optional to required

5. **Add background lifecycle task**
   - Run every 30 seconds
   - Stale: no heartbeat for 2+ minutes
   - Remove: no heartbeat for 10+ minutes
   - Start in `lifespan()`, cancel on shutdown

6. **Update GET /runners endpoint**
   - Return status from RunnerInfo directly

7. **Update agent-runner api_client.py**
   - Make register() parameters required

## Dependencies

None (Phase 1 is the foundation)

## Verification

1. [x] Start runner, stop, restart → same runner_id returned
2. [ ] Stop runner process, wait 2+ min → status becomes "stale" (not manually tested)
3. [ ] Stale for 10+ min → runner removed from GET /runners (not manually tested)
4. [x] Register without required properties → 422 error

Integration test: `tests/integration/08-runner-identity.md`
