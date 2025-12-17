# Refactor Validation Checklist

**Date:** 2025-12-17
**Commits:** 3cf44c7, 35d9ec7, 117c4ad

---

## What Changed

| Old | New | Scope |
|-----|-----|-------|
| Agent Runtime | Agent Coordinator | Server, Docker, Makefile, docs |
| Jobs | Runs | API (`/jobs` → `/runs`), classes, variables |
| Agent Launcher | Agent Runner | Server, API (`/launcher` → `/runner`), dashboard |

---

## Affected Components

| Component | Path | Key Changes |
|-----------|------|-------------|
| **Agent Coordinator** | `servers/agent-coordinator/` | Dir renamed, `main.py`, `run_queue.py`, `runner_registry.py` |
| **Agent Runner** | `servers/agent-runner/` | Dir renamed, `agent-runner` script, `lib/*.py` |
| **Dashboard** | `dashboard/src/` | `Runners.tsx`, `runnerService.ts`, `runner.ts` types |
| **MCP Server** | `mcps/agent-orchestrator/` | API client URLs |
| **Plugin CLI** | `plugins/orchestrator/` | `run_client.py`, command scripts |

---

## Validation Steps

### 1. Compile Checks
```bash
uv run python -m py_compile servers/agent-coordinator/main.py
uv run python -m py_compile servers/agent-coordinator/services/run_queue.py
uv run python -m py_compile servers/agent-coordinator/services/runner_registry.py
```

### 2. Start Services
```bash
# Terminal 1: Coordinator
cd servers/agent-coordinator && uv run python main.py

# Terminal 2: Runner
./servers/agent-runner/agent-runner
```

### 3. API Endpoints
```bash
# New endpoints (should work)
curl http://localhost:8765/runs
curl http://localhost:8765/runners

# Old endpoints (should 404)
curl http://localhost:8765/jobs
curl http://localhost:8765/launchers
```

### 4. Dashboard
```bash
cd dashboard && npm run build
```
- Navigate to `/runners` route
- Check runner appears when started

### 5. Grep Verification
```bash
# Should return NO results in active code
grep -rE "agent-runtime|agent-launcher|/jobs|/launcher/" \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  servers/ dashboard/src/ mcps/ plugins/ \
  | grep -v node_modules | grep -v __pycache__ | grep -v .venv
```

---

## Special Attention

- **API breaking change**: All `/jobs/*` → `/runs/*`, `/launcher/*` → `/runner/*`
- **Field renames**: `job_id` → `run_id`, `launcher_id` → `runner_id`
- **Docker**: Volume `agent-orchestrator-coordinator-data` (was `runtime-data`)
- **Makefile**: Target `restart-coordinator` (was `restart-runtime`)

---

## Cleanup After Validation

Remove these files after all checks pass:
- `terminology.md`
- `terminology_*.md` (3 files)
- `implementation_*.md` (3 files)
- `REFACTOR_VALIDATION.md` (this file)
