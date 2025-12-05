.PHONY: help build start stop restart logs clean status health clean-docs clean-sessions info urls open logs-dashboard logs-runtime logs-doc restart-dashboard restart-runtime restart-doc start-mcps stop-mcps logs-mcps start-ao-mcp stop-ao-mcp start-ao-api stop-ao-api start-cs-mcp stop-cs-mcp start-demo stop-demo

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
	@echo "  make open           - Open Dashboard in browser"
	@echo "  make clean          - Stop and remove all containers, networks (keeps data)"
	@echo "  make clean-all      - Stop and remove everything including all data volumes"
	@echo "                        (sessions, documents, elasticsearch index)"
	@echo "  make clean-docs     - Remove ONLY the document storage volume"
	@echo "  make clean-sessions - Remove ONLY the session storage volume"
	@echo ""
	@echo "Individual service commands:"
	@echo "  make logs-dashboard - View dashboard logs"
	@echo "  make logs-runtime   - View agent runtime logs"
	@echo "  make logs-doc       - View context store logs"
	@echo "  make restart-dashboard - Restart dashboard"
	@echo "  make restart-runtime - Restart agent runtime"
	@echo "  make restart-doc    - Restart context store"
	@echo ""
	@echo "Example MCP servers (config/mcps):"
	@echo "  make start-mcps     - Start Atlassian & ADO MCP servers"
	@echo "  make stop-mcps      - Stop MCP servers"
	@echo "  make logs-mcps      - View MCP server logs"
	@echo ""
	@echo "MCP servers (HTTP mode):"
	@echo "  make start-ao-mcp   - Start Agent Orchestrator MCP server (HTTP)"
	@echo "  make stop-ao-mcp    - Stop Agent Orchestrator MCP server"
	@echo "  make start-ao-api   - Start Agent Orchestrator API server (REST + MCP)"
	@echo "  make stop-ao-api    - Stop Agent Orchestrator API server"
	@echo "  make start-cs-mcp   - Start Context Store MCP server (HTTP)"
	@echo "  make stop-cs-mcp    - Stop Context Store MCP server"
	@echo ""
	@echo "Demo commands (starts/stops all services):"
	@echo "  make start-demo     - Start all services for demo"
	@echo "  make stop-demo      - Stop all demo services"

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
	@echo "Dashboard (port 3000):"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:3000 || echo "  ❌ Not responding"
	@echo ""
	@echo "Agent Runtime (port 8765):"
	@curl -s http://localhost:8765/health || echo "  ❌ Not responding"
	@echo ""
	@echo "Context Store (port 8766):"
	@curl -s http://localhost:8766/health || echo "  ❌ Not responding"

# Show service information
info:
	@echo "╔════════════════════════════════════════════════════════════════════════════╗"
	@echo "║          Agent Orchestrator Framework - Service Information               ║"
	@echo "╚════════════════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🌐 DASHBOARD"
	@echo "   URL:         http://localhost:3000"
	@echo "   Purpose:     Unified UI for agent management, sessions, and documents"
	@echo "   Action:      Open this URL in your browser"
	@echo ""
	@echo "⚙️  AGENT RUNTIME"
	@echo "   URL:         http://localhost:8765"
	@echo "   Purpose:     Session management, observability, and agent blueprints"
	@echo "   Endpoints:   /health, /sessions, /events/{id}, /ws, /agents"
	@echo ""
	@echo "📄 CONTEXT STORE"
	@echo "   URL:         http://localhost:8766"
	@echo "   Purpose:     Document storage and retrieval"
	@echo "   Endpoints:   /health, /documents, /upload, /download"
	@echo ""
	@echo "────────────────────────────────────────────────────────────────────────────"
	@echo "👉 To open the Dashboard in your browser:"
	@echo "   open http://localhost:3000        (macOS)"
	@echo "   xdg-open http://localhost:3000    (Linux)"
	@echo "   start http://localhost:3000       (Windows)"

# Alias for info
urls: info

# Open Dashboard in browser
open:
	@echo "Opening Dashboard in browser..."
	@if command -v open > /dev/null 2>&1; then \
		open http://localhost:3000; \
	elif command -v xdg-open > /dev/null 2>&1; then \
		xdg-open http://localhost:3000; \
	elif command -v start > /dev/null 2>&1; then \
		start http://localhost:3000; \
	else \
		echo "Could not detect browser opener. Please manually open: http://localhost:3000"; \
	fi

# Clean up (stop and remove containers, networks, but keep volumes)
clean:
	@echo "Cleaning up (keeping volumes)..."
	docker-compose down

# Clean up everything including volumes
# This removes: sessions, documents, and elasticsearch semantic search index
clean-all:
	@echo "Cleaning up everything including volumes..."
	@echo "  - Session data (agent-orchestrator-runtime-data)"
	@echo "  - Document storage (agent-orchestrator-document-data)"
	@echo "  - Elasticsearch index (context-store-es-data)"
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
		docker-compose stop context-store; \
		docker volume rm agent-orchestrator-document-data 2>/dev/null || echo "Volume already removed or doesn't exist"; \
		echo "Document storage cleaned! Restart context-store to create fresh storage."; \
	else \
		echo "Cancelled."; \
	fi

