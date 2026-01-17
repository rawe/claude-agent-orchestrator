# AOF Coordinator

The Coordinator is the central API server for the Agent Orchestration Framework. It manages sessions, agent blueprints, runner registration, and provides real-time event streaming.

## Image

```
ghcr.io/rawe/aof-coordinator:<version>
```

## Quick Start

```bash
docker run -d \
  --name aof-coordinator \
  -p 8765:8765 \
  -e AUTH_ENABLED=false \
  -e CORS_ORIGINS=* \
  -e AGENT_ORCHESTRATOR_AGENTS_DIR=/data/config/agents \
  -v $(pwd)/config:/data/config \
  ghcr.io/rawe/aof-coordinator:latest
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_ENABLED` | No | `true` | Enable/disable authentication |
| `AUTH0_DOMAIN` | If auth enabled | - | Auth0 domain for OIDC |
| `AUTH0_AUDIENCE` | If auth enabled | - | Auth0 API audience |
| `CORS_ORIGINS` | No | - | Allowed CORS origins (comma-separated or `*`) |
| `DEBUG_LOGGING` | No | `false` | Enable verbose debug logging |
| `DOCS_ENABLED` | No | `false` | Enable Swagger UI at `/docs` |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | No | `/data/config/agents` | Path to agent blueprint definitions |

## Ports

| Port | Protocol | Description |
|------|----------|-------------|
| 8765 | HTTP | API and SSE endpoints |

## Volumes

| Path | Description |
|------|-------------|
| `/app/.agent-orchestrator` | Session data and internal state |
| `/data/config` | Configuration directory containing `agents/` and `capabilities/` |

### Config Directory Structure

The config directory contains two subfolders:

```
/data/config/
├── agents/           # Agent blueprint definitions (JSON files)
│   ├── my-agent.json
│   └── another-agent.json
└── capabilities/     # Capability definitions
    └── ...
```

The `AGENT_ORCHESTRATOR_AGENTS_DIR` environment variable points to the `agents/` subfolder. The `capabilities/` folder is expected to be a sibling directory.

### Read-Write vs Read-Only Mount

**Read-Write (default):** Allows editing agent blueprints via the API.

```bash
-v $(pwd)/config:/data/config
```

**Read-Only:** Agent blueprints cannot be modified via the API. Use this if you manage blueprints externally (e.g., via Git) and want to prevent runtime modifications.

```bash
-v $(pwd)/config:/data/config:ro
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/sessions` | GET/POST | List/create sessions |
| `/sessions/{id}` | GET/DELETE | Get/delete session |
| `/sessions/{id}/runs` | GET/POST | List/create runs |
| `/events/{session_id}` | GET (SSE) | Real-time event stream |
| `/agents` | GET/POST | List/create agent blueprints |
| `/agents/{name}` | GET/PUT/DELETE | Get/update/delete agent blueprint |
| `/runners` | GET | List registered runners |
| `/docs` | GET | Swagger UI (if DOCS_ENABLED=true) |

## Health Check

The container includes a built-in health check that queries the `/health` endpoint:

```bash
# Check health manually
curl http://localhost:8765/health
```

## Example: Development Setup

```bash
docker run -d \
  --name aof-coordinator \
  -p 8765:8765 \
  -e AUTH_ENABLED=false \
  -e DOCS_ENABLED=true \
  -e CORS_ORIGINS=* \
  -e AGENT_ORCHESTRATOR_AGENTS_DIR=/data/config/agents \
  -v $(pwd)/config:/data/config \
  -v coordinator-data:/app/.agent-orchestrator \
  ghcr.io/rawe/aof-coordinator:latest
```

## Example: Production Setup

```bash
docker run -d \
  --name aof-coordinator \
  -p 8765:8765 \
  -e AUTH_ENABLED=true \
  -e AUTH0_DOMAIN=your-tenant.auth0.com \
  -e AUTH0_AUDIENCE=https://your-api-audience \
  -e CORS_ORIGINS=https://your-dashboard.example.com \
  -e AGENT_ORCHESTRATOR_AGENTS_DIR=/data/config/agents \
  -v /etc/aof/config:/data/config \
  -v /var/lib/aof/coordinator:/app/.agent-orchestrator \
  ghcr.io/rawe/aof-coordinator:1.0.0
```

## Docker Compose

```yaml
services:
  coordinator:
    image: ghcr.io/rawe/aof-coordinator:1.0.0
    ports:
      - "8765:8765"
    environment:
      AUTH_ENABLED: "false"
      CORS_ORIGINS: "*"
      DOCS_ENABLED: "true"
      AGENT_ORCHESTRATOR_AGENTS_DIR: /data/config/agents
    volumes:
      - coordinator-data:/app/.agent-orchestrator
      - ./config:/data/config
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')"]
      interval: 30s
      timeout: 3s
      retries: 3

volumes:
  coordinator-data:
```
