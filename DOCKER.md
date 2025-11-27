# Docker Setup Guide

This guide explains how to use the centralized Docker setup for the Agent Orchestrator Framework.

## Overview

The Agent Orchestrator Framework consists of four main Docker services:

1. **Unified Frontend** (Port 3000) - React-based UI for agent management, session monitoring, and document management
2. **Agent Manager** (Port 8767) - FastAPI service for agent CRUD operations
3. **Observability Backend** (Port 8765) - Python-based WebSocket server for agent session monitoring
4. **Document Sync Server** (Port 8766) - Python-based document storage and retrieval service

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Docker Network                                    │
│                   (agent-orchestrator-network)                            │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      Unified Frontend (Port 3000)                   │  │
│  │        Agent Management | Sessions | Documents                      │  │
│  └───────────────┬─────────────────┬─────────────────┬────────────────┘  │
│                  │                 │                 │                    │
│                  ▼                 ▼                 ▼                    │
│  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐       │
│  │   Agent Manager   │ │   Observability   │ │  Document Server  │       │
│  │    (Port 8767)    │ │     Backend       │ │    (Port 8766)    │       │
│  │                   │ │   (Port 8765)     │ │                   │       │
│  └─────────┬─────────┘ └───────────────────┘ └─────────┬─────────┘       │
│            │                                           │                  │
│            ▼                                           ▼                  │
│  ┌───────────────────┐                      ┌───────────────────┐        │
│  │   Volume Mount    │                      │   Named Volume    │        │
│  │   (agents dir)    │                      │   (persistent)    │        │
│  └───────────────────┘                      └───────────────────┘        │
└──────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker Desktop or Docker Engine
- Docker Compose V2

### Start All Services

The simplest way to start all services:

```bash
make start-bg
```

This will:
1. Build all Docker images (if needed)
2. Start all services in the background
3. Show you the URLs to access each service

### Alternative: Manual Docker Compose

If you prefer using Docker Compose directly:

```bash
# Build and start in background
docker-compose up --build -d

# View logs
docker-compose logs -f
```

## Custom Agent Directory Configuration

By default, the Agent Manager service looks for agent definitions in `./.agent-orchestrator/agents`. You can customize this to point to a different directory on your machine.

### Option 1: Using a `.env` file (Simplest)

Create a `.env` file in the project root:

```bash
# Set your custom agents directory path
echo "AGENT_DIR=/path/to/your/agents" > .env

# Then start services as usual
make start-bg
```

### Option 2: Using `docker-compose.override.yml` (Most Flexible)

For more complex overrides (multiple settings, port changes, etc.):

```bash
# Copy the template
cp docker-compose.override.yml.template docker-compose.override.yml

# Edit the file with your settings
# The override file is automatically loaded by Docker Compose
```

Edit `docker-compose.override.yml`:

```yaml
services:
  agent-manager:
    volumes:
      - /path/to/your/agents:/data/agents
```

### Option 3: Inline Environment Variable (One-off)

For quick testing without modifying any files:

```bash
AGENT_DIR=/path/to/your/agents make start-bg
```

Or with docker-compose directly:

```bash
AGENT_DIR=/path/to/your/agents docker-compose up --build -d
```

## Available Commands

Run `make help` to see all available commands:

### Basic Operations

| Command | Description |
|---------|-------------|
| `make build` | Build all Docker images |
| `make start` | Start all services (foreground, with logs) |
| `make start-bg` | Start all services in background |
| `make stop` | Stop all services |
| `make restart` | Restart all services |
| `make status` | Show status of all services |
| `make health` | Check health of all services |

### Logs

| Command | Description |
|---------|-------------|
| `make logs` | View logs from all services |
| `make logs-f` | Follow logs from all services |
| `make logs-obs` | View observability logs only |
| `make logs-doc` | View document server logs only |

### Cleanup

| Command | Description |
|---------|-------------|
| `make clean` | Stop and remove containers (keeps data) |
| `make clean-all` | Remove everything including data (sessions, documents) |
| `make clean-docs` | Remove only document storage volume |
| `make clean-sessions` | Remove only session storage volume |

### Individual Services

| Command | Description |
|---------|-------------|
| `make restart-obs` | Restart observability services |
| `make restart-doc` | Restart document server |

## Service Details

### Unified Frontend

- **Port:** 3000
- **Technology:** Node.js 18 + Vite + React + Tailwind CSS
- **Purpose:** Unified UI for agent management, session monitoring, and document management
- **URL:** http://localhost:3000
- **Code Location:** `./agent-orchestrator-frontend`