# Clean only session storage volume
clean-sessions:
	@echo "Cleaning session storage volume..."
	@echo "This will delete all session history and events."
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose stop agent-runtime; \
		docker volume rm agent-orchestrator-runtime-data 2>/dev/null || echo "Volume already removed or doesn't exist"; \
		echo "Session storage cleaned! Restart agent-runtime to create fresh storage."; \
	else \
		echo "Cancelled."; \
	fi

# Individual service logs
logs-dashboard:
	docker-compose logs dashboard

logs-runtime:
	docker-compose logs agent-runtime

logs-doc:
	docker-compose logs context-store

# Individual service restart
restart-dashboard:
	docker-compose restart dashboard

restart-runtime:
	docker-compose restart agent-runtime

restart-doc:
	docker-compose restart context-store

# Example MCP servers (for agent capabilities)
start-mcps:
	@echo "Starting example MCP servers..."
	@if [ ! -f config/mcps/.env ]; then \
		echo "⚠️  No .env file found. Copy the example and configure credentials:"; \
		echo "   cp config/mcps/.env.example config/mcps/.env"; \
		exit 1; \
	fi
	docker compose -f config/mcps/docker-compose.yml up -d --build
	@echo ""
	@echo "MCP servers started:"
	@echo "  - Atlassian (Jira + Confluence): http://localhost:9000"
	@echo "  - Azure DevOps:                  http://localhost:9001"

stop-mcps:
	@echo "Stopping MCP servers..."
	docker compose -f config/mcps/docker-compose.yml down

logs-mcps:
	docker compose -f config/mcps/docker-compose.yml logs -f

# Agent Orchestrator MCP server (HTTP mode)
# Loads configuration from .env file
MCP_SERVER_SCRIPT := interfaces/agent-orchestrator-mcp-server/agent-orchestrator-mcp.py
MCP_SERVER_PID_FILE := .agent-orchestrator-mcp-server.pid

start-ao-mcp:
	@echo "Starting Agent Orchestrator MCP server (HTTP mode)..."
	@if [ -f .env ]; then \
		set -a && . ./.env && set +a; \
	fi; \
	PORT=$${AGENT_ORCHESTRATOR_MCP_PORT:-9500}; \
	HOST=$${AGENT_ORCHESTRATOR_MCP_HOST:-127.0.0.1}; \
	if [ -f $(MCP_SERVER_PID_FILE) ] && kill -0 $$(cat $(MCP_SERVER_PID_FILE)) 2>/dev/null; then \
		echo "MCP server already running (PID: $$(cat $(MCP_SERVER_PID_FILE)))"; \
		exit 1; \
	fi; \
	echo "Configuration:"; \
	echo "  Host: $$HOST"; \
	echo "  Port: $$PORT"; \
	echo "  Project Dir: $${AGENT_ORCHESTRATOR_PROJECT_DIR:-<not set, uses tool parameter>}"; \
	echo ""; \
	AGENT_ORCHESTRATOR_PROJECT_DIR="$${AGENT_ORCHESTRATOR_PROJECT_DIR}" \
	uv run $(MCP_SERVER_SCRIPT) --http-mode --host $$HOST --port $$PORT & \
	echo $$! > $(MCP_SERVER_PID_FILE); \
	sleep 2; \
	echo ""; \
	echo "MCP server started (PID: $$(cat $(MCP_SERVER_PID_FILE)))"; \
	echo "Endpoint: http://$$HOST:$$PORT/mcp"

