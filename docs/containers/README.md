# AOF Container Images

The Agent Orchestration Framework (AOF) provides three container images for deployment:

| Image | Description |
|-------|-------------|
| `ghcr.io/rawe/aof-coordinator` | Session management, observability, and agent blueprint registry |
| `ghcr.io/rawe/aof-runner-claude-code` | Agent execution engine with Claude Code executor |
| `ghcr.io/rawe/aof-dashboard` | Web UI for agent management and monitoring |

## Quick Start

```bash
# Pull all images (replace <version> with actual version, e.g., 0.2.0)
docker pull ghcr.io/rawe/aof-coordinator:<version>
docker pull ghcr.io/rawe/aof-runner-claude-code:<version>
docker pull ghcr.io/rawe/aof-dashboard:<version>
```

## Versioning

All three images share the same release version. When you use the same version tag, all components are guaranteed to work together.

```bash
# Use a specific version
docker pull ghcr.io/rawe/aof-coordinator:<version>
docker pull ghcr.io/rawe/aof-runner-claude-code:<version>
docker pull ghcr.io/rawe/aof-dashboard:<version>
```

## Image Details

- [Coordinator](./coordinator.md) - API server for session orchestration
- [Runner (Claude Code)](./runner-claude-code.md) - Agent execution with Claude Code
- [Dashboard](./dashboard.md) - Web-based management UI

## Building Locally

Use the Makefile to build images locally:

```bash
# Build all images with a specific version
make release VERSION=<version>

# Build individual components
make release-coordinator VERSION=<version>
make release-runner VERSION=<version>
make release-dashboard VERSION=<version>

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
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Coordinator                                │
│                 (aof-coordinator:8765)                          │
│     Session Management │ Agent Registry │ Event Streaming        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP (polling)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Runner (Claude Code)                          │
│               (aof-runner-claude-code)                          │
│          Polls for runs │ Executes agents │ Reports status       │
└─────────────────────────────────────────────────────────────────┘
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

  dashboard:
    image: ghcr.io/rawe/aof-dashboard:<version>
    ports:
      - "3000:80"
    depends_on:
      - coordinator

  runner:
    image: ghcr.io/rawe/aof-runner-claude-code:<version>
    environment:
      - AGENT_ORCHESTRATOR_API_URL=http://coordinator:8765
      - CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN}
    volumes:
      - ./workspace:/workspace
    depends_on:
      - coordinator

volumes:
  coordinator-data:
```