**Features:**
- Agent Sessions (real-time monitoring via WebSocket)
- Document Management (upload, tag, preview)
- Agent Manager (create/edit agent definitions)

### Agent Manager

- **Port:** 8767
- **Technology:** Python 3.12 + FastAPI
- **Purpose:** CRUD API for agent definitions
- **Health Check:** http://localhost:8767/health
- **Code Location:** `./agent-orchestrator-backend`

**Environment Variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MANAGER_HOST` | `0.0.0.0` | Server bind address |
| `AGENT_MANAGER_PORT` | `8767` | Server port |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | `/data/agents` | Agents storage directory (in container) |

### Observability Backend

- **Port:** 8765
- **Technology:** Python 3.12 + WebSockets
- **Purpose:** Receives and stores agent session events
- **Health Check:** http://localhost:8765/sessions
- **Code Location:** `./agent-orchestrator-observability/backend`

**Development Mode:**
- Source code is mounted as a volume
- Changes to Python files are reflected in real-time

### Document Sync Server

- **Port:** 8766
- **Technology:** Python 3.11 + FastAPI
- **Purpose:** Document storage and retrieval for Claude Code plugins
- **Health Check:** http://localhost:8766/health
- **Code Location:** `./document-sync-plugin/document-server`

**Data Persistence:**
- Uses a named volume (`agent-orchestrator-document-data`)
- Data survives container restarts
- Database and files stored in `/app/data`

## How It Works: Minimizing Redundancy

### Design Decisions

The centralized `docker-compose.yml` was designed to minimize redundancy while keeping the setup simple:

#### 1. **Reusing Existing Dockerfiles**

Instead of duplicating Dockerfile content, the centralized compose file references the existing Dockerfiles in subdirectories:

```yaml
observability-backend:
  build:
    context: ./agent-orchestrator-observability
    dockerfile: docker/backend.Dockerfile
```

**Benefits:**
- No duplication of Dockerfile content
- Subdirectories remain self-contained
- Individual docker-compose files still work standalone

#### 2. **Relative Paths**

All paths are relative to the project root:

```yaml
volumes:
  - ./agent-orchestrator-observability/backend:/app/backend
```

**Benefits:**
- Clear and explicit
- No symlinks needed
- Easy to understand and maintain

#### 3. **Unified Network**

All services use a single Docker network:

```yaml
networks:
  agent-orchestrator-network:
    driver: bridge
```

**Benefits:**
- Services can communicate by container name
- Simpler network topology
- Better for future service additions

#### 4. **Standalone Compatibility**

The individual docker-compose files in subdirectories remain functional:

```bash
# Still works!
cd agent-orchestrator-observability
docker-compose up
```

**Benefits:**
- Developers can work on individual services
- No breaking changes to existing workflows
- Gradual migration path

## Building Services

### Automatic Building

When you run `make start` or `make start-bg`, Docker Compose will:
1. Check if images exist
2. Build them if they don't exist
3. Rebuild them if Dockerfiles or dependencies changed

### Force Rebuild

To force a complete rebuild of all images:

```bash
# Using make
make build

# Using docker-compose directly
docker-compose build --no-cache
```

### Build Individual Services

```bash
# Build only frontend
docker-compose build frontend

# Build only agent manager
docker-compose build agent-manager

# Build only observability backend
docker-compose build observability-backend

# Build only document server
docker-compose build document-server
```

### Build Process

The build process for each service:

**Unified Frontend:**
1. Uses `node:18-alpine` base image
2. Copies `package*.json` and installs dependencies
3. Builds production bundle with Vite
4. Serves via nginx on port 80

**Agent Manager:**
1. Uses `python:3.12-slim` base image
2. Installs `uv` package manager
3. Copies `pyproject.toml` and installs dependencies
4. Runs FastAPI server

**Observability Backend:**
1. Uses `python:3.12-slim` base image
2. Installs `uv` package manager
3. Copies `pyproject.toml` and installs dependencies
4. Code is mounted at runtime (development mode)

**Document Server:**
1. Uses `python:3.11-slim` base image
2. Installs dependencies from `requirements.txt`
3. Copies application code into image
4. Runs FastAPI server

## Troubleshooting

### Services Won't Start

Check if ports are already in use:

```bash
# Check if ports are occupied
lsof -i :3000  # Unified Frontend
lsof -i :8767  # Agent Manager
lsof -i :8765  # Observability backend
lsof -i :8766  # Document server
```

### Health Checks Failing

Check service health:

```bash
make health
```

Or manually:

```bash
curl http://localhost:3000       # Frontend
curl http://localhost:8767/health  # Agent Manager
curl http://localhost:8765/sessions  # Observability
curl http://localhost:8766/health  # Document Server
```

### View Service Logs

```bash
# All services
make logs-f

