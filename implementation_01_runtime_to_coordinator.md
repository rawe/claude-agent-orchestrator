# Implementation Guide: Agent Runtime → Agent Coordinator

**Sequence:** 1 of 3
**Estimated Changes:** ~150-200 references
**Dependencies:** None (do this first)

---

## Context

This is the first of three terminology renames for the Agent Orchestrator Framework. This rename must be completed before the other two.

### What is Agent Runtime?

The central FastAPI server (port 8765) that:
- Manages agent sessions (CRUD, lifecycle, persistence)
- Queues and dispatches runs to Agent Launchers
- Maintains the launcher registry with health monitoring
- Processes callbacks for parent-child session coordination
- Stores and serves agent blueprints
- Broadcasts real-time events via WebSocket
- Persists all data to SQLite

### Why Rename?

"Runtime" implies an execution environment where code runs. This component doesn't execute agents—it **coordinates** them. It's a control plane that orchestrates communication between CLI commands, launchers, dashboard, and MCP servers.

"Coordinator" accurately describes its role: coordinating sessions, jobs, launchers, and callbacks.

---

## Scope

### What Changes

1. Directory names
2. File names
3. Python class/variable names
4. Docker configuration
5. Makefile targets
6. Documentation
7. Dashboard UI text
8. Log messages

### What Does NOT Change

- API endpoint paths (no `/runtime/` paths exist)
- Port number (stays 8765)
- Environment variable `AGENT_ORCHESTRATOR_API_URL` (keep for now, it's generic)
- Database schema

---

## Implementation Checklist

### Phase 1: Directory Renames

```bash
# Main server directory
mv servers/agent-runtime servers/agent-coordinator

# Documentation directory
mv docs/agent-runtime docs/agent-coordinator
```

### Phase 2: Python Code (servers/agent-coordinator/)

#### pyproject.toml
- Line 2: `name = "agent-runtime"` → `name = "agent-coordinator"`

#### main.py
- Line ~85: `title="Agent Runtime"` → `title="Agent Coordinator"`
- Line ~86: Update description to mention "coordinator"

### Phase 3: Agent Launcher Code (servers/agent-launcher/)

#### lib/config.py
- Line 12: `ENV_RUNTIME_URL` → `ENV_COORDINATOR_URL`
- Line 27, 36: `agent_runtime_url` → `agent_coordinator_url`
- Update any comments mentioning "runtime"

#### Other files
- Update comments/docstrings mentioning "Agent Runtime" to "Agent Coordinator"

### Phase 4: Docker Configuration

#### docker-compose.yml
- Line ~29: Service name `agent-runtime` → `agent-coordinator`
- Line ~30: Container name `agent-orchestrator-agent-runtime` → `agent-orchestrator-agent-coordinator`
- Line ~32, 37: Build context `./servers/agent-runtime` → `./servers/agent-coordinator`
- Line ~169: Volume name `agent-orchestrator-runtime-data` → `agent-orchestrator-coordinator-data`
- Update any `depends_on` references

### Phase 5: Makefile

- Line ~210: Target `restart-runtime` → `restart-coordinator`
- Line ~165: Volume reference `agent-orchestrator-runtime-data` → `agent-orchestrator-coordinator-data`
- Update help text and comments (~10+ occurrences)

### Phase 6: Dashboard

#### src/pages/Home.tsx
- Line ~104: Update heading from "Agent Runtime" to "Agent Coordinator"

### Phase 7: MCP Server References

#### mcps/agent-orchestrator/agent-orchestrator-mcp.py
- Line ~32: Update help text "Agent Runtime API URL" → "Agent Coordinator API URL"

#### mcps/agent-orchestrator/libs/
- Update comments and docstrings mentioning "Agent Runtime"

### Phase 8: Plugin References

#### plugins/orchestrator/
- README.md: Update references (~5 occurrences)
- SKILL.md: Update references (~3 occurrences)
- commands/lib/agent_api.py: Update comments

### Phase 9: Documentation

Update all markdown files with "Agent Runtime" → "Agent Coordinator":

| File | Approximate Changes |
|------|---------------------|
| README.md | ~8 |
| docs/ARCHITECTURE.md | ~20+ |
| docs/GETTING_STARTED.md | ~10+ |
| docs/agent-coordinator/README.md | Throughout |
| docs/agent-coordinator/API.md | Throughout |
| docs/agent-coordinator/*.md | Throughout |
| docs/adr/*.md | Various |
| docs/features/*.md | Various |
| servers/agent-launcher/README.md | ~10+ |

### Phase 10: Test Files

- tests/README.md: Update references
- tests/integration/*.md: Update references
- tests/scripts/reset-db: Update comments
- .claude/commands/tests/*.md: Update references

---

## Verification Steps

After completing the rename:

1. **Build check:**
   ```bash
   cd servers/agent-coordinator && uv run python -c "import main"
   ```

2. **Docker check:**
   ```bash
   docker-compose config  # Validates compose file
   ```

3. **Start services:**
   ```bash
   make start  # Or docker-compose up
   ```

4. **Grep verification:**
   ```bash
   # Should return minimal results (only historical references)
   grep -r "agent-runtime" --include="*.py" --include="*.ts" --include="*.md" | grep -v node_modules | grep -v .venv
   ```

---

## Notes

- **Database migration:** The SQLite database path may change if it was in the old directory. Check `.agent-orchestrator/` for data location.
- **Git history:** Consider using `git mv` for directory renames to preserve history.
- **Running services:** Stop all services before renaming directories.

---

## Next Steps

After completing this rename, proceed to:
- **Implementation 2:** Jobs → Agent Runs (`implementation_02_jobs_to_runs.md`)
