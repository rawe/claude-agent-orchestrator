# Implementation Guide: Agent Launcher → Agent Runner

**Sequence:** 3 of 3
**Estimated Changes:** ~111 references
**Dependencies:** Complete implementations 1 and 2 first

---

## Context

This is the final terminology rename. After this, the API path `/launcher/runs` becomes `/runner/runs`, completing the full terminology update.

### What is Agent Launcher (currently)?

A standalone process that:
- Polls Agent Coordinator for pending runs
- Claims runs atomically
- Executes runs via framework-specific executors
- Reports run status (started, completed, failed, stopped)
- Handles stop commands
- Maintains heartbeat for health monitoring

### Why Rename to "Agent Runner"?

"Launcher" implies only starting things. This component does much more—it runs, monitors, and reports. The GitLab Runner analogy is apt: runners poll for work, execute it, and report back.

"Runner" is industry-standard terminology (GitLab Runner, GitHub Actions Runner) and pairs naturally with "Runs" (from implementation 2).

---

## Scope

### What Changes

1. Directory names
2. File names
3. API endpoint paths (`/launcher/*` → `/runner/*`)
4. Python classes and variables
5. TypeScript types and services
6. Dashboard UI and routes
7. Environment variables
8. Documentation

### What Does NOT Change

- Executor structure (stays in `executors/` subdirectory)
- Core execution logic
- Heartbeat/health monitoring concepts

---

## Implementation Checklist

### Phase 1: Directory Rename

```bash
mv servers/agent-launcher servers/agent-runner
```

### Phase 2: Main Script Rename

```bash
mv servers/agent-runner/agent-launcher servers/agent-runner/agent-runner
```

Update shebang and script name references inside the file.

### Phase 3: Agent Coordinator API (servers/agent-coordinator/)

#### main.py - API Endpoints

| Current Path | New Path |
|--------------|----------|
| `GET /launcher/runs` | `GET /runner/runs` |
| `POST /launcher/runs/{run_id}/started` | `POST /runner/runs/{run_id}/started` |
| `POST /launcher/runs/{run_id}/completed` | `POST /runner/runs/{run_id}/completed` |
| `POST /launcher/runs/{run_id}/failed` | `POST /runner/runs/{run_id}/failed` |
| `POST /launcher/runs/{run_id}/stopped` | `POST /runner/runs/{run_id}/stopped` |
| `POST /launcher/register` | `POST /runner/register` |
| `POST /launcher/heartbeat` | `POST /runner/heartbeat` |
| `GET /launchers` | `GET /runners` |
| `DELETE /launchers/{launcher_id}` | `DELETE /runners/{runner_id}` |

#### main.py - Request/Response Models

| Current | New |
|---------|-----|
| `LauncherRegisterRequest` | `RunnerRegisterRequest` |
| `LauncherRegisterResponse` | `RunnerRegisterResponse` |

#### main.py - Variables

| Current | New |
|---------|-----|
| `launcher_id` | `runner_id` |
| `launcher` | `runner` |
| `launchers` | `runners` |

#### services/launcher_registry.py

**Rename file:** `launcher_registry.py` → `runner_registry.py`

| Current | New |
|---------|-----|
| `class LauncherInfo` | `class RunnerInfo` |
| `class LauncherRegistry` | `class RunnerRegistry` |
| `launcher_registry` (singleton) | `runner_registry` |
| `launcher_id` | `runner_id` |
| `get_launcher()` | `get_runner()` |
| `get_all_launchers()` | `get_all_runners()` |
| `is_launcher_alive()` | `is_runner_alive()` |
| `remove_launcher()` | `remove_runner()` |
| `register_launcher()` | `register_runner()` |

#### services/stop_command_queue.py

| Current | New |
|---------|-----|
| `LauncherStopState` | `RunnerStopState` |
| `launcher_id` parameter | `runner_id` parameter |

### Phase 4: Environment Variables (main.py)

| Current | New |
|---------|-----|
| `LAUNCHER_POLL_TIMEOUT` | `RUNNER_POLL_TIMEOUT` |
| `LAUNCHER_HEARTBEAT_INTERVAL` | `RUNNER_HEARTBEAT_INTERVAL` |
| `LAUNCHER_HEARTBEAT_TIMEOUT` | `RUNNER_HEARTBEAT_TIMEOUT` |

### Phase 5: Agent Runner Code (servers/agent-runner/)

#### lib/config.py

| Current | New |
|---------|-----|
| `class LauncherConfig` | `class RunnerConfig` |
| Variable names with `launcher` | Variable names with `runner` |

#### lib/api_client.py

Update endpoint URLs:
```python
# Old
f"{self.base_url}/launcher/register"
f"{self.base_url}/launcher/runs"
f"{self.base_url}/launcher/heartbeat"

# New
f"{self.base_url}/runner/register"
f"{self.base_url}/runner/runs"
f"{self.base_url}/runner/heartbeat"
```

#### All lib/*.py files

| Current | New |
|---------|-----|
| `launcher_id` | `runner_id` |
| `launcher` | `runner` |
| Comments with "launcher" | Comments with "runner" |

#### Main script (agent-runner)