# Individual service
docker-compose logs -f observability-backend
docker-compose logs -f document-server
```

### Reset Everything

If things get into a bad state:

```bash
# Stop everything
make clean

# Remove all images and rebuild
docker-compose down --rmi all
make build
make start-bg
```

### Permission Issues

If you encounter permission issues with volumes:

```bash
# Fix ownership (Linux/macOS)
sudo chown -R $USER:$USER ./agent-orchestrator-observability
sudo chown -R $USER:$USER ./document-sync-plugin
```

## Data Persistence

Both the document server and session data use named Docker volumes for persistence. Data survives container restarts and rebuilds.

### Document Server Data

- **Volume Name:** `agent-orchestrator-document-data`
- **Location in Container:** `/app/data`
- **Contains:** SQLite database + uploaded files

### Session Data (Observability)

- **Volume Name:** `agent-orchestrator-observability-data`
- **Location in Container:** `/app/.agent-orchestrator`
- **Contains:** SQLite database with session history and events

### Backing Up Data

```bash
# Backup documents
docker run --rm -v agent-orchestrator-document-data:/data -v $(pwd):/backup alpine tar czf /backup/document-data-backup.tar.gz /data

# Backup sessions
docker run --rm -v agent-orchestrator-observability-data:/data -v $(pwd):/backup alpine tar czf /backup/session-data-backup.tar.gz /data
```

### Clearing Data

```bash
make clean-docs      # Clear only documents
make clean-sessions  # Clear only sessions
make clean-all       # Clear everything (containers + all data)
```

## Integration with Claude Code Plugins

### Document Sync Plugin

The document sync plugin requires the document server to be running:

```bash
# Start the document server
make start-bg

# Verify it's running
curl http://localhost:8766/health
```

In Claude Code, the plugin will automatically connect to `http://localhost:8766`.

### Unified Frontend

The unified frontend provides a single interface for all agent orchestration tasks:

1. Start all services:
   ```bash
   make start-bg
   ```

2. Open the UI:
   ```
   http://localhost:3000
   ```

3. Features available:
   - **Sessions**: Monitor agent sessions in real-time
   - **Documents**: Upload and manage context documents
   - **Agents**: Create and configure agent definitions

## Advanced Usage

### Custom Environment Variables

Create a `.env` file in the project root:

```env
# Agent Manager
AGENT_DIR=/path/to/your/agents

# Observability
DEBUG_LOGGING=true
```

Docker Compose will automatically load these variables.

### Development Mode

The current setup is optimized for development with volume mounts. For production:

1. Remove volume mounts for code
2. Copy code into images during build
3. Use production-grade web servers (gunicorn, nginx)
4. Add proper logging and monitoring
5. Use environment-specific configurations

### Running Individual Services

You can start specific services:

```bash
# Only document server
docker-compose up document-server

# Only agent manager
docker-compose up agent-manager

# Frontend with all backends
docker-compose up frontend agent-manager observability-backend document-server
```

## Migration from Subdirectory Compose Files

The centralized setup is **fully compatible** with existing subdirectory compose files:

- Old way still works: `cd agent-orchestrator-observability && docker-compose up`
- New way is easier: `make start-bg` from project root
- Both approaches use the same Dockerfiles
- No code changes needed

**Recommendation:** Use the centralized setup for running multiple services, and subdirectory compose files for focused development on a single service.

## Next Steps

1. Start services: `make start-bg`
2. Open the frontend: http://localhost:3000
3. Check status: `make status`
4. Check health: `make health`
5. View logs: `make logs-f`

For issues or questions, check the logs first:
```bash
make logs-f
```

## Summary

The centralized Docker setup provides:

- **Simple:** Single command to start everything
- **Minimal Redundancy:** Reuses existing Dockerfiles
- **Flexible:** Custom agent directory via `.env` or `docker-compose.override.yml`
- **Development-Friendly:** Hot reloading for code changes
- **Production-Ready:** Health checks and proper networking
- **Well-Documented:** Clear commands and troubleshooting steps
