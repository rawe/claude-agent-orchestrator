# Agent Launcher → Agent Runner: Renaming Analysis

This document catalogs all occurrences of "Agent Launcher" terminology that need to be renamed when transitioning to "Agent Runner".

**Total estimated changes:** ~111+ references across the codebase.

---

## 1. Directory Names

| Current | New |
|---------|-----|
| `servers/agent-launcher/` | `servers/agent-runner/` |
| `tickets/feat_001_agent_launcher/` | `tickets/feat_001_agent_runner/` |

---

## 2. File Names

| Current | New |
|---------|-----|
| `servers/agent-launcher/agent-launcher` | `servers/agent-runner/agent-runner` |
| `servers/agent-launcher/README.md` | `servers/agent-runner/README.md` |
| All lib files move with directory | - |

---

## 3. Environment Variables

| Current | New | Location |
|---------|-----|----------|
| `LAUNCHER_POLL_TIMEOUT` | `RUNNER_POLL_TIMEOUT` | agent-runtime/main.py |
| `LAUNCHER_HEARTBEAT_INTERVAL` | `RUNNER_HEARTBEAT_INTERVAL` | agent-runtime/main.py |
| `LAUNCHER_HEARTBEAT_TIMEOUT` | `RUNNER_HEARTBEAT_TIMEOUT` | agent-runtime/main.py |

**Note:** Generic env vars like `POLL_TIMEOUT`, `HEARTBEAT_INTERVAL` in agent-launcher can stay.

---

## 4. API Endpoints

| Current | New | Method |
|---------|-----|--------|
| `POST /launcher/register` | `POST /runner/register` | POST |
| `GET /launcher/jobs` | `GET /runner/jobs` | GET |
| `POST /launcher/jobs/{job_id}/started` | `POST /runner/jobs/{job_id}/started` | POST |
| `POST /launcher/jobs/{job_id}/completed` | `POST /runner/jobs/{job_id}/completed` | POST |
| `POST /launcher/jobs/{job_id}/failed` | `POST /runner/jobs/{job_id}/failed` | POST |
| `POST /launcher/jobs/{job_id}/stopped` | `POST /runner/jobs/{job_id}/stopped` | POST |
| `POST /launcher/heartbeat` | `POST /runner/heartbeat` | POST |
| `GET /launchers` | `GET /runners` | GET |
| `DELETE /launchers/{launcher_id}` | `DELETE /runners/{runner_id}` | DELETE |

---

## 5. Python Classes

| Current | New | File |
|---------|-----|------|
| `LauncherConfig` | `RunnerConfig` | agent-launcher/lib/config.py |
| `LauncherInfo` | `RunnerInfo` | agent-runtime/services/launcher_registry.py |
| `LauncherRegistry` | `RunnerRegistry` | agent-runtime/services/launcher_registry.py |
| `LauncherRegisterRequest` | `RunnerRegisterRequest` | agent-runtime/main.py |
| `LauncherRegisterResponse` | `RunnerRegisterResponse` | agent-runtime/main.py |
| `LauncherStopState` | `RunnerStopState` | agent-runtime/services/stop_command_queue.py |

---

## 6. Python Variables & Methods

| Current | New | Context |
|---------|-----|---------|
| `launcher_id` | `runner_id` | Parameters, DB fields, API params |
| `launcher_registry` | `runner_registry` | Service instance |
| `launcher` / `launchers` | `runner` / `runners` | Local variables |
| `get_launcher()` | `get_runner()` | Method |
| `get_all_launchers()` | `get_all_runners()` | Method |
| `is_launcher_alive()` | `is_runner_alive()` | Method |
| `remove_launcher()` | `remove_runner()` | Method |
| `register_launcher()` | `register_runner()` | Method |

---

## 7. TypeScript/React

| Current | New | File |
|---------|-----|------|
| `Launcher` (type) | `Runner` | dashboard/src/types/launcher.ts |
| `LauncherStatus` | `RunnerStatus` | dashboard/src/types/launcher.ts |
| `launcherService` | `runnerService` | dashboard/src/services/launcherService.ts |
| `LauncherCard` | `RunnerCard` | dashboard/src/pages/Launchers.tsx |
| `Launchers` (page) | `Runners` | dashboard/src/pages/Launchers.tsx |

### File Renames

| Current | New |
|---------|-----|
| `dashboard/src/types/launcher.ts` | `dashboard/src/types/runner.ts` |
| `dashboard/src/services/launcherService.ts` | `dashboard/src/services/runnerService.ts` |
| `dashboard/src/pages/Launchers.tsx` | `dashboard/src/pages/Runners.tsx` |

### Routes

| Current | New |
|---------|-----|
| `/launchers` | `/runners` |

---

## 8. Database Fields

| Current | New | Table |
|---------|-----|-------|
| `launcher_id` | `runner_id` | jobs, runner_registry |
| `claimed_by_launcher` | `claimed_by_runner` | job history |

---

## 9. Documentation Files

| File | Approximate Changes |
|------|---------------------|
| `README.md` | ~8 |
| `docs/ARCHITECTURE.md` | ~5 |
| `docs/agent-runtime/API.md` | ~40+ |
| `docs/agent-runtime/JOBS_API.md` | ~30+ |
| `docs/agent-runtime/JOB_EXECUTION_FLOW.md` | ~20+ |
| `docs/agent-runtime/DATA_MODELS.md` | ~15 |
| `docs/adr/ADR-002-agent-launcher-architecture.md` | Rename file |
| `docs/adr/ADR-006-launcher-registration-health-monitoring.md` | Rename file |
| `docs/features/agent-callback-architecture.md` | ~30+ |
| `docs/features/session-stop-command.md` | ~15 |
| `servers/agent-launcher/README.md` | ~40+ |

---

## 10. Log Messages

| Current | New |
|---------|-----|
| `"Registered as {launcher_id}"` | `"Registered as {runner_id}"` |
| `"Launcher started - waiting for jobs"` | `"Runner started - waiting for jobs"` |
| `"Launcher stopped"` | `"Runner stopped"` |
| `"Launcher was deregistered externally"` | `"Runner was deregistered externally"` |
| Logger name `"agent-launcher"` | `"agent-runner"` |

---

## 11. Service File (launcher_registry.py)

**Rename file:** `launcher_registry.py` → `runner_registry.py`

---

## Summary

| Category | Count | Priority |
|----------|-------|----------|
| Directory renames | 2 | Critical |
| API endpoints | 8 | Critical |
| Python classes | 6+ | High |
| TypeScript types/files | 5+ | High |
| Database fields | 3 | High |
| Environment variables | 3 | Medium |
| Code variables | 50+ | Medium |
| Documentation | 14+ files | Medium |
| Log messages | 5+ | Low |

---

## Backward Compatibility

- API endpoint changes break existing launcher clients
- Database migration needed for `runner_id` field
- Consider deprecation period for API versioning
