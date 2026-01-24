# Implementation References

Quick reference for implementing centralized script management.

---

## Documentation

| File | Content | Why Relevant |
|------|---------|--------------|
| `docs/ARCHITECTURE.md` | Core terminology: Agent Blueprint, Session, Run, Runner, Executor | Understand system concepts before implementation |
| `docs/architecture/agent-types.md` | Procedural vs autonomous agents, parameter validation, demand tags | Script execution model mirrors procedural agent patterns |

---

## Agent Coordinator

| Location | Why Relevant |
|----------|--------------|
| `servers/agent-coordinator/main.py` | API endpoints - add `/scripts` routes similar to `/agents` |
| `servers/agent-coordinator/agent_storage.py` | File-based storage - follow same pattern for scripts |
| `servers/agent-coordinator/models.py` | Pydantic models - add Script model |
| `servers/agent-coordinator/services/run_queue.py` | Long-poll response - add sync commands |
| `servers/agent-coordinator/services/runner_registry.py` | Runner tracking - determine which runners need scripts |
| `config/agents/` | Agent folder structure - scripts will mirror this pattern |

---

## Agent Runner

| Location | Why Relevant |
|----------|--------------|
| `servers/agent-runner/agent-runner` | Main runner script - add script sync on startup |
| `servers/agent-runner/lib/poller.py` | Long-poll handling - process sync commands |
| `servers/agent-runner/lib/executor.py` | Executor dispatch - locate synced scripts |
| `servers/agent-runner/lib/executor_config.py` | Profile configuration - scripts directory config |
| `servers/agent-runner/profiles/` | Executor profiles - may need scripts_dir field |
| `servers/agent-runner/executors/procedural-executor/ao-procedural-exec` | Procedural execution - update to use synced scripts |

---

## Dashboard

| Location | Why Relevant |
|----------|--------------|
| `dashboard/src/pages/AgentManager.tsx` | Agent CRUD UI - add Scripts tab, enable procedural editing |
| `dashboard/src/services/agentService.ts` | Agent API calls - add script service |
| `dashboard/src/types/` | TypeScript types - add Script types |

---

## Key Integration Points

1. **Coordinator**: Add `/scripts` CRUD endpoints, download endpoint for sync
2. **Long-poll**: Add `sync_scripts` and `remove_scripts` commands
3. **Runner**: Handle sync commands, store scripts locally
4. **Procedural executor**: Locate scripts in sync directory
5. **Dashboard**: Scripts management UI, procedural agent editing
