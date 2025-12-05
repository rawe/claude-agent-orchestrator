# Environment Variable Refactoring Summary

## Rationale

The Agent Registry service was merged into the Agent Runtime service, creating a single unified backend at port 8765.

**Previously two separate services:**
- `servers/agent-runtime/` (port 8765) - Session and event management
- `servers/agent-registry/` (port 8767) - Agent blueprint management

**Now unified in:**
- `servers/agent-runtime/` (port 8765) - Sessions, events, AND agent blueprints

Previously, there were two separate environment variables pointing to (now) the same service:

- `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` (for sessions)
- `AGENT_ORCHESTRATOR_AGENT_API_URL` (for agent blueprints)

This was confusing and redundant. We consolidated into a single, clearly-named variable.

## Variable Mapping

| Context | Old Variable | New Variable |
|---------|--------------|--------------|
| Python (ao-* commands) | `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` | `AGENT_ORCHESTRATOR_API_URL` |
| Python (ao-* commands) | `AGENT_ORCHESTRATOR_AGENT_API_URL` | `AGENT_ORCHESTRATOR_API_URL` |
| Dashboard (Vite) | `VITE_AGENT_RUNTIME_URL` | `VITE_AGENT_ORCHESTRATOR_API_URL` |

**Default value:** `http://127.0.0.1:8765` (unchanged)

## Files Changed

### Python Code
- `plugins/orchestrator/skills/orchestrator/commands/lib/config.py` - Core config, new `get_api_url()`, `Config.api_url`
- `plugins/orchestrator/skills/orchestrator/commands/lib/agent_api.py` - Imports from config
- `plugins/orchestrator/skills/orchestrator/commands/lib/claude_client.py` - Parameter rename `session_manager_url` → `api_url`
- `plugins/orchestrator/skills/orchestrator/commands/ao-start`
- `plugins/orchestrator/skills/orchestrator/commands/ao-resume`
- `plugins/orchestrator/skills/orchestrator/commands/ao-status`
- `plugins/orchestrator/skills/orchestrator/commands/ao-list-sessions`
- `plugins/orchestrator/skills/orchestrator/commands/ao-list-blueprints`
- `plugins/orchestrator/skills/orchestrator/commands/ao-show-config`
- `plugins/orchestrator/skills/orchestrator/commands/ao-get-result`
- `plugins/orchestrator/skills/orchestrator/commands/ao-delete-all`

### Dashboard (TypeScript)
- `dashboard/src/utils/constants.ts` - Export `AGENT_ORCHESTRATOR_API_URL`
- `dashboard/src/services/api.ts` - Primary `agentOrchestratorApi`, aliases for compatibility
- `dashboard/src/vite-env.d.ts` - Type declaration

### Docker
- `docker-compose.yml` - Dashboard environment
- `dashboard/docker-compose.yml` - Both frontend services

### Environment Templates
- `.env.template` - Added new var documentation
- `dashboard/.env.example` - Updated var name

### Documentation
- `docs/ARCHITECTURE.md`
- `docs/agent-runtime/USAGE.md`
- `docs/agent-runtime/API.md`
- `plugins/orchestrator/README.md`
- `plugins/orchestrator/skills/orchestrator/references/ENV_VARS.md`
- `plugins/orchestrator/skills/orchestrator/references/AGENT-ORCHESTRATOR.md`
- `dashboard/README.md`
- `dashboard/docs/BACKEND-TODO.md`

## Verification

To verify no old references remain:
```bash
grep -r "AGENT_ORCHESTRATOR_SESSION_MANAGER_URL\|AGENT_ORCHESTRATOR_AGENT_API_URL\|VITE_AGENT_RUNTIME_URL\|session_manager_url" --include="*.py" --include="*.ts" --include="*.md" --include="*.yml"
```

## Agent Control API (Chat Tab Fix)

The Dashboard Chat tab requires a separate API for starting/resuming agent sessions. This functionality is provided by the MCP server running in API mode (port 9500), which is not yet merged into agent-runtime.

**New variable added:**
- `VITE_AGENT_CONTROL_API_URL` - Default: `http://localhost:9500`

**Dashboard services now use:**
- `agentOrchestratorApi` (port 8765) - Sessions, events, blueprints
- `agentControlApi` (port 9500) - Start/resume sessions (Chat tab only)

This is a temporary separation until the start/resume functionality is merged into agent-runtime.

## Branch

`claude/merge-registry-into-runtime`
