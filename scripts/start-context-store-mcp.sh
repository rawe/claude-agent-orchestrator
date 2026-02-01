#!/bin/bash
# =============================================================================
# Start Context Store MCP Server - HTTP Mode
# =============================================================================
# MCP URL: http://localhost:9501/mcp
# Connects to Context Store at http://localhost:8766
# Note: Start context-store first!
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# MCP Server configuration
MCP_HOST="0.0.0.0"
MCP_PORT="9501"

# Context Store connection
CONTEXT_STORE_HOST="localhost"
CONTEXT_STORE_PORT="8766"
CONTEXT_STORE_SCHEME="http"

cd "$PROJECT_ROOT/mcps/context-store"

CONTEXT_STORE_HOST="$CONTEXT_STORE_HOST" \
CONTEXT_STORE_PORT="$CONTEXT_STORE_PORT" \
CONTEXT_STORE_SCHEME="$CONTEXT_STORE_SCHEME" \
uv run context-store-mcp.py --http-mode --host "$MCP_HOST" --port "$MCP_PORT"
