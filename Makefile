# ==============================================================================
# Cross-Platform Compatibility (Mac & Windows)
# ==============================================================================
# This Makefile uses bash syntax (conditionals, process management, etc.) and
# must work on both macOS and Windows (via Git Bash).
#
# Key compatibility requirements:
#
# 1. SHELL := bash
#    - Uses PATH lookup instead of hardcoded /bin/bash
#    - Mac: finds /bin/bash via PATH
#    - Windows: finds Git Bash's bash.exe via PATH
#    - Required because Windows PowerShell cannot execute bash syntax
#
# 2. Quoted "$(MAKE)" calls
#    - $(MAKE) expands to the full path of the make binary
#    - Windows paths often contain spaces/parentheses: C:\Program Files (x86)\...
#    - Without quotes, these paths break shell command parsing
#    - All recursive $(MAKE) calls must be quoted: @"$(MAKE)" target
#
# Windows users: Run this Makefile from Git Bash, not PowerShell/CMD
# ==============================================================================

SHELL := bash

.PHONY: help build start stop restart clean status health clean-docs clean-sessions info urls open restart-dashboard restart-coordinator restart-doc start-mcp-atlassian stop-mcp-atlassian start-mcp-ado stop-mcp-ado start-mcp-neo4j stop-mcp-neo4j start-mcp-agent-orchestrator stop-mcp-agent-orchestrator start-mcp-context-store stop-mcp-context-store start-mcps stop-mcps start-all stop-all start-chat-ui stop-chat-ui start-coordinator stop-coordinator start-dashboard stop-dashboard start-context-store stop-context-store start-neo4j stop-neo4j start-elasticsearch stop-elasticsearch start-core stop-core start-agent-runner stop-agent-runner run-agent-runner logs-agent-runner

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
	@echo "Individual Docker services:"
	@echo "  make start-coordinator    - Start only agent-coordinator"
	@echo "  make stop-coordinator     - Stop agent-coordinator"
	@echo "  make start-dashboard      - Start only dashboard"
	@echo "  make stop-dashboard       - Stop dashboard"
	@echo "  make start-context-store  - Start only context-store"
	@echo "  make stop-context-store   - Stop context-store"
	@echo "  make start-elasticsearch  - Start only elasticsearch"
	@echo "  make stop-elasticsearch   - Stop elasticsearch"
	@echo "  make start-neo4j          - Start only neo4j"
	@echo "  make stop-neo4j           - Stop neo4j"
	@echo ""
	@echo "Service profiles:"
	@echo "  make start-core     - Start coordinator + dashboard only (fast startup)"
	@echo "  make stop-core      - Stop coordinator + dashboard"
	@echo ""
	@echo "Restart individual services:"
	@echo "  make restart-dashboard    - Restart dashboard"
	@echo "  make restart-coordinator  - Restart agent coordinator"
	@echo "  make restart-doc          - Restart context store"
	@echo ""
	@echo "Agent Runner (local process):"
	@echo "  make start-agent-runner   - Start in background (logs to .agent-runner.log)"
	@echo "  make stop-agent-runner    - Stop agent runner"
	@echo "  make run-agent-runner     - Run in foreground (Ctrl+C to stop)"
	@echo "  make run-agent-runner-v   - Run in foreground with verbose/debug output"
	@echo "  make logs-agent-runner    - Tail logs (Ctrl+C to stop watching)"
	@echo ""
	@echo "MCP servers (mcps/):"
	@echo "  make start-mcp-agent-orchestrator - Start Agent Orchestrator MCP"
	@echo "  make stop-mcp-agent-orchestrator  - Stop Agent Orchestrator MCP"
	@echo "  make start-mcp-context-store      - Start Context Store MCP"
	@echo "  make stop-mcp-context-store       - Stop Context Store MCP"
	@echo "  make start-mcp-atlassian          - Start Atlassian MCP (Jira + Confluence)"
	@echo "  make stop-mcp-atlassian           - Stop Atlassian MCP"
	@echo "  make start-mcp-ado                - Start Azure DevOps MCP"
	@echo "  make stop-mcp-ado                 - Stop Azure DevOps MCP"
	@echo "  make start-mcp-neo4j              - Start Neo4j MCP"
	@echo "  make stop-mcp-neo4j               - Stop Neo4j MCP"
	@echo "  make start-mcps                   - Start all MCP servers"
	@echo "  make stop-mcps                    - Stop all MCP servers"
	@echo ""
	@echo "All services:"
	@echo "  make start-all      - Start core services + all MCP servers"
	@echo "  make stop-all       - Stop everything"
	@echo ""
	@echo "Applications (interfaces/):"
	@echo "  make start-chat-ui         - Start Chat UI (Docker)"
	@echo "  make stop-chat-ui          - Stop Chat UI (Docker)"

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
	@"$(MAKE)" --no-print-directory info
	@echo ""
	@echo "💡 Quick commands:"
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
	@echo "Agent Coordinator (port 8765):"
	@curl -s http://localhost:8765/health || echo "  ❌ Not responding"
	@echo ""
	@echo "Context Store (port 8766):"
	@curl -s http://localhost:8766/health || echo "  ❌ Not responding"
	@echo ""
	@echo "Neo4j (port 7475):"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:7475 || echo "  ❌ Not responding"

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
	@echo "⚙️  AGENT COORDINATOR"
	@echo "   URL:         http://localhost:8765"
	@echo "   Purpose:     Session management, observability, and agent blueprints"
	@echo "   Endpoints:   /health, /sessions, /events/{id}, /ws, /agents"
	@echo ""
	@echo "📄 CONTEXT STORE"
	@echo "   URL:         http://localhost:8766"
	@echo "   Purpose:     Document storage and retrieval"
	@echo "   Endpoints:   /health, /documents, /upload, /download"
	@echo ""
	@echo "🔗 NEO4J"
	@echo "   Browser:     http://localhost:7475"
	@echo "   Bolt:        bolt://localhost:7688"
	@echo "   Credentials: neo4j / agent-orchestrator"
	@echo "   Purpose:     Graph database for knowledge graphs"
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
# This removes: sessions, documents, elasticsearch index, and neo4j data
clean-all:
	@echo "Cleaning up everything including volumes..."
	@echo "  - Session data (agent-orchestrator-coordinator-data)"
	@echo "  - Document storage (agent-orchestrator-document-data)"
	@echo "  - Elasticsearch index (context-store-es-data)"
	@echo "  - Neo4j graph data (agent-orchestrator-neo4j-data)"
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
		docker-compose stop agent-coordinator; \
		docker volume rm agent-orchestrator-coordinator-data 2>/dev/null || echo "Volume already removed or doesn't exist"; \
		echo "Session storage cleaned! Restart agent-coordinator to create fresh storage."; \
	else \
		echo "Cancelled."; \
	fi

