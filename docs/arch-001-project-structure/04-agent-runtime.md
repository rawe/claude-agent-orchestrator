# Package 04: Agent Runtime

## Goal
Move observability backend into `/servers/agent-runtime/`.

## Source → Target
```
agent-orchestrator-observability/backend/ → servers/agent-runtime/
```

## Steps

1. **Create target directory**
   - Create `/servers/agent-runtime/`

2. **Move server files**
   - Move all files from `agent-orchestrator-observability/backend/` → `servers/agent-runtime/`

3. **Update server identity**
   - Update `pyproject.toml`: name = `agent-runtime`
   - Update `main.py`: FastAPI title = "Agent Runtime"

4. **Update dashboard references**
   - Update `dashboard/src/utils/constants.ts`: rename variable to `AGENT_RUNTIME_URL`
   - Update `dashboard/src/services/api.ts`: rename axios instance

5. **Update ao-* command references**
   - Update `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/session_client.py`: server URL
   - Update `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/config.py`: if URL configured there

6. **Update Makefile**
   - Change observability-backend target path to `servers/agent-runtime/`

7. **Update docker-compose.yml**
   - Change build context to `./servers/agent-runtime`
   - Rename service to `agent-runtime`

8. **Delete old location**
   - Remove `agent-orchestrator-observability/backend/`
   - Remove `agent-orchestrator-observability/` if now empty (frontend already deprecated)

## Verification
- Start Agent Runtime server from new location
- Dashboard sessions/events → should work unchanged
- All ao-* commands → should work unchanged
- WebSocket connection → should work unchanged

## References
- Target structure: See [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure) → `/servers/agent-runtime/`
- Component details: See [ARCHITECTURE.md](./ARCHITECTURE.md#agent-runtime)
