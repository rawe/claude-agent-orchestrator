# AOF Container Images

The Agent Orchestration Framework (AOF) provides four container images for deployment:

| Image | Description |
|-------|-------------|
| `ghcr.io/rawe/aof-coordinator` | Session management, observability, and agent blueprint registry |
| `ghcr.io/rawe/aof-runner-claude-code` | Agent execution engine with Claude Code executor |
| `ghcr.io/rawe/aof-runner-procedural` | Agent execution engine with procedural (CLI) executor |
| `ghcr.io/rawe/aof-dashboard` | Web UI for agent management and monitoring |
| `ghcr.io/rawe/aof-context-store` | Document management and synchronization |

## Quick Start

```bash
# Pull all images (replace <version> with actual version, e.g., 0.2.0)
docker pull ghcr.io/rawe/aof-coordinator:<version>
docker pull ghcr.io/rawe/aof-runner-claude-code:<version>
docker pull ghcr.io/rawe/aof-runner-procedural:<version>
docker pull ghcr.io/rawe/aof-dashboard:<version>
docker pull ghcr.io/rawe/aof-context-store:<version>
```

## Versioning

All four images share the same release version. When you use the same version tag, all components are guaranteed to work together.

```bash
# Use a specific version
docker pull ghcr.io/rawe/aof-coordinator:<version>
docker pull ghcr.io/rawe/aof-runner-claude-code:<version>
docker pull ghcr.io/rawe/aof-runner-procedural:<version>
docker pull ghcr.io/rawe/aof-dashboard:<version>
docker pull ghcr.io/rawe/aof-context-store:<version>
```

## Image Details

- [Coordinator](./coordinator.md) - API server for session orchestration
- [Runner (Claude Code)](./runner-claude-code.md) - Agent execution with Claude Code
- [Runner (Procedural)](./runner-procedural.md) - Agent execution with CLI commands
- [Dashboard](./dashboard.md) - Web-based management UI
- [Context Store](./context-store.md) - Document management and synchronization

## Building Locally

Use the Makefile to build images locally:

```bash
# Build all images with a specific version
make release VERSION=<version>

# Build individual components
make release-coordinator VERSION=<version>
make release-runner VERSION=<version>
make release-runner-procedural VERSION=<version>
make release-dashboard VERSION=<version>
make release-context-store VERSION=<version>

# Build and push to registry
make release VERSION=<version> PUSH=true

# Use a different registry
make release VERSION=<version> REGISTRY=ghcr.io/myorg
```

## Image Labels

All images include OCI-compliant labels:

| Label | Description |
|-------|-------------|
| `org.opencontainers.image.version` | Release version |
| `org.opencontainers.image.revision` | Git commit SHA |
| `org.opencontainers.image.created` | Build timestamp |
| `aof.component` | Component name |
| `aof.component.version` | Component-specific version |

Inspect labels with:

```bash
docker inspect ghcr.io/rawe/aof-coordinator:<version> --format='{{json .Config.Labels}}' | jq
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Dashboard                                │
│                    (aof-dashboard:80)                           │
│                         Web UI                                   │
└───────────────┬─────────────────────────────┬───────────────────┘
                │ HTTP                         │ HTTP
                ▼                              ▼
┌───────────────────────────────┐  ┌──────────────────────────────┐
│          Coordinator          │  │       Context Store          │
│    (aof-coordinator:8765)     │  │  (aof-context-store:8766)    │
│  Sessions │ Registry │ Events │  │  Documents │ Tags │ Search   │
└───────────────┬───────────────┘  └──────────────────────────────┘
                │ HTTP (polling)
                ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│   Runner (Claude Code)       │  │   Runner (Procedural)        │
│ (aof-runner-claude-code)     │  │ (aof-runner-procedural)      │
│ AI-powered agent execution   │  │ CLI command execution        │
└──────────────────────────────┘  └──────────────────────────────┘
                └────────────────┬─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │ Shared Workspace │
                        │   ./workspace    │
                        └─────────────────┘
```

## Docker Compose Example

```yaml
version: '3.8'

services:
  coordinator:
    image: ghcr.io/rawe/aof-coordinator:<version>
    ports:
      - "8765:8765"
    environment:
      - AUTH_ENABLED=false
      - CORS_ORIGINS=*
      - AGENT_ORCHESTRATOR_AGENTS_DIR=/data/config/agents
    volumes:
      - coordinator-data:/app/.agent-orchestrator
      - ./config:/data/config

  context-store:
    image: ghcr.io/rawe/aof-context-store:<version>
    ports:
      - "8766:8766"
    environment:
      - CORS_ORIGINS=*
    volumes:
      - context-store-data:/app/document-data

  dashboard:
    image: ghcr.io/rawe/aof-dashboard:<version>
    ports:
      - "3000:80"
    depends_on:
      - coordinator
      - context-store

  runner:
    image: ghcr.io/rawe/aof-runner-claude-code:<version>
    environment:
      - AGENT_ORCHESTRATOR_API_URL=http://coordinator:8765
      - CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN}
    volumes:
      - ./workspace:/workspace
    depends_on:
      - coordinator

  runner-procedural:
    image: ghcr.io/rawe/aof-runner-procedural:<version>
    environment:
      - AGENT_ORCHESTRATOR_API_URL=http://coordinator:8765
      - PROFILE=echo
    volumes:
      - ./workspace:/workspace
    depends_on:
      - coordinator

volumes:
  coordinator-data:
  context-store-data:
```
