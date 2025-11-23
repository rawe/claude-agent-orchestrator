.PHONY: help build start stop restart logs clean status health clean-docs info urls open

# Default target
help:
	@echo "Agent Orchestrator Framework - Docker Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make build          - Build all Docker images"
	@echo "  make start          - Start all services (builds if needed)"
	@echo "  make start-bg       - Start all services in background"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make logs-f         - Follow logs from all services"
	@echo "  make status         - Show status of all services"
	@echo "  make health         - Check health of all services"
	@echo "  make info           - Show service URLs and descriptions"
	@echo "  make open           - Open Observability Frontend in browser"
	@echo "  make clean          - Stop and remove all containers, networks (keeps volumes)"
	@echo "  make clean-all      - Stop and remove everything including volumes"
	@echo "  make clean-docs     - Remove ONLY the document storage volume (keeps containers)"
	@echo ""
	@echo "Individual service commands:"
	@echo "  make logs-obs       - View observability logs (backend + frontend)"
	@echo "  make logs-doc       - View document server logs"
	@echo "  make restart-obs    - Restart observability services"
	@echo "  make restart-doc    - Restart document server"

# Build all images
build:
	@echo "Building all Docker images..."
	docker-compose build

# Start all services (with build)
start:
	@echo "Starting all services..."
	docker-compose up --build

# Start all services in background
start-bg:
	@echo "Starting all services in background..."
	docker-compose up --build -d
	@echo ""
	@$(MAKE) --no-print-directory info
	@echo ""
	@echo "💡 Quick commands:"
	@echo "   make logs-f    - Follow logs"
	@echo "   make status    - Check status"
	@echo "   make info      - Show this info again"

# Stop all services
stop:
	@echo "Stopping all services..."
	docker-compose stop

# Restart all services
restart:
	@echo "Restarting all services..."
	docker-compose restart

# View logs
logs:
	docker-compose logs

# Follow logs
logs-f:
	docker-compose logs -f

# Show service status
status:
	@echo "Service Status:"
	@docker-compose ps
	@echo ""
	@echo "Running containers:"
	@docker ps --filter "name=agent-orchestrator" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check health of all services
health:
	@echo "Checking service health..."
	@echo ""
	@echo "Observability Backend (port 8765):"
	@curl -s http://localhost:8765/sessions | head -c 100 && echo "  ✅ OK" || echo "  ❌ Not responding"
	@echo ""
	@echo "Document Server (port 8766):"
	@curl -s http://localhost:8766/health || echo "  ❌ Not responding"
	@echo ""
	@echo "Observability Frontend (port 5173):"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:5173 || echo "  ❌ Not responding"

# Show service information
info:
	@echo "╔════════════════════════════════════════════════════════════════════════════╗"
	@echo "║          Agent Orchestrator Framework - Service Information               ║"
	@echo "╚════════════════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🌐 OBSERVABILITY FRONTEND"
	@echo "   URL:         http://localhost:5173"
	@echo "   Purpose:     Visual UI to monitor agent tasks in real-time"
	@echo "   Action:      Open this URL in your browser to see agent activity"
	@echo ""
	@echo "⚙️  OBSERVABILITY BACKEND"
	@echo "   URL:         http://localhost:8765"
	@echo "   Purpose:     WebSocket server receiving agent events"
	@echo "   Endpoints:   /sessions, /events/{id}, /ws"
	@echo "   Note:        Used internally by the frontend and observability hooks"
	@echo ""
	@echo "📄 DOCUMENT SYNC SERVER"
	@echo "   URL:         http://localhost:8766"
	@echo "   Purpose:     Document storage and retrieval for Claude Code plugins"
	@echo "   Endpoints:   /health, /documents, /upload, /download"
	@echo "   Note:        Required for the document-sync Claude Code plugin"
	@echo ""
	@echo "────────────────────────────────────────────────────────────────────────────"
	@echo "👉 To open the Observability Frontend in your browser:"
	@echo "   open http://localhost:5173        (macOS)"
	@echo "   xdg-open http://localhost:5173    (Linux)"
	@echo "   start http://localhost:5173       (Windows)"

# Alias for info
urls: info

# Open Observability Frontend in browser
open:
	@echo "Opening Observability Frontend in browser..."
	@if command -v open > /dev/null 2>&1; then \
		open http://localhost:5173; \
	elif command -v xdg-open > /dev/null 2>&1; then \
		xdg-open http://localhost:5173; \
	elif command -v start > /dev/null 2>&1; then \
		start http://localhost:5173; \
	else \
		echo "Could not detect browser opener. Please manually open: http://localhost:5173"; \
	fi

# Clean up (stop and remove containers, networks, but keep volumes)
clean:
	@echo "Cleaning up (keeping volumes)..."
	docker-compose down

# Clean up everything including volumes
clean-all:
	@echo "Cleaning up everything including volumes..."
	@read -p "This will delete all persistent data. Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "All cleaned up!"; \
	else \
		echo "Cancelled."; \
	fi

# Clean only document storage volume
clean-docs:
	@echo "Cleaning document storage volume..."
	@echo "This will delete all documents and the document database."
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose stop document-server; \
		docker volume rm agent-orchestrator-document-data 2>/dev/null || echo "Volume already removed or doesn't exist"; \
		echo "Document storage cleaned! Restart document-server to create fresh storage."; \
	else \
		echo "Cancelled."; \
	fi

# Individual service logs
logs-obs:
	docker-compose logs observability-backend observability-frontend

logs-doc:
	docker-compose logs document-server

# Individual service restart
restart-obs:
	docker-compose restart observability-backend observability-frontend

restart-doc:
	docker-compose restart document-server
