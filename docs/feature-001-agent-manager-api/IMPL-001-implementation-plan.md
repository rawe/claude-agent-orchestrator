# IMPL-001: Agent Manager Service Implementation Plan

**Status:** Approved
**Date:** 2025-11-25
**Principles:** KISS, YAGNI

---

## Goal

Create an **Agent Manager API Service** that provides HTTP endpoints for agent CRUD operations and status management. Python CLI commands will consume this API, and the unified frontend will use the same endpoints. File-based storage remains unchanged for 100% backwards compatibility.

---

## Architectural Approach

### Core Principles
- **File-based storage:** Continue using `.agent-orchestrator/agents/{name}/` structure
- **API-first:** Python CLI commands call HTTP API (port 8767)
- **Signal file for status:** `.disabled` file indicates inactive agent
- **Minimal abstraction:** Simple file operations wrapper, no complex ORM
- **Shared validation:** Single source of truth for agent validation rules

### System Flow
```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Python CLI │ ──HTTP─→│ Agent Manager    │ ──R/W─→ │  File System    │
│  Commands   │         │ Service :8767    │         │  .agent-orch... │
└─────────────┘         └──────────────────┘         └─────────────────┘
                                  ↑
                                  │ HTTP
                                  │
                        ┌─────────────────┐
                        │ Unified         │
                        │ Frontend        │
                        └─────────────────┘
```

---

## Implementation Steps

### Phase 1: Agent Manager Service (New)

#### 1.1 Create Service Structure

**Directory:** `/agent-orchestrator-backend/`

**Files to create:**
```
agent-orchestrator-backend/
├── main.py              # FastAPI app
├── models.py            # Pydantic models
├── agent_storage.py     # File I/O abstraction
├── validation.py        # Agent validation rules
├── requirements.txt     # Dependencies
└── README.md            # Service documentation
```

**Why:** Clean separation, matches existing backend services pattern

---

#### 1.2 Implement File Storage Abstraction

**File:** `agent-orchestrator-backend/agent_storage.py`

**Purpose:** Centralize all file I/O operations for agents

**Functions needed:**
```python
def get_agents_dir() -> Path
    # Read AGENT_ORCHESTRATOR_AGENTS_DIR env var
    # Default: {project_dir}/.agent-orchestrator/agents

def list_agents() -> List[Agent]
    # Scan agents directory
    # For each agent folder, read agent.json
    # Check for .disabled file
    # Return list of Agent objects

def get_agent(name: str) -> Agent | None
    # Read agent.json (name, description, skills)
    # Read agent.system-prompt.md if exists
    # Read agent.mcp.json if exists → parse mcpServers dict
    # Check for .disabled file → set status
    # Return Agent object or None

def create_agent(agent: AgentCreate) -> Agent
    # Validate name (alphanumeric + hyphens, unique)
    # Create {agents_dir}/{name}/ directory
    # Write agent.json with name, description, skills (if provided)
    # Write agent.system-prompt.md if provided
    # Write agent.mcp.json with {"mcpServers": {...}} if mcp_servers provided
    # Return created Agent

def update_agent(name: str, updates: AgentUpdate) -> Agent
    # Read existing agent
    # Apply partial updates to JSON files
    # Return updated Agent

def delete_agent(name: str) -> bool
    # Remove entire {agents_dir}/{name}/ directory
    # Return success/failure

def set_agent_status(name: str, status: str) -> Agent
    # If status == "inactive": create .disabled file
    # If status == "active": remove .disabled file
    # Return updated Agent
```

**Why:** Single responsibility, easy to test, reusable

---

#### 1.3 Define Data Models

**File:** `agent-orchestrator-backend/models.py`

**Models:**
```python
class MCPServerConfig(BaseModel):
    """MCP server configuration matching agent.mcp.json structure"""
    command: str
    args: list[str]
    env: dict[str, str] | None = None

class AgentBase(BaseModel):
    name: str
    description: str

class AgentCreate(AgentBase):
    system_prompt: str | None = None
    mcp_servers: dict[str, MCPServerConfig] | None = None  # Full MCP config from agent.mcp.json
    skills: list[str] | None = None  # Skills array (e.g., ["pdf", "xlsx"])

class AgentUpdate(BaseModel):
    description: str | None = None
    system_prompt: str | None = None
    mcp_servers: dict[str, MCPServerConfig] | None = None
    skills: list[str] | None = None

class Agent(AgentBase):
    system_prompt: str | None = None
    mcp_servers: dict[str, MCPServerConfig] | None = None  # Full config with command, args, env
    skills: list[str] | None = None
    status: Literal["active", "inactive"] = "active"
    created_at: str
    modified_at: str

class AgentStatusUpdate(BaseModel):
    status: Literal["active", "inactive"]
```