| Current | New |
|---------|-----|
| Logger name `"agent-launcher"` | `"agent-runner"` |
| `"Launcher started"` | `"Runner started"` |
| `"Launcher stopped"` | `"Runner stopped"` |
| `"Registered as {launcher_id}"` | `"Registered as {runner_id}"` |

### Phase 6: Dashboard (dashboard/src/)

#### types/launcher.ts

**Rename file:** `launcher.ts` → `runner.ts`

| Current | New |
|---------|-----|
| `interface Launcher` | `interface Runner` |
| `type LauncherStatus` | `type RunnerStatus` |
| `launcher_id` | `runner_id` |

#### services/launcherService.ts

**Rename file:** `launcherService.ts` → `runnerService.ts`

| Current | New |
|---------|-----|
| `launcherService` | `runnerService` |
| `'/launchers'` endpoint | `'/runners'` endpoint |
| `Launcher` type | `Runner` type |

#### pages/Launchers.tsx

**Rename file:** `Launchers.tsx` → `Runners.tsx`

| Current | New |
|---------|-----|
| `Launchers` component | `Runners` component |
| `LauncherCard` component | `RunnerCard` component |
| Page title "Agent Launchers" | "Agent Runners" |
| All `launcher` variables | `runner` variables |

#### Router/Navigation

- Update route from `/launchers` to `/runners`
- Update sidebar menu item label

#### types/index.ts

Update exports to use new type names.

### Phase 7: Makefile

Update any references to agent-launcher:
```makefile
# Old
./servers/agent-launcher/agent-launcher

# New
./servers/agent-runner/agent-runner
```

### Phase 8: Docker Configuration

#### docker-compose.yml (if launcher is containerized)

Update any service definitions, volume mounts, or build contexts.

### Phase 9: Documentation

#### Rename Files

| Current | New |
|---------|-----|
| `docs/adr/ADR-002-agent-launcher-architecture.md` | `docs/adr/ADR-002-agent-runner-architecture.md` |
| `docs/adr/ADR-006-launcher-registration-health-monitoring.md` | `docs/adr/ADR-006-runner-registration-health-monitoring.md` |

#### Update Content

Replace throughout all documentation:
- "Agent Launcher" → "Agent Runner"
- "launcher" → "runner"
- "/launcher/" → "/runner/"
- "launcher_id" → "runner_id"

Files to update:
- README.md
- docs/ARCHITECTURE.md
- docs/agent-coordinator/API.md
- docs/agent-coordinator/RUNS_API.md
- docs/agent-coordinator/RUN_EXECUTION_FLOW.md
- docs/features/agent-callback-architecture.md
- docs/features/session-stop-command.md
- servers/agent-runner/README.md

### Phase 10: Test Files

- tests/README.md
- tests/integration/*.md
- .claude/commands/tests/*.md
- Update any test scripts referencing launcher paths

### Phase 11: Tickets/Planning Docs

```bash
mv tickets/feat_001_agent_launcher tickets/feat_001_agent_runner
```

---

## Verification Steps

1. **Python syntax check:**
   ```bash
   uv run python -m py_compile servers/agent-coordinator/main.py
   uv run python -m py_compile servers/agent-coordinator/services/runner_registry.py
   ```

2. **Start coordinator:**
   ```bash
   cd servers/agent-coordinator && uv run python main.py
   ```

3. **Start runner:**
   ```bash
   ./servers/agent-runner/agent-runner
   ```

4. **Test API endpoints:**
   ```bash
   curl http://localhost:8765/runners  # Should work
   curl http://localhost:8765/launchers  # Should 404
   ```

5. **Test runner registration:**
   ```bash
   # Runner should register successfully and appear in /runners list
   ```

6. **Dashboard check:**
   - Navigate to `/runners` route
   - Verify runner appears in UI

7. **Grep verification:**
   ```bash
   # Should return minimal results (only historical/git references)
   grep -r "launcher" --include="*.py" --include="*.ts" --include="*.tsx" servers/ dashboard/src/ | grep -v node_modules | grep -v __pycache__
   ```

---

## Breaking Changes

This is a **breaking API change**:
- All clients using `/launcher/*` endpoints must update to `/runner/*`
- All clients using `/launchers` must update to `/runners`
- Field `launcher_id` changes to `runner_id`

---

## Final State

After completing all three implementations:

| Component | Old Name | New Name |
|-----------|----------|----------|
| Central Server | Agent Runtime | Agent Coordinator |
| Execution Manager | Agent Launcher | Agent Runner |
| Work Unit | Job | Agent Run |

API Endpoints:
- `POST /runs` - Create run
- `GET /runner/runs` - Poll for runs
- `POST /runner/runs/{run_id}/started` - Report started
- `GET /runners` - List runners

Conceptual Model:
```
Blueprint → Session → Agent Run → Agent Runner → Executor → Claude Code
```

---

## Completion Checklist

After all three implementations:

- [ ] All services start without errors
- [ ] Dashboard loads and shows runners
- [ ] Runner registers and receives runs
- [ ] Full workflow test: create run → runner claims → executes → completes
- [ ] No "runtime", "launcher", or "job" references in active code (grep check)
- [ ] Documentation updated throughout
- [ ] README reflects new terminology