stop-ao-mcp:
	@echo "Stopping Agent Orchestrator MCP server..."
	@if [ -f $(MCP_SERVER_PID_FILE) ]; then \
		PID=$$(cat $(MCP_SERVER_PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "Server stopped (PID: $$PID)"; \
		else \
			echo "Server not running (stale PID file)"; \
		fi; \
		rm -f $(MCP_SERVER_PID_FILE); \
	else \
		echo "No PID file found. Trying to find and kill process..."; \
		pkill -f "agent-orchestrator-mcp.py --http-mode" 2>/dev/null && echo "Server stopped" || echo "No server found"; \
	fi

# Agent Orchestrator API server (REST + MCP combined)
# Provides both MCP protocol at /mcp and REST API at /api with OpenAPI docs
API_SERVER_PID_FILE := .agent-orchestrator-api-server.pid

start-ao-api:
	@echo "Starting Agent Orchestrator API server (REST + MCP)..."
	@if [ -f .env ]; then \
		set -a && . ./.env && set +a; \
	fi; \
	PORT=$${AGENT_ORCHESTRATOR_MCP_PORT:-9500}; \
	HOST=$${AGENT_ORCHESTRATOR_MCP_HOST:-127.0.0.1}; \
	if [ -f $(API_SERVER_PID_FILE) ] && kill -0 $$(cat $(API_SERVER_PID_FILE)) 2>/dev/null; then \
		echo "API server already running (PID: $$(cat $(API_SERVER_PID_FILE)))"; \
		exit 1; \
	fi; \
	echo "Configuration:"; \
	echo "  Host: $$HOST"; \
	echo "  Port: $$PORT"; \
	echo "  Project Dir: $${AGENT_ORCHESTRATOR_PROJECT_DIR:-<not set, uses tool parameter>}"; \
	echo ""; \
	AGENT_ORCHESTRATOR_PROJECT_DIR="$${AGENT_ORCHESTRATOR_PROJECT_DIR}" \
	uv run $(MCP_SERVER_SCRIPT) --api-mode --host $$HOST --port $$PORT & \
	echo $$! > $(API_SERVER_PID_FILE); \
	sleep 2; \
	echo ""; \
	echo "API server started (PID: $$(cat $(API_SERVER_PID_FILE)))"; \
	echo ""; \
	echo "Endpoints:"; \
	echo "  MCP Protocol:  http://$$HOST:$$PORT/mcp"; \
	echo "  REST API:      http://$$HOST:$$PORT/api"; \
	echo "  API Docs:      http://$$HOST:$$PORT/api/docs"; \
	echo "  ReDoc:         http://$$HOST:$$PORT/api/redoc"

stop-ao-api:
	@echo "Stopping Agent Orchestrator API server..."
	@if [ -f $(API_SERVER_PID_FILE) ]; then \
		PID=$$(cat $(API_SERVER_PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "Server stopped (PID: $$PID)"; \
		else \
			echo "Server not running (stale PID file)"; \
		fi; \
		rm -f $(API_SERVER_PID_FILE); \
	else \
		echo "No PID file found. Trying to find and kill process..."; \
		pkill -f "agent-orchestrator-mcp.py --api-mode" 2>/dev/null && echo "Server stopped" || echo "No server found"; \
	fi

# Context Store MCP server (HTTP mode)
# Loads configuration from .env file
CS_MCP_SERVER_SCRIPT := interfaces/context-store-mcp-server/context-store-mcp.py
CS_MCP_SERVER_PID_FILE := .context-store-mcp-server.pid

start-cs-mcp:
	@echo "Starting Context Store MCP server (HTTP mode)..."
	@if [ -f .env ]; then \
		set -a && . ./.env && set +a; \
	fi; \
	PORT=$${CONTEXT_STORE_MCP_PORT:-9501}; \
	HOST=$${CONTEXT_STORE_MCP_HOST:-127.0.0.1}; \
	if [ -f $(CS_MCP_SERVER_PID_FILE) ] && kill -0 $$(cat $(CS_MCP_SERVER_PID_FILE)) 2>/dev/null; then \
		echo "MCP server already running (PID: $$(cat $(CS_MCP_SERVER_PID_FILE)))"; \
		exit 1; \
	fi; \
	echo "Configuration:"; \
	echo "  Host: $$HOST"; \
	echo "  Port: $$PORT"; \
	echo ""; \
	uv run $(CS_MCP_SERVER_SCRIPT) --http-mode --host $$HOST --port $$PORT & \
	echo $$! > $(CS_MCP_SERVER_PID_FILE); \
	sleep 2; \
	echo ""; \
	echo "MCP server started (PID: $$(cat $(CS_MCP_SERVER_PID_FILE)))"; \
	echo "Endpoint: http://$$HOST:$$PORT/mcp"

stop-cs-mcp:
	@echo "Stopping Context Store MCP server..."
	@if [ -f $(CS_MCP_SERVER_PID_FILE) ]; then \
		PID=$$(cat $(CS_MCP_SERVER_PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "Server stopped (PID: $$PID)"; \
		else \
			echo "Server not running (stale PID file)"; \
		fi; \
		rm -f $(CS_MCP_SERVER_PID_FILE); \
	else \
		echo "No PID file found. Trying to find and kill process..."; \
		pkill -f "context-store-mcp.py --http-mode" 2>/dev/null && echo "Server stopped" || echo "No server found"; \
	fi

# Demo commands - start/stop all services
start-demo:
	@echo "Starting all demo services..."
	@echo ""
	@$(MAKE) --no-print-directory start-bg
	@echo ""
	@$(MAKE) --no-print-directory start-mcps
	@echo ""
	@$(MAKE) --no-print-directory start-ao-api
	@echo ""
	@$(MAKE) --no-print-directory start-cs-mcp
	@echo ""
	@echo "============================================"
	@echo "All demo services started!"
	@echo "============================================"

stop-demo:
	@echo "Stopping all demo services..."
	@echo ""
	@$(MAKE) --no-print-directory stop
	@echo ""
	@$(MAKE) --no-print-directory stop-mcps
	@echo ""
	@$(MAKE) --no-print-directory stop-ao-api
	@echo ""
	@$(MAKE) --no-print-directory stop-cs-mcp
	@echo ""
	@echo "============================================"
	@echo "All demo services stopped!"
	@echo "============================================"