**Example MCP Servers Structure:**
```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest"]
  },
  "brave-search": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "${BRAVE_API_KEY}"
    }
  }
}
```

**Why:** Type safety, validation, API contract definition

---

#### 1.4 Implement Validation

**File:** `agent-orchestrator-backend/validation.py`

**Functions:**
```python
def validate_agent_name(name: str) -> None:
    # Length: 1-60 characters
    # Pattern: alphanumeric, hyphens, underscores only
    # Raise ValueError if invalid

def validate_unique_name(name: str, agents_dir: Path) -> None:
    # Check if {agents_dir}/{name}/ exists
    # Raise ValueError if exists

def validate_mcp_servers(mcp_servers: dict | None) -> None:
    # Validate MCP server config structure
    # Each server must have: command (str), args (list[str])
    # Optional: env (dict[str, str])
    # Raise ValueError if invalid schema
```

**Why:** Consistent validation between API and CLI, fail fast

---

#### 1.5 Create FastAPI Endpoints

**File:** `agent-orchestrator-backend/main.py`

**Endpoints:**

```python
# Health check
GET /health
→ {"status": "healthy"}

# List all agents
GET /agents
→ [Agent, Agent, ...]

# Get single agent
GET /agents/{name}
→ Agent
→ 404 if not found

# Create agent
POST /agents
Body: AgentCreate
→ 201, Agent
→ 400 if validation fails
→ 409 if name already exists

# Update agent (partial)
PATCH /agents/{name}
Body: AgentUpdate
→ 200, Agent
→ 404 if not found

# Delete agent
DELETE /agents/{name}
→ 204 No Content
→ 404 if not found

# Update status
PATCH /agents/{name}/status
Body: AgentStatusUpdate
→ 200, Agent
→ 404 if not found
```

**CORS:** Enable for `http://localhost:5173`, `http://localhost:3000`

**Error handling:** Return proper HTTP status codes and error messages

**Why:** RESTful design, standard HTTP semantics

---

#### 1.6 Configuration

**File:** `agent-orchestrator-backend/main.py`

**Environment variables:**
```python
AGENT_MANAGER_HOST = "0.0.0.0"          # Allow Docker networking
AGENT_MANAGER_PORT = 8767
AGENT_ORCHESTRATOR_PROJECT_DIR = CWD    # Default to current dir
AGENT_ORCHESTRATOR_AGENTS_DIR = None    # Optional override
```

**Why:** Consistent with existing services, Docker-compatible

---

### Phase 2: Update Python CLI Commands

**Scope:** CLI commands only **read** agent data from API (for listing and loading). Agent creation/editing/deletion is done exclusively via frontend UI or direct file editing.

#### 2.1 Create API Client

**File:** `/plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/agent_api.py`

**Purpose:** HTTP client for Agent Manager Service

**Functions:**
```python
def get_api_url() -> str:
    # Read AGENT_ORCHESTRATOR_AGENT_API_URL env var
    # Default: "http://localhost:8767"

def list_agents_api() -> List[dict]:
    # GET {api_url}/agents
    # Return JSON response

def get_agent_api(name: str) -> dict | None:
    # GET {api_url}/agents/{name}
    # Return agent or None if 404

# Note: Agent creation/editing is done via frontend UI only
# No create/update/delete functions needed in CLI client
```

**Error handling:**
- Catch connection errors → friendly message "Agent Manager Service not running on port 8767"
- Wrap HTTP errors → raise appropriate exceptions

**Why:** Centralized HTTP logic, easier to test

---

#### 2.2 Update `ao-list-agents`

**File:** `/plugins/agent-orchestrator/skills/agent-orchestrator/commands/ao-list-agents`

**Changes:**
```python
# OLD:
from lib.agent import list_all_agents
agents = list_all_agents(config.agents_dir)

# NEW:
from lib.agent_api import list_agents_api
agents = list_agents_api()
```