# Individual service restart
restart-dashboard:
	docker-compose restart dashboard

restart-coordinator:
	docker-compose restart agent-coordinator

restart-doc:
	docker-compose restart context-store

# ============================================================================
# INDIVIDUAL DOCKER SERVICES (granular control)
# ============================================================================
# Use these when you only need specific services.
# Note: --no-deps means dependencies won't be started automatically.
#       Use start-core for common coordinator+dashboard combo.

start-coordinator:
	@echo "Starting Agent Coordinator..."
	docker-compose up -d --no-deps agent-coordinator
	@echo "Agent Coordinator started: http://localhost:8765"

stop-coordinator:
	@echo "Stopping Agent Coordinator..."
	docker-compose stop agent-coordinator

start-dashboard:
	@echo "Starting Dashboard..."
	@echo "(Note: Requires agent-coordinator to be running)"
	docker-compose up -d --no-deps dashboard
	@echo "Dashboard started: http://localhost:3000"

stop-dashboard:
	@echo "Stopping Dashboard..."
	docker-compose stop dashboard

start-context-store:
	@echo "Starting Context Store..."
	@echo "(Note: Semantic search requires elasticsearch)"
	docker-compose up -d --no-deps context-store
	@echo "Context Store started: http://localhost:8766"

stop-context-store:
	@echo "Stopping Context Store..."
	docker-compose stop context-store

start-elasticsearch:
	@echo "Starting Elasticsearch..."
	docker-compose up -d --no-deps elasticsearch
	@echo "Elasticsearch started: http://localhost:9200"

stop-elasticsearch:
	@echo "Stopping Elasticsearch..."
	docker-compose stop elasticsearch

start-neo4j:
	@echo "Starting Neo4j..."
	docker-compose up -d --no-deps neo4j
	@echo "Neo4j started: http://localhost:7475 (bolt: 7688)"

stop-neo4j:
	@echo "Stopping Neo4j..."
	docker-compose stop neo4j

