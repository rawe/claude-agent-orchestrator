# Phase 1: Centralized Script Management - Implementation Plan

## Prerequisites

Before implementing this plan, read the design document for full context:

- **[Phase 1: Scripts and Procedural Agents](./phase-1-scripts-and-procedural-agents.md)** - Complete design specification including script model, procedural agent changes, sync mechanism, and execution flow

## Overview

Scripts become a first-class primitive stored in the Coordinator. Procedural agents reference scripts for execution. Scripts are distributed to runners via long-poll sync commands.

## Milestones

### Milestone 1: Script Storage Layer (Coordinator)

Create `servers/agent-coordinator/script_storage.py` following `capability_storage.py` pattern:

```
config/scripts/{script_name}/
    script.json       # name, description, script_file, parameters_schema, demands
    {script_file}     # e.g., send-notification.py
```

**Files to create:**
- `servers/agent-coordinator/script_storage.py` - CRUD operations (get_scripts_dir, list_scripts, get_script, create_script, update_script, delete_script)

**Files to modify:**
- `servers/agent-coordinator/models.py` - Add Script, ScriptCreate, ScriptUpdate, ScriptSummary models

**Verification:** Create test script directory manually, start coordinator, verify no errors

---

### Milestone 2: Script API Endpoints (Coordinator)

**Files to modify:**
- `servers/agent-coordinator/main.py` - Add endpoints:
  - `GET /scripts` - List all scripts
  - `POST /scripts` - Create script
  - `GET /scripts/{name}` - Get script
  - `PATCH /scripts/{name}` - Update script
  - `DELETE /scripts/{name}` - Delete script
  - `GET /scripts/{name}/download` - Download script folder as tar.gz (for runner sync)

**Verification:** Test CRUD via curl

---

### Milestone 3: Procedural Agent Script Reference

**Files to modify:**
- `servers/agent-coordinator/models.py` - Add `script: Optional[str]` field to Agent model
- `servers/agent-coordinator/agent_storage.py` - Read/write `script` field
- `servers/agent-coordinator/main.py` - In run creation:
  - Resolve script from agent's `script` field
  - Merge demands (script + agent)
  - Use script's parameters_schema for validation

**Verification:** Create script + procedural agent referencing it, verify merged demands

---

### Milestone 4: Script Sync Mechanism

**Files to create:**
- `servers/agent-coordinator/services/script_sync_queue.py` - Queue sync/remove commands per runner

**Files to modify:**
- `servers/agent-coordinator/main.py`:
  - `GET /runner/runs` - Check for sync commands before returning runs
  - `POST /runner/register` - Queue initial sync for procedural runners
  - `DELETE /scripts/{name}` - Queue remove commands
  - Script create/update - Queue sync commands

- `servers/agent-runner/lib/api_client.py`:
  - Add to `PollResult`: `sync_scripts: list[str]`, `remove_scripts: list[str]`
  - Handle new response types in `poll_run()`
  - Add `download_script(name)` method

- `servers/agent-runner/lib/poller.py`:
  - Handle `sync_scripts` command - download and store locally
  - Handle `remove_scripts` command - delete local script folder
  - Store in `{project_dir}/.agent-orchestrator/scripts/{name}/`

**Verification:** Start coordinator with script, start procedural runner, verify script synced

---

### Milestone 5: Procedural Executor Script Execution

**Files to modify:**
- `servers/agent-runner/executors/procedural-executor/ao-procedural-exec`:
  - Check local scripts directory first: `{project_dir}/.agent-orchestrator/scripts/{agent.script}/`
  - Fall back to coordinator API for legacy agents (using `command` field)
  - Execute script with parameters converted to CLI args

**Verification:** End-to-end test - create script, create agent, sync to runner, invoke via API

---

### Milestone 6: Dashboard UI

**Files to create:**
- `dashboard/src/types/script.ts` - Script, ScriptCreate, ScriptUpdate, ScriptSummary
- `dashboard/src/services/scriptService.ts` - API client methods
- `dashboard/src/hooks/useScripts.ts` - State management hook
- `dashboard/src/pages/Scripts.tsx` - Scripts management page
- `dashboard/src/components/features/scripts/ScriptTable.tsx`
- `dashboard/src/components/features/scripts/ScriptEditor.tsx`
- `dashboard/src/components/features/scripts/index.ts`

**Files to modify:**
- `dashboard/src/router.tsx` - Add `/scripts` route
- `dashboard/src/components/layout/Sidebar.tsx` - Add Scripts nav item
- `dashboard/src/pages/index.ts` - Export Scripts page
- Agent editor - Add script selector for procedural agents (optional in Phase 1)

**Verification:** Navigate to Scripts page, create/edit/delete scripts

---

## Dependency Order

```
M1 (Storage) → M2 (API) → M3 (Agent Reference) → M4 (Sync) → M5 (Executor)
                    ↓
               M6 (Dashboard) - can start after M2
```

## Key Design Decisions

1. **UV scripts with `--isolated`?** - Defer, make configurable in executor config
2. **Script validation?** - Basic JSON schema syntax validation only
3. **Versioning?** - No versioning in Phase 1, scripts are mutable
4. **Existing runner-registered agents?** - Coexist: `command` field for legacy, `script` field for new

## Testing

1. Unit tests for script_storage.py CRUD
2. API endpoint tests
3. Integration tests using `/tests/run`:
   - Script CRUD
   - Procedural agent with script reference
   - Script sync to runner
   - End-to-end execution

## Critical Files Reference

| Component | Pattern File | New/Modified |
|-----------|--------------|--------------|
| Storage | `capability_storage.py` | `script_storage.py` (new) |
| Models | `models.py` | Add Script models |
| API | `main.py` | Add /scripts endpoints |
| Sync Queue | `stop_command_queue.py` | `script_sync_queue.py` (new) |
| Poll Result | `api_client.py:PollResult` | Add sync_scripts, remove_scripts |
| Poller | `poller.py` | Handle sync commands |
| Executor | `ao-procedural-exec` | Use synced scripts |
| Dashboard | `Capabilities.tsx` | `Scripts.tsx` (new) |
