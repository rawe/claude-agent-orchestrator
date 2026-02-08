# Executor Session ID Scope: Keep the Bind Call, Drop executor_session_id Storage

## Status: Decision Record (Phase 2)

## Current Flow

The `executor_session_id` is the Claude SDK's internal UUID for a conversation (e.g.,
`"a1b2c3d4-..."`). Today it flows through the system like this:

```
Executor:  extract from SDK SystemMessage(subtype='init')
        -> POST /bind {executor_session_id, project_dir}
                                    |
Runner Gateway:  enrich with {hostname, executor_profile}
                                    |
Coordinator:  bind_session_executor() ->
                - session.executor_session_id = "a1b2c3d4-..."
                - session.hostname = "runner-1"
                - session.executor_profile = "claude-sdk-executor"
                - session.status = "running"
```

For one-shot resume, the executor fetches `executor_session_id` back via
`GET /sessions/{session_id}` and passes it to `ClaudeSDKClient(options.resume=...)`.

## What the Bind Call Actually Does

`bind_session_executor()` (database.py:356) performs **four** operations:

| # | Operation | Needed for multi-turn? |
|---|-----------|----------------------|
| 1 | `session.status = 'running'` | **Yes** -- clients poll session status |
| 2 | `session.hostname = "..."` | **Yes** -- affinity routing for resume runs (run_demands.py:122) |
| 3 | `session.executor_profile = "..."` | **Yes** -- affinity routing for resume runs (run_demands.py:124) |
| 4 | `session.executor_session_id = "..."` | **No** -- useless after process death; resume uses live process |

## Decision: Keep the Bind, Stop Storing executor_session_id

**Keep the bind call.** It is the only mechanism that delivers `hostname` and
`executor_profile` to the coordinator for affinity routing, and it transitions the session
to `running` status. Without it, resume routing breaks and clients see stale session status.

**Stop relying on `executor_session_id` for resume.** In multi-turn, resume happens within
the live process via `client.query()`. The SDK's session UUID is only meaningful while the
`ClaudeSDKClient` instance is alive. Once the process dies, the ID is useless because
`--resume` + `--input-format stream-json` is a broken CLI combination (GitHub #16712).

### Concrete Changes

**Phase 2 -- minimal**:
- The executor continues to call `bind()` exactly as it does today. No change to the
  executor, `session_events.py`, `session_client.py`, or `runner_gateway.py`.
- The coordinator continues to store `executor_session_id` -- no schema change needed.
- The runner's `_route_resume()` (new in Phase 2) routes via the registry's live process
  lookup, not via `executor_session_id`.

**Phase 3 -- cleanup** (optional, not blocking):
- The one-shot `run_resume()` code path in the executor (which fetches `executor_session_id`
  back from the coordinator) can be deleted when legacy claude-code profiles are migrated.
- The `executor_session_id` column could be made nullable/removed from the sessions table
  if no other consumer needs it.
- The `get_session_affinity()` query could drop `executor_session_id` from its SELECT.

### Why Not Remove the Bind Now

Removing the bind call would require:
1. Moving `session.status = 'running'` into `report_run_started()` -- currently that
   endpoint only sets `run.status = RUNNING`, not `session.status`. This is a coordinator
   change.
2. Moving `hostname` + `executor_profile` delivery into `report_run_started()` -- this
   would require the runner to send these fields in the started report, which currently
   only sends `runner_id`.
3. Changing `run_demands.py` affinity lookup to use the runner registry instead of the
   sessions table.

This is achievable but unnecessary churn for Phase 2. The bind call works correctly. The
only thing that changes is the *meaning* of `executor_session_id`: from "needed for resume"
to "diagnostic/audit data."

## Affinity in Multi-Turn

Session affinity is still needed even with persistent processes. The coordinator must route
`resume_session` runs to the runner that holds the live process. This routing uses
`hostname` + `executor_profile` from the sessions table (set by the bind call).

The live process itself is tracked by the runner's `ProcessRegistry`. The coordinator does
not track processes -- it tracks which runner should receive the run. The runner then
checks its local registry to find the live process.

## Summary

| Aspect | Decision |
|--------|----------|
| Bind call | **Keep** (delivers hostname, executor_profile, status) |
| executor_session_id storage | **Keep** (no cost to store; useful for diagnostics) |
| executor_session_id for resume | **Ignore** (multi-turn resumes via live process, not SDK resume) |
| Executor code changes | **None** for Phase 2 |
| Coordinator code changes | **None** for Phase 2 |
