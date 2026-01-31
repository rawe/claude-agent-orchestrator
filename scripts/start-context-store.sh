#!/bin/bash
# =============================================================================
# Start Context Store Server - Development Mode
# =============================================================================
#
# Usage:
#   ./scripts/start-context-store.sh            # Context Store only
#   ./scripts/start-context-store.sh --with-mcp # Context Store + MCP Server
#
# Context Store Server (Document API):
#   - URL: http://localhost:8766
#   - Data dir: .agent-orchestrator/context-store-data/
#   - Semantic search: disabled (no Elasticsearch/Ollama required)
#   - CORS: allows all origins (*)
#
# MCP Server (when --with-mcp):
#   - URL: http://localhost:9501/mcp
#   - Connects to Context Store at http://localhost:8766
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# =============================================================================
# Configuration
# =============================================================================

# Context Store Server settings
CONTEXT_STORE_HOST="0.0.0.0"
CONTEXT_STORE_PORT="8766"
CONTEXT_STORE_SCHEME="http"
CONTEXT_STORE_PUBLIC_URL="http://localhost:${CONTEXT_STORE_PORT}"

# Data directory (isolated dev data)
DATA_DIR="$PROJECT_ROOT/.agent-orchestrator/context-store-data"

# MCP Server settings (only used with --with-mcp)
MCP_HOST="0.0.0.0"
MCP_PORT="9501"

# =============================================================================
# Main
# =============================================================================

# Parse arguments
WITH_MCP=false
if [[ "$1" == "--with-mcp" ]]; then
    WITH_MCP=true
fi

# Ensure data directory exists
mkdir -p "$DATA_DIR/files"

# Cleanup function for graceful shutdown
cleanup() {
    echo ""
    echo "Shutting down..."
    if [[ -n "$MCP_PID" ]]; then
        kill "$MCP_PID" 2>/dev/null || true
    fi
    if [[ -n "$CONTEXT_STORE_PID" ]]; then
        kill "$CONTEXT_STORE_PID" 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT

if [[ "$WITH_MCP" == "true" ]]; then
    # ==========================================================================
    # Mode: Context Store + MCP Server
    # ==========================================================================
    echo "Starting Context Store + MCP Server..."
    echo ""

    # Start Context Store in background
    echo "[Context Store] Starting on http://localhost:${CONTEXT_STORE_PORT}..."
    cd "$PROJECT_ROOT/servers/context-store"

    DOCUMENT_SERVER_HOST="$CONTEXT_STORE_HOST" \
    DOCUMENT_SERVER_PORT="$CONTEXT_STORE_PORT" \
    DOCUMENT_SERVER_STORAGE="$DATA_DIR/files" \
    DOCUMENT_SERVER_DB="$DATA_DIR/documents.db" \
    DOCUMENT_SERVER_PUBLIC_URL="$CONTEXT_STORE_PUBLIC_URL" \
    SEMANTIC_SEARCH_ENABLED=false \
    CORS_ORIGINS="*" \
    uv run python -m src.main &
    CONTEXT_STORE_PID=$!

    # Wait for Context Store to be ready
    echo "[Context Store] Waiting for server to be ready..."
    for i in {1..30}; do
        if curl -s "http://localhost:${CONTEXT_STORE_PORT}/health" > /dev/null 2>&1; then
            echo "[Context Store] Ready!"
            break
        fi
        if [[ $i -eq 30 ]]; then
            echo "[Context Store] Warning: Health check timed out, starting MCP anyway..."
        fi
        sleep 1
    done

    # Start MCP Server
    echo ""
    echo "[MCP Server] Starting on http://localhost:${MCP_PORT}/mcp..."
    cd "$PROJECT_ROOT/mcps/context-store"

    CONTEXT_STORE_HOST="localhost" \
    CONTEXT_STORE_PORT="$CONTEXT_STORE_PORT" \
    CONTEXT_STORE_SCHEME="$CONTEXT_STORE_SCHEME" \
    uv run context-store-mcp.py --http-mode --host "$MCP_HOST" --port "$MCP_PORT" &
    MCP_PID=$!

    echo ""
    echo "============================================"
    echo "Services running:"
    echo "  Context Store: http://localhost:${CONTEXT_STORE_PORT}"
    echo "  MCP Server:    http://localhost:${MCP_PORT}/mcp"
    echo "============================================"
    echo "Press Ctrl+C to stop all services"
    echo ""

    # Wait for either process to exit
    wait $CONTEXT_STORE_PID $MCP_PID

else
    # ==========================================================================
    # Mode: Context Store only
    # ==========================================================================
    echo "Starting Context Store Server..."
    echo "  URL: http://localhost:${CONTEXT_STORE_PORT}"
    echo "  Data: $DATA_DIR"
    echo ""

    cd "$PROJECT_ROOT/servers/context-store"

    DOCUMENT_SERVER_HOST="$CONTEXT_STORE_HOST" \
    DOCUMENT_SERVER_PORT="$CONTEXT_STORE_PORT" \
    DOCUMENT_SERVER_STORAGE="$DATA_DIR/files" \
    DOCUMENT_SERVER_DB="$DATA_DIR/documents.db" \
    DOCUMENT_SERVER_PUBLIC_URL="$CONTEXT_STORE_PUBLIC_URL" \
    SEMANTIC_SEARCH_ENABLED=false \
    CORS_ORIGINS="*" \
    uv run python -m src.main
fi