**Fallback (optional):**
```python
try:
    agents = list_agents_api()
except ConnectionError:
    if "--local" in sys.argv:
        # Fall back to file-based
        from lib.agent import list_all_agents
        agents = list_all_agents(config.agents_dir)
    else:
        print("Error: Agent Manager Service not running")
        print("Start with: cd agent-orchestrator-backend && uvicorn main:app --port 8767")
        sys.exit(1)
```

**Why:** Minimal change, maintains existing output format

---

#### 2.3 Update `ao-new` Command

**File:** `/plugins/agent-orchestrator/skills/agent-orchestrator/commands/ao-new`

**Changes:**
```python
# When --agent flag is used:
# OLD:
from lib.agent import load_agent_config
agent_config = load_agent_config(agent_name, config.agents_dir)

# NEW:
from lib.agent_api import get_agent_api
agent_data = get_agent_api(agent_name)
if not agent_data:
    print(f"Error: Agent '{agent_name}' not found")
    sys.exit(1)

# Convert API response to format expected by claude_client.py
agent_config = {
    "system_prompt": agent_data.get("system_prompt"),
    "mcp_servers": agent_data.get("mcp_servers"),
}
```

**Why:** Consistent agent loading from API

**Note:** Agent creation/editing is done via the frontend UI or direct file editing. No CLI commands for agent management are needed.

---

### Phase 3: Update Frontend

#### 3.1 Create Agent API Client

**File:** `agent-orchestrator-frontend/src/services/agentApi.ts`

**Purpose:** TypeScript client for Agent Manager Service

