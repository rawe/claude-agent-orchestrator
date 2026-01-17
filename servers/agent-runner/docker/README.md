# Agent Runner Docker Images

Containerized Agent Runner with layered image architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 agent-runner-base                            │
│  - Python 3.12 + uv                                         │
│  - Agent runner source code                                 │
│  - Core dependencies                                        │
└─────────────────────────────────────────────────────────────┘
              │                              │
              ▼                              ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│ agent-runner-claude-code│    │ agent-runner-procedural │
│ - Node.js + Claude Code │    │ - Procedural executor   │
│ - OAuth token auth      │    │ - CLI command execution │
└─────────────────────────┘    └─────────────────────────┘
              │
              ▼
┌─────────────────────────┐
│ Custom executor images  │
│ (user-defined)          │
└─────────────────────────┘
```

## Quick Start

```bash
cd servers/agent-runner/docker

# 1. Generate OAuth token (on host with logged-in Claude Code)
claude setup-token
# Copy the token (sk-ant-...)

# 2. Setup environment
cp .env.template .env
# Edit .env: paste CLAUDE_CODE_OAUTH_TOKEN

# 3. Start Agent Coordinator (if not running)
cd ../../agent-coordinator
AUTH_ENABLED=false DOCS_ENABLED=true uv run python -m main &
cd ../agent-runner/docker

# 4. Build and run
docker compose up -d --build

# 5. View logs
docker compose logs -f
```

## Building Images

### Option A: Multi-stage Dockerfile (recommended)

Single Dockerfile with all stages - no manual base image build needed:

```bash
# From project root

# Claude Code executor
docker build --target claude-code -t agent-runner-claude-code:latest \
  -f servers/agent-runner/docker/Dockerfile .

# Procedural executor
docker build --target procedural -t agent-runner-procedural:latest \
  -f servers/agent-runner/docker/Dockerfile .

# Base image only (if needed)
docker build --target base -t agent-runner-base:latest \
  -f servers/agent-runner/docker/Dockerfile .
```

### Option B: Separate Dockerfiles (for extensibility)

Use separate Dockerfiles when building custom executors that extend the base:

```bash
# From project root

# 1. Build base image first
docker build -t agent-runner-base:latest \
  -f servers/agent-runner/docker/base/Dockerfile .

# 2. Build executor images
docker build -t agent-runner-claude-code:latest \
  --build-arg BASE_IMAGE=agent-runner-base:latest \
  -f servers/agent-runner/docker/claude-code/Dockerfile .

docker build -t agent-runner-procedural:latest \
  --build-arg BASE_IMAGE=agent-runner-base:latest \
  -f servers/agent-runner/docker/procedural/Dockerfile .
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | `http://host.docker.internal:8765` | Agent Coordinator URL |
| `PROFILE` | `best` | Executor profile name |
| `PROJECT_DIR` | `/workspace` | Working directory in container |
| `RUNNER_TAGS` | (empty) | Comma-separated capability tags |
| `REQUIRE_MATCHING_TAGS` | `false` | Only accept runs with matching tags |
| `VERBOSE` | `false` | Enable verbose logging |
| `MCP_PORT` | (random) | Fixed MCP server port |
| `EXTERNAL_MCP_URL` | (empty) | External MCP server URL |

### Claude Code Authentication (claude-code image only)

| Variable | Description |
|----------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth token from `claude setup-token` (required) |

**Note:** Do NOT set `ANTHROPIC_API_KEY` when using OAuth token - they conflict.

### Auth0 (Optional)

For authenticated coordinators:

| Variable | Description |
|----------|-------------|
| `AUTH0_DOMAIN` | Auth0 tenant domain |
| `AUTH0_RUNNER_CLIENT_ID` | M2M client ID |
| `AUTH0_RUNNER_CLIENT_SECRET` | M2M client secret |
| `AUTH0_AUDIENCE` | API audience |

### Volumes

| Container Path | Purpose |
|----------------|---------|
| `/workspace` | Project files for agent work |

## Available Profiles

Each executor image includes only compatible profiles:

**agent-runner-claude-code:**

| Profile | Description |
|---------|-------------|
| `best` | Full access, best practices, opus model |
| `quick` | Full access, best practices, sonnet model |

**agent-runner-procedural:**

| Profile | Description |
|---------|-------------|
| `echo` | Example CLI command executor |
| `test-procedural` | Test profile for procedural executor |

### Why profiles are per-image

Profiles reference a specific executor via `command` path (e.g., `executors/claude-code/ao-claude-code-exec`). The path is relative to the agent-runner's working directory (`/app/servers/agent-runner/`). Each Docker image only contains its executor, so it can only run profiles that reference that executor. Copying incompatible profiles would cause "executor not found" errors.

## Creating Custom Executor Images

Extend the base image with your own executor:

```dockerfile
# my-executor/Dockerfile
FROM agent-runner-base:latest

# Add custom dependencies
RUN apt-get update && apt-get install -y my-tool

# Copy your executor
COPY my-executor/ /app/servers/agent-runner/executors/my-executor/

# Add your profile
COPY my-profile.json /app/servers/agent-runner/profiles/

# Set default profile
ENV PROFILE=my-profile
```

Build and run:

```bash
docker build -t agent-runner-my-executor:latest \
  --build-arg BASE_IMAGE=agent-runner-base:latest \
  -f my-executor/Dockerfile .

docker run -d \
  -e AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765 \
  -v ./workspace:/workspace \
  agent-runner-my-executor:latest
```

## Operations

### View Logs

```bash
docker compose logs -f
```

### Stop Container

```bash
docker compose down
```

### Rebuild After Changes

```bash
docker compose up -d --build
```

### Shell Access

```bash
docker compose exec agent-runner bash
```

### List Available Profiles

```bash
docker compose exec agent-runner uv run --script agent-runner --profile-list
```

## Troubleshooting

### "Cannot connect to Agent Coordinator"

- Verify coordinator is running: `curl http://localhost:8765/health`
- Ensure `AGENT_ORCHESTRATOR_API_URL` uses `host.docker.internal` (not `localhost`)

### "Profile not found"

- Check profile exists: `docker compose exec agent-runner ls /app/servers/agent-runner/profiles/`
- Ensure executor image includes the required executor for that profile

### "Permission denied on workspace"

```bash
mkdir -p workspace
chmod 777 workspace  # Or appropriate permissions
```

## Directory Structure

```
docker/
├── Dockerfile            # Multi-stage (base + all executors)
├── base/
│   ├── Dockerfile        # Base image (for extensibility)
│   └── entrypoint.sh     # Container startup script
├── claude-code/
│   ├── Dockerfile        # Claude Code executor (for extensibility)
│   ├── claude-config/    # Claude Code config (.claude.json)
│   └── profiles/         # claude-code compatible profiles
├── procedural/
│   ├── Dockerfile        # Procedural executor (for extensibility)
│   └── profiles/         # procedural compatible profiles
├── docker-compose.yml    # Default orchestration
├── .env.template         # Environment template
├── .gitignore
├── .dockerignore
├── workspace/            # Default workspace mount
└── README.md             # This file
```
