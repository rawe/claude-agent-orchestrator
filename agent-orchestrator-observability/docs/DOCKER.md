# Docker Setup Guide

Quick reference for running the observability stack with Docker.

## Quick Start

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Services

### Backend
- **Port:** 8765
- **Container:** agent-orchestrator-observability-backend
- **Image:** Built from `docker/backend.Dockerfile`
- **Database:** Stored in `observability-data` volume

### Frontend
- **Port:** 5173
- **Container:** agent-orchestrator-observability-frontend
- **Image:** Built from `docker/frontend.Dockerfile`
- **Hot Reload:** Source files mounted for development

## Common Commands

### Start Services
```bash
docker-compose up -d
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart backend
```

### Rebuild After Code Changes
```bash
docker-compose up -d --build
```

### Stop Services
```bash
# Stop but keep volumes
docker-compose down

# Stop and remove volumes (clears database)
docker-compose down -v
```

### Check Status
```bash
docker-compose ps
```

## Development Workflow

### Making Backend Changes
1. Edit files in `backend/`
2. Backend will auto-reload (uvicorn reload mode)
3. If dependencies changed: `docker-compose up -d --build backend`

### Making Frontend Changes
1. Edit files in `frontend/src/`
2. Frontend will hot-reload automatically
3. If dependencies changed: `docker-compose up -d --build frontend`

## Volumes

### observability-data
Persistent volume for SQLite database.

**View data:**
```bash
# Access backend container
docker exec -it agent-orchestrator-observability-backend sh

# Query database
sqlite3 .agent-orchestrator/observability.db "SELECT * FROM sessions;"
```

**Backup database:**
```bash
docker cp agent-orchestrator-observability-backend:/app/.agent-orchestrator/observability.db ./backup.db
```

**Restore database:**
```bash
docker cp ./backup.db agent-orchestrator-observability-backend:/app/.agent-orchestrator/observability.db
```

## Networking

Services communicate via `observability-network`:
- Backend accessible at `http://backend:8765` from frontend container
- Both services exposed to host on their respective ports

## Environment Variables

### Backend
- `PYTHONUNBUFFERED=1` - Immediate log output

### Frontend
- `VITE_BACKEND_URL=http://localhost:8765` - Backend API URL

## Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
lsof -i :8765
lsof -i :5173

# Kill the process or change ports in docker-compose.yml
```

### Container Won't Start
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild from scratch
docker-compose down -v
docker-compose up -d --build
```

### Database Issues
```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

### Changes Not Reflecting
```bash
# For code changes
docker-compose restart

# For dependency changes
docker-compose up -d --build

# Nuclear option - full rebuild
docker-compose down
docker system prune -a
docker-compose up -d --build
```

## Production Deployment

For production, modify `docker-compose.yml`:

1. Build frontend for production:
   ```dockerfile
   # In frontend.Dockerfile, change CMD to:
   RUN npm run build
   CMD ["npx", "serve", "-s", "dist", "-l", "5173"]
   ```

2. Remove volume mounts (use image files)
3. Add proper secrets management
4. Configure reverse proxy (nginx/traefik)
5. Use production backend server (gunicorn)

## Resource Limits

Add to docker-compose.yml services:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```
