# Agent Coordinator

FastAPI service providing session management, real-time observability, and agent blueprint registry.

## Why?

The Agent Coordinator is the unified backend service for the Agent Orchestrator Framework. It handles:
- **Session Management**: Track agent session lifecycle, events, and results
- **Real-time Updates**: WebSocket broadcasting for dashboard live monitoring
- **Agent Registry**: CRUD API for agent blueprints (system prompts, MCP servers, skills)

## Quick Start

```bash
# Run locally
uv run python -m main

# With custom agents directory
AGENT_ORCHESTRATOR_AGENTS_DIR=/path/to/agents uv run python -m main

# With debug logging
DEBUG_LOGGING=true uv run python -m main
```

## API Endpoints

### Session Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions` | List all sessions |
| POST | `/sessions` | Create new session |
| GET | `/sessions/{id}` | Get session details |
| GET | `/sessions/{id}/status` | Get session status |
| GET | `/sessions/{id}/result` | Get session result |
| GET | `/sessions/{id}/events` | Get session events |
| POST | `/sessions/{id}/events` | Add event to session |
| PATCH | `/sessions/{id}/metadata` | Update session metadata |
| DELETE | `/sessions/{id}` | Delete session |

### Events (Legacy)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/events` | Send event (creates session if needed) |
| GET | `/events/{session_id}` | Get session events |

### Agent Registry

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/agents` | List all agents |
| GET | `/agents/{name}` | Get agent by name |
| POST | `/agents` | Create agent |
| PATCH | `/agents/{name}` | Update agent |
| DELETE | `/agents/{name}` | Delete agent |
| PATCH | `/agents/{name}/status` | Toggle active/inactive |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws` | Real-time session and event updates |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG_LOGGING` | `false` | Enable verbose debug logging |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | `{cwd}/.agent-orchestrator/agents` | Agents storage directory |
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | `{cwd}` | Project directory (fallback for agents dir) |

## Agent File Structure

Agents are stored as directories:

```
.agent-orchestrator/agents/{name}/
├── agent.json              # Required: name, description, skills
├── agent.system-prompt.md  # Optional: system prompt
├── agent.mcp.json          # Optional: MCP server config
└── .disabled               # Optional: presence = inactive
```

## Database

Session and event data is stored in SQLite:
- Location: `.agent-orchestrator/observability.db`
- Tables: `sessions`, `events`

## Docker

```bash
# Via docker-compose (from project root)
make start-bg

# Check logs
make logs-coordinator

# Health check
curl http://localhost:8765/health
```
