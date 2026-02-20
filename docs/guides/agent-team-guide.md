# Agent Team Guide

How to structure agent teams for development tasks in this project.

## Team Roles

### Team Lead (you, the main Claude Code session)

The team lead is the orchestrator. It does NOT write code — it manages infrastructure
and coordinates agents.

**Responsibilities:**
- **Start services** as background tasks before any dev work begins
- **Monitor service logs** for errors after each phase of changes
- **Restart services** when Python code changes (coordinator, runner)
- **Create tasks** and assign them to agents
- **Relay issues** between agents (tester finds bug → team lead tells dev)
- **Inform user** about dashboard URL for live verification

**Service startup order:**
```bash
# 1. Coordinator (must start first — others connect to it)
./scripts/start-coordinator.sh    # http://localhost:8765

# 2. Dashboard (Vite, hot reload)
./scripts/start-dashboard.sh      # http://localhost:3000

# 3. Runner (connects to coordinator)
./scripts/start-runner-claude-code.sh
```

### Dev Agent (`general-purpose`, `bypassPermissions`)

Implements all code changes. Uses Edit tool for file modifications.

**Key knowledge:**
- Dashboard (.tsx/.ts) changes are hot-reloaded by Vite — no restart needed
- Coordinator (Python) changes require team lead to restart the service
- Runner (Python) changes require team lead to restart the service
- Never create git commits — team lead handles commits with user approval

### Tester Agent (`general-purpose`, `bypassPermissions`)

Verifies API behavior, TypeScript compilation, and runs integration tests.

**Testing toolkit:**
- API testing: `curl` against `http://localhost:8765`
- API docs: `http://localhost:8765/docs`
- TypeScript check: `cd apps/dashboard && npx tsc --noEmit`
- Integration tests:
  ```bash
  cd servers/agent-runner
  EXECUTOR_UNDER_TEST=executors/claude-code/ao-claude-code-exec \
    uv run --with pytest pytest tests/integration/tests/ -v \
    --ignore=tests/integration/tests/test_resume_mode.py
  ```
- Reports failures to team lead via SendMessage

### Planner Agent (`general-purpose`, plan mode) — optional

Used when a task requires architectural decisions before implementation.
Reads codebase, designs the approach, produces a design document.
Team lead reviews the design with the user before dev agent implements.

## Restart Rules

| Component | Language | Auto-reload? | Restart needed? |
|-----------|----------|-------------|-----------------|
| Coordinator | Python | No | Yes, after any .py change |
| Dashboard | TypeScript | Yes (Vite HMR) | No |
| Runner | Python | No | Yes, after any .py change |

**Runner restart gotcha**: Runner ID is deterministic (hash of hostname + project_dir +
executor_profile). If the coordinator still has the old registration, restart the
coordinator first, then the runner.

## Workflow Template

1. Team lead starts all 3 services as background tasks
2. Team lead creates tasks with dependencies
3. Agents claim and work on tasks in ID order
4. After Python changes: team lead restarts affected services
5. Tester verifies after each phase of dev work
6. User verifies UI at `http://localhost:3000`
7. Team lead commits with user approval
8. Team lead shuts down agents and cleans up team

## Anti-Patterns

- **Don't let agents restart services** — only the team lead manages background tasks
- **Don't skip the tester** — always verify API + TypeScript + integration tests
- **Don't commit without user approval** — present changes and wait
- **Don't implement without planning** — for non-trivial API/protocol changes, use a
  planner agent first