# ============================================================================
# SERVICE PROFILES (common combinations)
# ============================================================================

# Core services only: coordinator + dashboard (no elasticsearch, no neo4j)
# Use this for UI development or when you don't need document storage
start-core:
	@echo "Starting core services (coordinator + dashboard)..."
	docker-compose up -d --no-deps agent-coordinator dashboard
	@echo ""
	@echo "Core services started:"
	@echo "  Dashboard:    http://localhost:3000"
	@echo "  Coordinator:  http://localhost:8765"
	@echo ""
	@echo "Note: Context Store not started. Run 'make start-context-store' if needed."

stop-core:
	@echo "Stopping core services..."
	docker-compose stop agent-coordinator dashboard

# ============================================================================
# AGENT RUNNER (local process, not Docker)
# ============================================================================
# Runs agents in a specific project directory.
# Uses PROJECT_DIR from .env or AGENT_ORCHESTRATOR_PROJECT_DIR as fallback.

AGENT_RUNNER_SCRIPT := servers/agent-runner/agent-runner
AGENT_RUNNER_PID_FILE := .agent-runner.pid
AGENT_RUNNER_LOG_FILE := .agent-runner.log

start-agent-runner:
	@echo "Starting Agent Runner..."
	@if [ -f $(AGENT_RUNNER_PID_FILE) ] && kill -0 $$(cat $(AGENT_RUNNER_PID_FILE)) 2>/dev/null; then \
		echo "Agent Runner already running (PID: $$(cat $(AGENT_RUNNER_PID_FILE)))"; \
		echo "Use 'make logs-agent-runner' to view logs"; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		set -a && . ./.env && set +a; \
	fi; \
	PROJ_DIR="$${PROJECT_DIR:-$${AGENT_ORCHESTRATOR_PROJECT_DIR:-.}}"; \
	if [ "$$PROJ_DIR" = "." ]; then \
		echo "Warning: No PROJECT_DIR set. Using current directory."; \
		echo "Set PROJECT_DIR in .env or use: make start-agent-runner PROJECT_DIR=/path/to/project"; \
	fi; \
	echo "Configuration:"; \
	echo "  Project Dir: $$PROJ_DIR"; \
	echo "  Coordinator: $${AGENT_ORCHESTRATOR_API_URL:-http://localhost:8765}"; \
	echo "  Log file:    $(AGENT_RUNNER_LOG_FILE)"; \
	echo ""; \
	PROJECT_DIR="$$PROJ_DIR" $(AGENT_RUNNER_SCRIPT) > $(AGENT_RUNNER_LOG_FILE) 2>&1 & \
	echo $$! > $(AGENT_RUNNER_PID_FILE); \
	sleep 2; \
	echo "Agent Runner started (PID: $$(cat $(AGENT_RUNNER_PID_FILE)))"; \
	echo ""; \
	echo "View logs:  make logs-agent-runner"

