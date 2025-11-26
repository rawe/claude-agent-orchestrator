# Implementation Plan: Agent Manager API

**Principles:** KISS, YAGNI, No backward compatibility hacks
**Tooling:** uv for Python dependency management

---

## Phase 1: Agent Manager Backend Service

### 1.1 Create Service Structure

**Directory:** `agent-orchestrator-backend/`

**Files:**
```
agent-orchestrator-backend/
├── main.py              # FastAPI app (port 8767)
├── models.py            # Pydantic models
├── agent_storage.py     # File I/O for agents
├── validation.py        # Name/config validation
├── pyproject.toml       # Dependencies (uv compatible)
└── Dockerfile           # Container build (uses uv)
```

### 1.2 Implement Files

**agent_storage.py:**
- `get_agents_dir()` - from env or default
- `list_agents()` - scan dirs, read agent.json, check .disabled
- `get_agent(name)` - read agent.json + agent.system-prompt.md + agent.mcp.json
- `create_agent(agent)` - create dir, write files
- `update_agent(name, updates)` - partial update files
- `delete_agent(name)` - remove directory
- `set_agent_status(name, status)` - create/remove .disabled

**models.py:**
```python
MCPServerConfig: command, args, env (optional)
AgentBase: name, description
AgentCreate: + system_prompt, mcp_servers, skills (all optional)
AgentUpdate: description, system_prompt, mcp_servers, skills (all optional)
Agent: full model with status, created_at, modified_at
AgentStatusUpdate: status literal
```

**validation.py:**
- `validate_agent_name(name)` - 1-60 chars, alphanumeric + hyphen/underscore
- `validate_unique_name(name, agents_dir)` - check dir doesn't exist
- `validate_mcp_servers(mcp_servers)` - validate structure

**main.py - Endpoints:**
```
GET  /health                    -> {"status": "healthy"}
GET  /agents                    -> [Agent, ...]
GET  /agents/{name}             -> Agent | 404
POST /agents                    -> 201 Agent | 400 | 409
PATCH /agents/{name}            -> Agent | 404
DELETE /agents/{name}           -> 204 | 404
PATCH /agents/{name}/status     -> Agent | 404
```

CORS: localhost:5173, localhost:3000

### 1.3 Docker Setup

**Dockerfile** - Python 3.11 slim, uv for deps, uvicorn
- Follow pattern from `plugins/document-sync/document-server/Dockerfile`
- Uses `uv pip install --system -e .`

**docker-compose.yml** - Add agent-manager service on port 8767
- Mount agents dir from host for file persistence
- Add to agent-orchestrator-network

---

## Phase 2: Update CLI Commands

### 2.1 Create API Client

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/agent_api.py`

```python
def get_api_url() -> str:
    # AGENT_ORCHESTRATOR_AGENT_API_URL or default "http://localhost:8767"

def list_agents_api() -> list[dict]:
    # GET /agents, raise on connection error

def get_agent_api(name: str) -> dict | None:
    # GET /agents/{name}, return None on 404
```

Clean error messages when API unavailable.

### 2.2 Update ao-list-agents

Replace file-based `list_all_agents()` with `list_agents_api()`.

### 2.3 Update ao-new

Replace `load_agent_config()` with `get_agent_api()`.

---

## Phase 3: Update Frontend

### 3.1 Update Types

**File:** `src/types/agent.ts`

Change `mcp_servers: string[]` to:
```typescript
mcp_servers: Record<string, MCPServerConfig> | null
```

Add `MCPServerConfig` interface.

### 3.2 Replace Mock Service

**File:** `src/services/agentService.ts`

Remove all mock data. Call `agentApi` directly:
- `listAgents()` -> GET /agents
- `getAgent(name)` -> GET /agents/{name}
- `createAgent(data)` -> POST /agents
- `updateAgent(name, data)` -> PATCH /agents/{name}
- `deleteAgent(name)` -> DELETE /agents/{name}
- `updateAgentStatus(name, status)` -> PATCH /agents/{name}/status

### 3.3 Add MCP JSON Editor (Simple)

**File:** `src/components/features/agents/MCPJsonEditor.tsx`

Simple textarea with:
- JSON.parse validation on change
- Error display for invalid JSON
- Placeholder with example

### 3.4 Add MCP Templates

**File:** `src/utils/mcpTemplates.ts`

Two example templates:
- `playwright` - npx @playwright/mcp@latest
- `brave-search` - with env var placeholder

Include comment on how to add more templates.

### 3.5 Update AgentEditor

Replace MCP checkbox presets with:
- Template dropdown/buttons (2 templates)
- Textarea JSON editor
- Validation error display

### 3.6 Environment Config

**File:** `.env.example`
```
VITE_AGENT_MANAGER_URL=http://localhost:8767
```

---

## Phase 4: Testing

Manual checklist:
- [ ] Backend: all CRUD endpoints work
- [ ] Backend: .disabled file toggles status
- [ ] CLI: ao-list-agents shows agents from API
- [ ] CLI: ao-new --agent loads config from API
- [ ] Frontend: list/create/edit/delete agents
- [ ] Frontend: status toggle works
- [ ] Frontend: MCP JSON editor validates

---

## Implementation Order

1. `agent-orchestrator-backend/` - all files
2. Dockerfile + docker-compose.yml update
3. Test backend with curl
4. `lib/agent_api.py` - API client
5. Update `ao-list-agents`
6. Update `ao-new`
7. Test CLI
8. Update `src/types/agent.ts`
9. Update `src/services/agentService.ts`
10. Create `MCPJsonEditor.tsx`
11. Create `mcpTemplates.ts`
12. Update `AgentEditor.tsx`
13. End-to-end test

---

## Deviations from Original Plan

See `DEFERRED.md` for features not implemented in this iteration.
