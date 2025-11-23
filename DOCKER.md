# Docker Setup Guide

This guide explains how to use the centralized Docker setup for the Agent Orchestrator Framework.

## Overview

The Agent Orchestrator Framework consists of three main Docker services:

1. **Observability Backend** (Port 8765) - Python-based WebSocket server for agent monitoring
2. **Observability Frontend** (Port 5173) - React-based UI for visualizing agent tasks
3. **Document Sync Server** (Port 8766) - Python-based document storage and retrieval service

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                            │
│              (agent-orchestrator-network)                    │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │  Observability   │  │  Observability   │  │ Document  │ │
│  │     Backend      │◄─┤     Frontend     │  │  Server   │ │
│  │   (Port 8765)    │  │   (Port 5173)    │  │ (8766)    │ │
│  └──────────────────┘  └──────────────────┘  └───────────┘ │
│          │                                          │        │
│          │                                          │        │
│  ┌───────▼────────┐                        ┌────────▼─────┐ │
│  │  Volume Mount  │                        │ Named Volume │ │
│  │  (dev code)    │                        │ (persistent) │ │
│  └────────────────┘                        └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
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
| `make clean-all` | Remove everything including volumes |

### Individual Services

| Command | Description |
|---------|-------------|
| `make restart-obs` | Restart observability services |
| `make restart-doc` | Restart document server |

## Service Details

### Observability Backend

- **Port:** 8765
- **Technology:** Python 3.12 + WebSockets
- **Purpose:** Receives and stores agent task events
- **Health Check:** http://localhost:8765/health
- **Code Location:** `./agent-orchestrator-observability/backend`

**Development Mode:**
- Source code is mounted as a volume
- Changes to Python files are reflected in real-time

### Observability Frontend

- **Port:** 5173
- **Technology:** Node.js 18 + Vite + React
- **Purpose:** Visual interface for monitoring agent tasks
- **URL:** http://localhost:5173
- **Code Location:** `./agent-orchestrator-observability/frontend`

**Development Mode:**
- Source code is mounted as a volume
- Hot module reloading (HMR) is enabled
- Changes to React components are reflected immediately

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
# Build only observability backend
docker-compose build observability-backend

# Build only document server
docker-compose build document-server
```

### Build Process

The build process for each service:

**Observability Backend:**
1. Uses `python:3.12-slim` base image
2. Installs `uv` package manager
3. Copies `pyproject.toml` and installs dependencies
4. Code is mounted at runtime (development mode)

**Observability Frontend:**
1. Uses `node:18-alpine` base image
2. Copies `package*.json` and installs dependencies
3. Code is mounted at runtime (development mode)
4. Runs Vite dev server with HMR

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
lsof -i :8765  # Observability backend
lsof -i :5173  # Observability frontend
lsof -i :8766  # Document server
```

### Health Checks Failing

Check service health:

```bash
make health
```

Or manually:

```bash
curl http://localhost:8765/health
curl http://localhost:8766/health
curl http://localhost:5173
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

### Document Server Data

The document server uses a named volume for persistent storage:

- **Volume Name:** `agent-orchestrator-document-data`
- **Location in Container:** `/app/data`
- **Contains:** SQLite database + uploaded files

**Backing up data:**

```bash
# Create backup
docker run --rm -v agent-orchestrator-document-data:/data -v $(pwd):/backup alpine tar czf /backup/document-data-backup.tar.gz /data

# Restore backup
docker run --rm -v agent-orchestrator-document-data:/data -v $(pwd):/backup alpine sh -c "cd / && tar xzf /backup/document-data-backup.tar.gz"
```

### Observability Data

Currently, the observability backend starts with a fresh database on each run. To enable persistence, uncomment the volume in `docker-compose.yml`:

```yaml
observability-backend:
  volumes:
    - ./agent-orchestrator-observability/backend:/app/backend
    - observability-data:/app/data  # Uncomment this line
```

Then add the volume definition:

```yaml
volumes:
  document-data:
    name: agent-orchestrator-document-data
  observability-data:  # Add this
    name: agent-orchestrator-observability-data
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

### Observability Plugin

The observability plugin is optional but provides valuable insights:

1. Start the observability services:
   ```bash
   make start-bg
   ```

2. Open the UI:
   ```
   http://localhost:5173
   ```

3. Watch agent tasks in real-time as they execute

## Advanced Usage

### Custom Environment Variables

Create a `.env` file in the project root:

```env
# Observability
DEBUG_LOGGING=true
VITE_BACKEND_URL=http://localhost:8765

# Document Server
LOG_LEVEL=DEBUG
DOCUMENT_SERVER_PORT=8766
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

# Only observability stack
docker-compose up observability-backend observability-frontend
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
2. Check status: `make status`
3. Check health: `make health`
4. View logs: `make logs-f`
5. Start using your Claude Code plugins!

For issues or questions, check the logs first:
```bash
make logs-f
```

## Summary

The centralized Docker setup provides:

✅ **Simple:** Single command to start everything
✅ **Minimal Redundancy:** Reuses existing Dockerfiles
✅ **Flexible:** Can still use subdirectory compose files
✅ **Development-Friendly:** Hot reloading for code changes
✅ **Production-Ready:** Health checks and proper networking
✅ **Well-Documented:** Clear commands and troubleshooting steps

Enjoy your simplified Docker workflow! 🚀
