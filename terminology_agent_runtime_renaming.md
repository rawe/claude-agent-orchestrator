# Agent Runtime → Agent Coordinator: Renaming Analysis

This document catalogs all occurrences of "Agent Runtime" terminology that need to be renamed when transitioning to "Agent Coordinator".

---

## 1. Directory & File Names

| Current | New | Location | Type |
|---------|-----|----------|------|
| `servers/agent-runtime/` | `servers/agent-coordinator/` | Root servers directory | Directory |
| `docs/agent-runtime/` | `docs/agent-coordinator/` | Documentation directory | Directory |

**Files inside agent-runtime directory:**
- `main.py` - FastAPI app title (line 85: `title="Agent Runtime"`)
- `README.md` - Server documentation
- `pyproject.toml` - Project name: "agent-runtime" (line 2)

---

## 2. Documentation Files to Rename

| Current Path | New Path |
|--------------|----------|
| `docs/agent-runtime/API.md` | `docs/agent-coordinator/API.md` |
| `docs/agent-runtime/USAGE.md` | `docs/agent-coordinator/USAGE.md` |
| `docs/agent-runtime/JOBS_API.md` | `docs/agent-coordinator/JOBS_API.md` |
| `docs/agent-runtime/JOB_EXECUTION_FLOW.md` | `docs/agent-coordinator/JOB_EXECUTION_FLOW.md` |
| `docs/agent-runtime/DATABASE_SCHEMA.md` | `docs/agent-coordinator/DATABASE_SCHEMA.md` |
| `docs/agent-runtime/DATA_MODELS.md` | `docs/agent-coordinator/DATA_MODELS.md` |
| `docs/agent-runtime/README.md` | `docs/agent-coordinator/README.md` |

---

## 3. Environment Variables

| Current | New | Decision |
|---------|-----|----------|
| `AGENT_ORCHESTRATOR_API_URL` | Keep or `AGENT_COORDINATOR_API_URL` | Optional - generic name works |
| `VITE_AGENT_ORCHESTRATOR_API_URL` | Keep or rename | Optional - frontend config |

**Note:** These are generic and not specific to "runtime". Renaming is optional.

---

## 4. Code Variables & Functions

| Current | New | File | Line |
|---------|-----|------|------|
| `agent_runtime_url` | `agent_coordinator_url` | `servers/agent-launcher/lib/config.py` | 27, 36 |
| `ENV_RUNTIME_URL` | `ENV_COORDINATOR_URL` | `servers/agent-launcher/lib/config.py` | 12 |
| `title="Agent Runtime"` | `title="Agent Coordinator"` | `servers/agent-runtime/main.py` | 85 |

---

## 5. Docker Configuration

| Current | New | File | Line |
|---------|-----|------|------|
| `agent-runtime` (service) | `agent-coordinator` | `docker-compose.yml` | 29 |
| `agent-orchestrator-agent-runtime` | `agent-orchestrator-agent-coordinator` | `docker-compose.yml` | 30 |
| `./servers/agent-runtime` | `./servers/agent-coordinator` | `docker-compose.yml` | 32, 37 |
| `agent-orchestrator-runtime-data` | `agent-orchestrator-coordinator-data` | `docker-compose.yml` | 169 |

---

## 6. Makefile Targets

| Current | New | Line |
|---------|-----|------|
| `restart-runtime` | `restart-coordinator` | 210 |
| `agent-orchestrator-runtime-data` | `agent-orchestrator-coordinator-data` | 165 |
| Help text references | Update all | 25, 98, 118+ |

---

## 7. Dashboard References

| File | Current | New |
|------|---------|-----|
| `dashboard/src/pages/Home.tsx` | "Agent Runtime" | "Agent Coordinator" (line 104) |

---

## 8. CLI & Launcher Code

| File | Change |
|------|--------|
| `servers/agent-launcher/agent-launcher` | Help text (lines 10, 12, 20) |
| `servers/agent-launcher/README.md` | 10+ occurrences |
| `servers/agent-launcher/lib/config.py` | Variable rename |
| `servers/agent-launcher/lib/poller.py` | Log messages |

---

## 9. MCP Server References

| File | Change |
|------|--------|
| `mcps/agent-orchestrator/agent-orchestrator-mcp.py` | Help text (line 32) |
| `mcps/agent-orchestrator/libs/core_functions.py` | Comments |
| `mcps/agent-orchestrator/libs/api_client.py` | Docstrings |

---

## 10. Plugin Files

| File | Occurrences |
|------|-------------|
| `plugins/orchestrator/README.md` | 5+ |
| `plugins/orchestrator/SKILL.md` | 3+ |
| `plugins/orchestrator/skills/orchestrator/commands/lib/agent_api.py` | 1 |

---

## 11. Test Files

| File | Change |
|------|--------|
| `tests/README.md` | 8+ references |
| `tests/integration/*.md` | 6+ references |
| `tests/scripts/reset-db` | 2+ comments |
| `.claude/commands/tests/*.md` | 5+ references |

---

## 12. Architecture Documentation

| File | Action |
|------|--------|
| `tickets/arch-001-project-structure/04-agent-runtime.md` | Rename to `04-agent-coordinator.md` |
| `docs/ARCHITECTURE.md` | 20+ references |
| `docs/GETTING_STARTED.md` | 10+ references |

---

## Summary

| Category | Count | Priority |
|----------|-------|----------|
| Directory renames | 2 | Critical |
| Docker configuration | 6+ | Critical |
| Documentation files | 7+ | High |
| Code variables | 10+ | High |
| Comments & docstrings | 80+ | Medium |
| Makefile targets | 10+ | Medium |
| UI text | 5+ | Medium |
| Environment variables | Optional | Low |

**Total:** ~150-200 references across the codebase.

---

## Critical Considerations

1. **Database volume**: Renaming `agent-orchestrator-runtime-data` requires data migration
2. **Docker dependencies**: Update `depends_on: - agent-runtime` references
3. **Backwards compatibility**: Consider keeping `AGENT_ORCHESTRATOR_API_URL` as alias
4. **Port 8765**: Remains unchanged (it's infrastructure, not terminology)
