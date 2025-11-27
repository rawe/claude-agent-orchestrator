# Package 03: Agent Registry

## Goal
Move agent backend into `/servers/agent-registry/`.

## Source → Target
```
agent-orchestrator-backend/ → servers/agent-registry/
```

## Steps

1. **Create target directory**
   - Create `/servers/agent-registry/`

2. **Move server files**
   - Move all files from `agent-orchestrator-backend/` → `servers/agent-registry/`

3. **Update server identity**
   - Update `pyproject.toml`: name = `agent-registry`
   - Update `main.py`: FastAPI title = "Agent Registry"

4. **Update dashboard references**
   - Update `dashboard/src/utils/constants.ts`: rename variable to `AGENT_REGISTRY_URL`
   - Update `dashboard/src/services/api.ts`: rename axios instance

5. **Update Makefile**
   - Change agent-backend target path to `servers/agent-registry/`

6. **Update docker-compose.yml**
   - Change build context to `./servers/agent-registry`
   - Rename service to `agent-registry`

7. **Delete old location**
   - Remove `agent-orchestrator-backend/`

## Verification
- Start Agent Registry server from new location
- Dashboard agent management → should work unchanged
- ao-list-agents command → should work unchanged

## References
- Target structure: See [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure) → `/servers/agent-registry/`
- Component details: See [ARCHITECTURE.md](./ARCHITECTURE.md#agent-registry)
