#!/bin/bash
# =============================================================================
# Start Agent Coordinator - Development Mode
# =============================================================================
# - Auth disabled (AUTH_ENABLED=false) - DO NOT USE IN PRODUCTION
# - API docs enabled at http://localhost:8765/docs
# - CORS allows all origins
# - Agents loaded from config/agents/
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/servers/agent-coordinator"

AUTH_ENABLED=false \
DOCS_ENABLED=true \
CORS_ORIGINS=* \
AGENT_ORCHESTRATOR_AGENTS_DIR="$PROJECT_ROOT/config/agents" \
uv run python -m main