stop-agent-runner:
	@echo "Stopping Agent Runner..."
	@if [ -f $(AGENT_RUNNER_PID_FILE) ]; then \
		PID=$$(cat $(AGENT_RUNNER_PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "Agent Runner stopped (PID: $$PID)"; \
		else \
			echo "Agent Runner not running (stale PID file)"; \
		fi; \
		rm -f $(AGENT_RUNNER_PID_FILE); \
	else \
		echo "No PID file found. Trying to find and kill process..."; \
		pkill -f "agent-runner/agent-runner" 2>/dev/null && echo "Agent Runner stopped" || echo "No Agent Runner process found"; \
	fi

# Run agent runner in foreground (direct output, Ctrl+C to stop)
run-agent-runner:
	@if [ -f .env ]; then \
		set -a && . ./.env && set +a; \
	fi; \
	PROJ_DIR="$${PROJECT_DIR:-$${AGENT_ORCHESTRATOR_PROJECT_DIR:-.}}"; \
	if [ "$$PROJ_DIR" = "." ]; then \
		echo "Warning: No PROJECT_DIR set. Using current directory."; \
	fi; \
	VERBOSE_FLAG=""; \
	if [ "$${VERBOSE:-}" = "1" ]; then \
		VERBOSE_FLAG="--verbose"; \
	fi; \
	echo "Starting Agent Runner in foreground (Ctrl+C to stop)..."; \
	echo "  Project Dir: $$PROJ_DIR"; \
	if [ -n "$$VERBOSE_FLAG" ]; then echo "  Verbose: enabled"; fi; \
	echo ""; \
	PROJECT_DIR="$$PROJ_DIR" $(AGENT_RUNNER_SCRIPT) $$VERBOSE_FLAG

# Run agent runner in foreground with verbose output (shortcut)
run-agent-runner-v:
	@$(MAKE) run-agent-runner VERBOSE=1

# Tail agent runner logs
logs-agent-runner:
	@if [ -f $(AGENT_RUNNER_LOG_FILE) ]; then \
		echo "Tailing $(AGENT_RUNNER_LOG_FILE) (Ctrl+C to stop)..."; \
		echo ""; \
		tail -f $(AGENT_RUNNER_LOG_FILE); \
	else \
		echo "No log file found. Start the agent runner first: make start-agent-runner"; \
	fi

# External MCP servers (mcps/)
start-mcp-atlassian:
	@echo "Starting Atlassian MCP server..."
	@if [ ! -f mcps/atlassian/.env ]; then \
		echo "⚠️  No .env file found. Copy the example and configure credentials:"; \
		echo "   cp mcps/atlassian/.env.example mcps/atlassian/.env"; \
		exit 1; \
	fi
	@cd mcps/atlassian && docker compose up -d
	@echo "Atlassian MCP started: http://localhost:9000"

stop-mcp-atlassian:
	@echo "Stopping Atlassian MCP server..."
	@cd mcps/atlassian && docker compose down

start-mcp-ado:
	@echo "Starting Azure DevOps MCP server..."
	@if [ ! -f mcps/ado/.env ]; then \
		echo "⚠️  No .env file found. Copy the example and configure credentials:"; \
		echo "   cp mcps/ado/.env.example mcps/ado/.env"; \
		exit 1; \
	fi
	@cd mcps/ado && docker compose up -d --build
	@echo "Azure DevOps MCP started: http://localhost:9001"

stop-mcp-ado:
	@echo "Stopping Azure DevOps MCP server..."
	@cd mcps/ado && docker compose down

start-mcp-neo4j:
	@echo "Starting Neo4j MCP server..."
	@if [ ! -f mcps/neo4j/.env ]; then \
		echo "ℹ️  No .env file found. Using defaults (connecting to local Neo4j container)."; \
		echo "   To customize, copy: cp mcps/neo4j/.env.example mcps/neo4j/.env"; \
	fi
	@cd mcps/neo4j && docker compose up -d
	@echo "Neo4j MCP started: http://localhost:9003"

stop-mcp-neo4j:
	@echo "Stopping Neo4j MCP server..."
	@cd mcps/neo4j && docker compose down

# Start all MCP servers
# - Agent Orchestrator and Context Store are REQUIRED (no prefix, will abort on failure)
# - Atlassian, ADO, Neo4j are OPTIONAL and need external credentials (- prefix ignores failures)
#   The "-" prefix tells Make to continue even if the command fails, showing warnings but not stopping
start-mcps:
	@echo "Starting all MCP servers..."
	@"$(MAKE)" --no-print-directory start-mcp-agent-orchestrator
	@"$(MAKE)" --no-print-directory start-mcp-context-store
	-@"$(MAKE)" --no-print-directory start-mcp-atlassian
	-@"$(MAKE)" --no-print-directory start-mcp-ado
	-@"$(MAKE)" --no-print-directory start-mcp-neo4j

stop-mcps:
	@echo "Stopping all MCP servers..."
	@"$(MAKE)" --no-print-directory stop-mcp-agent-orchestrator
	@"$(MAKE)" --no-print-directory stop-mcp-context-store
	@"$(MAKE)" --no-print-directory stop-mcp-atlassian
	@"$(MAKE)" --no-print-directory stop-mcp-ado
	@"$(MAKE)" --no-print-directory stop-mcp-neo4j

# Agent Orchestrator MCP server (HTTP mode)
# Loads configuration from .env file
AO_MCP_SERVER_SCRIPT := mcps/agent-orchestrator/agent-orchestrator-mcp.py
AO_MCP_SERVER_PID_FILE := .mcp-agent-orchestrator.pid

start-mcp-agent-orchestrator:
	@echo "Starting Agent Orchestrator MCP server..."
	@if [ -f .env ]; then \
		set -a && . ./.env && set +a; \
	fi; \
	PORT=$${AGENT_ORCHESTRATOR_MCP_PORT:-9500}; \
	HOST=$${AGENT_ORCHESTRATOR_MCP_HOST:-127.0.0.1}; \
	if [ -f $(AO_MCP_SERVER_PID_FILE) ] && kill -0 $$(cat $(AO_MCP_SERVER_PID_FILE)) 2>/dev/null; then \
		echo "MCP server already running (PID: $$(cat $(AO_MCP_SERVER_PID_FILE)))"; \
		exit 1; \
	fi; \
	echo "Configuration:"; \
	echo "  Host: $$HOST"; \
	echo "  Port: $$PORT"; \
	echo "  Project Dir: $${AGENT_ORCHESTRATOR_PROJECT_DIR:-<not set, uses tool parameter>}"; \
	echo ""; \
	AGENT_ORCHESTRATOR_PROJECT_DIR="$${AGENT_ORCHESTRATOR_PROJECT_DIR}" \
	uv run --script $(AO_MCP_SERVER_SCRIPT) --http-mode --host $$HOST --port $$PORT & \
	echo $$! > $(AO_MCP_SERVER_PID_FILE); \
	sleep 2; \
	echo ""; \
	echo "Agent Orchestrator MCP started (PID: $$(cat $(AO_MCP_SERVER_PID_FILE)))"; \
	echo "Endpoint: http://$$HOST:$$PORT/mcp"

stop-mcp-agent-orchestrator:
	@echo "Stopping Agent Orchestrator MCP server..."
	@if [ -f $(AO_MCP_SERVER_PID_FILE) ]; then \
		PID=$$(cat $(AO_MCP_SERVER_PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "Server stopped (PID: $$PID)"; \
		else \
			echo "Server not running (stale PID file)"; \
		fi; \
		rm -f $(AO_MCP_SERVER_PID_FILE); \
	else \
		echo "No PID file found. Trying to find and kill process..."; \
		pkill -f "agent-orchestrator-mcp.py --http-mode" 2>/dev/null && echo "Server stopped" || echo "No server found"; \
	fi

# Context Store MCP server (HTTP mode)
# Loads configuration from .env file
CS_MCP_SERVER_SCRIPT := mcps/context-store/context-store-mcp.py
CS_MCP_SERVER_PID_FILE := .mcp-context-store.pid

start-mcp-context-store:
	@echo "Starting Context Store MCP server..."
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
	uv run --script $(CS_MCP_SERVER_SCRIPT) --http-mode --host $$HOST --port $$PORT & \
	echo $$! > $(CS_MCP_SERVER_PID_FILE); \
	sleep 2; \
	echo ""; \
	echo "Context Store MCP started (PID: $$(cat $(CS_MCP_SERVER_PID_FILE)))"; \
	echo "Endpoint: http://$$HOST:$$PORT/mcp"

stop-mcp-context-store:
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

# Start/stop all services (core + MCPs)
start-all:
	@echo "Starting all services..."
	@echo ""
	@"$(MAKE)" --no-print-directory start-bg
	@echo ""
	@"$(MAKE)" --no-print-directory start-mcps
	@echo ""
	@echo "============================================"
	@echo "All services started!"
	@echo "============================================"

stop-all:
	@echo "Stopping all services..."
	@echo ""
	@"$(MAKE)" --no-print-directory stop
	@echo ""
	@"$(MAKE)" --no-print-directory stop-mcps
	@echo ""
	@echo "============================================"
	@echo "All services stopped!"
	@echo "============================================"

# ============================================================================
# Applications using Agent Orchestrator Framework (interfaces/)
# ============================================================================

# Chat UI (Docker-based)
CHAT_UI_DIR := interfaces/chat-ui

start-chat-ui:
	@echo "Starting Chat UI..."
	@if [ ! -f $(CHAT_UI_DIR)/.env ]; then \
		echo "No .env file found. Copying from .env.example..."; \
		cp $(CHAT_UI_DIR)/.env.example $(CHAT_UI_DIR)/.env; \
		echo "Created $(CHAT_UI_DIR)/.env - edit if needed"; \
	fi
	@echo "Building and starting Docker container..."
	@cd $(CHAT_UI_DIR) && docker compose up -d --build
	@echo ""
	@echo "Chat UI started"
	@echo "URL: http://localhost:3010"

stop-chat-ui:
	@echo "Stopping Chat UI..."
	@cd $(CHAT_UI_DIR) && docker compose down
	@echo "Chat UI stopped"