**Implementation:**
```typescript
const API_BASE = import.meta.env.VITE_AGENT_MANAGER_URL || 'http://localhost:8767';

export interface MCPServerConfig {
  command: string;
  args: string[];
  env?: Record<string, string>;
}

export interface Agent {
  name: string;
  description: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;  // Full MCP config
  skills?: string[] | null;                              // Skills array
  status: 'active' | 'inactive';
  created_at: string;
  modified_at: string;
}

export interface AgentCreate {
  name: string;
  description: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[] | null;
}

export interface AgentUpdate {
  description?: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[] | null;
}

export const agentApi = {
  async listAgents(): Promise<Agent[]> {
    const res = await fetch(`${API_BASE}/agents`);
    if (!res.ok) throw new Error('Failed to fetch agents');
    return res.json();
  },

  async getAgent(name: string): Promise<Agent> {
    const res = await fetch(`${API_BASE}/agents/${name}`);
    if (!res.ok) throw new Error(`Agent not found: ${name}`);
    return res.json();
  },

  async createAgent(data: AgentCreate): Promise<Agent> {
    const res = await fetch(`${API_BASE}/agents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create agent');
    return res.json();
  },

  async updateAgent(name: string, data: AgentUpdate): Promise<Agent> {
    const res = await fetch(`${API_BASE}/agents/${name}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update agent');
    return res.json();
  },

  async deleteAgent(name: string): Promise<void> {
    const res = await fetch(`${API_BASE}/agents/${name}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete agent');
  },

  async updateStatus(name: string, status: 'active' | 'inactive'): Promise<Agent> {
    const res = await fetch(`${API_BASE}/agents/${name}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error('Failed to update status');
    return res.json();
  },
};
```

**Why:** Type-safe API client, reusable across frontend

---

#### 3.2 Update Frontend Data Types

**File:** `agent-orchestrator-frontend/src/types/agent.ts`

**Changes:**
```typescript
// Update existing types to match backend
export interface MCPServerConfig {
  command: string;
  args: string[];
  env?: Record<string, string>;
}

export interface Agent {
  name: string;
  description: string;
  system_prompt: string;
  mcp_servers: Record<string, MCPServerConfig> | null;  // CHANGED: Full config, not string[]
  skills: string[] | null;                              // Keep skills field
  status: AgentStatus;
  created_at: string;
  modified_at: string;  // CHANGED: renamed from updated_at
}
```

**Why:** Match backend API contract exactly

---

#### 3.3 Replace Mock Service with Real API

**File:** `agent-orchestrator-frontend/src/services/agentService.ts`

**Changes:**
```typescript
// REMOVE: All mock data and in-memory array
// REMOVE: Simulated delay logic

// REPLACE WITH: Real API calls using axios
import { agentApi } from './api';
import type { Agent, AgentCreate, AgentUpdate } from '../types/agent';

export const agentService = {
  async listAgents(): Promise<Agent[]> {
    const response = await agentApi.get('/agents');
    return response.data;
  },

  async getAgent(name: string): Promise<Agent> {
    const response = await agentApi.get(`/agents/${name}`);
    return response.data;
  },

  async createAgent(data: AgentCreate): Promise<Agent> {
    const response = await agentApi.post('/agents', data);
    return response.data;
  },

  async updateAgent(name: string, data: AgentUpdate): Promise<Agent> {
    const response = await agentApi.patch(`/agents/${name}`, data);
    return response.data;
  },

  async deleteAgent(name: string): Promise<void> {
    await agentApi.delete(`/agents/${name}`);
  },

  async updateAgentStatus(name: string, status: 'active' | 'inactive'): Promise<Agent> {
    const response = await agentApi.patch(`/agents/${name}/status`, { status });
    return response.data;
  },

  async checkNameAvailable(name: string): Promise<boolean> {
    try {
      await agentApi.get(`/agents/${name}`);
      return false; // Agent exists
    } catch (error) {
      return true; // 404 = name available
    }
  },
};
```

**Why:** Replace mock with real HTTP calls

---

#### 3.4 Add MCP JSON Editor Component

**File (new):** `agent-orchestrator-frontend/src/components/features/agents/MCPEditor.tsx`

**Purpose:** JSON editor for MCP server configuration with validation

**Dependencies:**
```bash
npm install @monaco-editor/react
```

**Implementation:**
```typescript
import Editor from '@monaco-editor/react';
import { useState } from 'react';

interface MCPEditorProps {
  value: Record<string, any> | null;
  onChange: (value: Record<string, any> | null) => void;
  error?: string;
}

export function MCPEditor({ value, onChange, error }: MCPEditorProps) {
  const [jsonError, setJsonError] = useState<string | null>(null);

  const handleChange = (newValue: string | undefined) => {
    if (!newValue) {
      onChange(null);
      setJsonError(null);
      return;
    }

    try {
      const parsed = JSON.parse(newValue);
      onChange(parsed);
      setJsonError(null);
    } catch (e) {
      setJsonError('Invalid JSON syntax');
    }
  };

  return (
    <div>
      <Editor
        height="300px"
        language="json"
        value={value ? JSON.stringify(value, null, 2) : ''}
        onChange={handleChange}
        options={{
          minimap: { enabled: false },
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          fontSize: 14,
        }}
      />
      {(jsonError || error) && (
        <p className="text-red-500 text-sm mt-2">{jsonError || error}</p>
      )}
    </div>
  );
}
```

**Why:** User-friendly JSON editing with syntax highlighting and validation

---

#### 3.5 Add MCP Templates Helper

**File (new):** `agent-orchestrator-frontend/src/utils/mcpTemplates.ts`

**Purpose:** Common MCP server templates for quick insertion

**Implementation:**
```typescript
import type { MCPServerConfig } from '../types/agent';

export const MCP_TEMPLATES: Record<string, MCPServerConfig> = {
  playwright: {
    command: 'npx',
    args: ['@playwright/mcp@latest'],
  },
  github: {
    command: 'npx',
    args: ['@modelcontextprotocol/server-github'],
    env: {
      GITHUB_PERSONAL_ACCESS_TOKEN: '${GITHUB_PERSONAL_ACCESS_TOKEN}',
    },
  },
  'brave-search': {
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-brave-search'],
    env: {
      BRAVE_API_KEY: '${BRAVE_API_KEY}',
    },
  },
  filesystem: {
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-filesystem', '/path/to/allowed/directory'],
  },
  postgres: {
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-postgres'],
    env: {
      POSTGRES_CONNECTION_STRING: '${POSTGRES_CONNECTION_STRING}',
    },
  },
  sqlite: {
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-sqlite', '/path/to/database.db'],
  },
  slack: {
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-slack'],
    env: {
      SLACK_BOT_TOKEN: '${SLACK_BOT_TOKEN}',
    },
  },
};

export const TEMPLATE_NAMES = Object.keys(MCP_TEMPLATES);

export function getTemplate(name: string): MCPServerConfig | null {
  return MCP_TEMPLATES[name] || null;
}

export function addTemplate(
  existing: Record<string, MCPServerConfig> | null,
  templateName: string
): Record<string, MCPServerConfig> {
  const template = getTemplate(templateName);
  if (!template) return existing || {};

  return {
    ...(existing || {}),
    [templateName]: template,
  };
}
```

**Why:** Simplify common MCP server additions without requiring preset UI

---

#### 3.6 Update AgentEditor Component

**File:** `agent-orchestrator-frontend/src/components/features/agents/AgentEditor.tsx`

**Changes:**

1. **Replace MCP preset checkboxes with JSON editor:**
```typescript
import { MCPEditor } from './MCPEditor';
import { MCP_TEMPLATES, TEMPLATE_NAMES, addTemplate } from '../../../utils/mcpTemplates';

// Remove old preset checkbox UI
// Add JSON editor + template buttons

<div className="space-y-2">
  <label className="block text-sm font-medium">MCP Servers (Optional)</label>

  {/* Template Quick Add Buttons */}
  <div className="flex flex-wrap gap-2 mb-2">
    <span className="text-xs text-gray-500">Quick add:</span>
    {TEMPLATE_NAMES.map(name => (
      <button
        key={name}
        type="button"
        onClick={() => {
          const updated = addTemplate(formData.mcp_servers, name);
          setFormData({ ...formData, mcp_servers: updated });
        }}
        className="px-2 py-1 text-xs bg-blue-50 hover:bg-blue-100 rounded"
      >
        + {name}
      </button>
    ))}
  </div>

  {/* JSON Editor */}
  <MCPEditor
    value={formData.mcp_servers}
    onChange={(value) => setFormData({ ...formData, mcp_servers: value })}
    error={errors.mcp_servers}
  />

  <p className="text-xs text-gray-500">
    MCP servers configuration. Use templates above or edit JSON directly.
  </p>
</div>
```

2. **Keep skills as simple checkboxes (works well):**
```typescript
// Keep existing skills UI - no changes needed
// Skills remain as simple string array
```

**Why:** Progressive enhancement - templates for convenience, JSON for power users

---

#### 3.7 Update Environment Configuration

**File:** `agent-orchestrator-frontend/.env.example`

**Add:**
```bash
VITE_AGENT_MANAGER_URL=http://localhost:8767
```

**File:** `agent-orchestrator-frontend/README.md`

**Update:** Document new environment variable and Agent Manager Service requirement

**Why:** Configuration visibility, deployment guidance

---

### Phase 4: Testing & Validation

#### 4.1 Manual Testing Checklist

**Agent Manager Service:**
- [ ] Service starts on port 8767
- [ ] GET /agents returns existing agents
- [ ] GET /agents/{name} returns 404 for non-existent agent
- [ ] POST /agents creates new agent with all files
- [ ] POST /agents validates name format
- [ ] POST /agents returns 409 for duplicate name
- [ ] PATCH /agents/{name} updates agent files
- [ ] DELETE /agents/{name} removes directory
- [ ] PATCH /agents/{name}/status creates/removes .disabled file
- [ ] CORS headers present for frontend origin

**Python CLI:**
- [ ] ao-list-agents calls API and displays agents
- [ ] ao-list-agents shows friendly error if service not running
- [ ] ao-new --agent={name} loads agent config from API
- [ ] Inactive agents are filtered out (status check via .disabled file)

**Frontend:**
- [ ] Agents page fetches real data from API
- [ ] Create agent form works
- [ ] Edit agent works (JSON editor for MCP servers)
- [ ] Delete agent works
- [ ] Toggle status works
- [ ] MCP JSON editor validates syntax
- [ ] MCP template buttons add correct config
- [ ] Skills checkboxes work
- [ ] Loading states shown
- [ ] Error states handled

**Backwards Compatibility:**
- [ ] Existing file-based agents load correctly
- [ ] Agent files remain Git-trackable
- [ ] Directory structure unchanged

**Why:** Systematic validation, catch regressions early

---

## File Changes Summary

### New Files (Create)
```
agent-orchestrator-backend/
├── main.py                    # FastAPI service
├── models.py                  # Data models
├── agent_storage.py           # File I/O
├── validation.py              # Validation rules
├── requirements.txt           # FastAPI, pydantic, uvicorn
└── README.md

plugins/.../commands/
└── lib/agent_api.py           # HTTP client for loading agents

agent-orchestrator-frontend/src/
├── services/agentApi.ts               # TypeScript API client (already exists)
├── components/features/agents/
│   └── MCPEditor.tsx                  # JSON editor for MCP config
└── utils/mcpTemplates.ts              # MCP server templates
```

### Modified Files
```
plugins/.../commands/
├── ao-list-agents                     # Call API instead of file read
└── ao-new                             # Load agent config from API

agent-orchestrator-frontend/src/
├── types/agent.ts                     # Update mcp_servers to full config, add skills
├── services/agentService.ts           # Replace mock with real API calls
├── components/features/agents/
│   └── AgentEditor.tsx                # Replace MCP checkboxes with JSON editor
├── .env.example                       # Add VITE_AGENT_MANAGER_URL
└── README.md                          # Document new service
```

### No Changes (Backwards Compatible)
```
.agent-orchestrator/agents/    # File structure unchanged
plugins/.../lib/agent.py       # Keep for potential fallback
plugins/.../lib/config.py      # Reuse configuration
```

---

## Implementation Order

**Priority 1 (Core API):**
1. Create `agent-orchestrator-backend/` service structure
2. Implement `agent_storage.py` with file operations
3. Implement `models.py` and `validation.py`
4. Implement `main.py` with all endpoints
5. Test API manually with curl/Postman

**Priority 2 (CLI Integration):**
6. Create `lib/agent_api.py` HTTP client
7. Update `ao-list-agents` to use API
8. Update `ao-new` to load agent configs from API
9. Test CLI commands

**Priority 3 (Frontend Integration):**
10. Update `src/types/agent.ts` with full MCP config types
11. Replace mock service with real API calls in `agentService.ts`
12. Install `@monaco-editor/react` for JSON editor
13. Create `MCPEditor.tsx` component
14. Create `mcpTemplates.ts` with common MCP servers
15. Update `AgentEditor.tsx` - replace MCP checkboxes with JSON editor
16. Test end-to-end workflow

---

## Dependencies

**New Python Dependencies:**
```txt
# agent-orchestrator-backend/requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
```

**Existing Dependencies (Reuse):**
- `typer` - Already used in CLI
- `requests` - For `agent_api.py` HTTP client (or use `urllib`)

**New Frontend Dependencies:**
```bash
npm install @monaco-editor/react
```

---

## Deployment Notes

**Development:**
```bash
# Terminal 1: Start Agent Manager Service
cd agent-orchestrator-backend
uvicorn main:app --port 8767 --reload

# Terminal 2: Start Observability Backend (if needed)
cd agent-orchestrator-observability/backend
uvicorn main:app --port 8765 --reload

# Terminal 3: Start Document Server (if needed)
cd plugins/document-sync/document-server
uvicorn src.main:app --port 8766 --reload

# Terminal 4: Start Frontend
cd agent-orchestrator-frontend
npm run dev
```

**Environment Variables:**
```bash
export AGENT_ORCHESTRATOR_PROJECT_DIR=/path/to/project
export AGENT_MANAGER_PORT=8767
export VITE_AGENT_MANAGER_URL=http://localhost:8767
```

**Why:** Clear startup instructions, multi-service coordination

---

## Success Criteria

✅ Agent Manager Service running on port 8767
✅ All CRUD endpoints functional
✅ Python CLI commands use API for listing/loading agents (read-only)
✅ Frontend can create, edit, delete, and toggle agent status
✅ Frontend displays real agents (not mock data)
✅ MCP JSON editor works with syntax validation
✅ Status toggle creates/removes `.disabled` file
✅ 100% backwards compatible with existing file structure
✅ No breaking changes to existing workflows
✅ Agent management done via UI only (not CLI commands)

---

## Out of Scope (YAGNI)

❌ Authentication/authorization
❌ Database migration
❌ Agent versioning
❌ Bulk operations
❌ Agent import/export
❌ Audit logging
❌ Rate limiting
❌ Caching layer
❌ GraphQL API
❌ MCP server validation against actual packages (just validate JSON schema)
❌ MCP server testing/health checks
❌ Complex skills configuration (skills are simple string arrays for now)

**Why:** Focus on core functionality, add later if needed

---

## Next Steps

1. Review and approve this plan
2. Begin Phase 1: Agent Manager Service implementation
3. Test each phase before proceeding to next
4. Update documentation as implementation progresses
