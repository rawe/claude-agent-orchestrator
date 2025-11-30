# Agent Registry

FastAPI service providing HTTP endpoints for agent CRUD operations.

## Why?

Agent definitions (system prompts, MCP servers, skills) are stored as files. This service provides a unified API that both the **CLI commands** (`ao-list-agents`, `ao-new --agent`) and the **dashboard** use to manage agents. Single source of truth, no direct file manipulation needed.

## Quick Start

```bash
# Run locally
uv run python -m main

# With custom agents directory
AGENT_ORCHESTRATOR_AGENTS_DIR=/path/to/agents uv run python -m main
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/agents` | List all agents |
| GET | `/agents/{name}` | Get agent by name |
| POST | `/agents` | Create agent |
| PATCH | `/agents/{name}` | Update agent |
| DELETE | `/agents/{name}` | Delete agent |
| PATCH | `/agents/{name}/status` | Toggle active/inactive |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_REGISTRY_HOST` | `0.0.0.0` | Server bind address |
| `AGENT_REGISTRY_PORT` | `8767` | Server port |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | `{cwd}/.agent-orchestrator/agents` | Agents storage directory |

## File Structure

Agents are stored as directories:

```
.agent-orchestrator/agents/{name}/
├── agent.json              # Required: name, description, skills
├── agent.system-prompt.md  # Optional: system prompt
├── agent.mcp.json          # Optional: MCP server config
└── .disabled               # Optional: presence = inactive
```

## Docker

```bash
# Via docker-compose (from project root)
make start-bg

# Check logs
make logs-agent
```
