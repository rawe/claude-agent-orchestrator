#!/bin/bash
# =============================================================================
# Start Context Store Server - Development Mode
# =============================================================================
# URL: http://localhost:8766
# Data: .agent-orchestrator/context-store-data/
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
CONTEXT_STORE_HOST="0.0.0.0"
CONTEXT_STORE_PORT="8766"
DATA_DIR="$PROJECT_ROOT/.agent-orchestrator/context-store-data"

mkdir -p "$DATA_DIR/files"

cd "$PROJECT_ROOT/servers/context-store"

DOCUMENT_SERVER_HOST="$CONTEXT_STORE_HOST" \
DOCUMENT_SERVER_PORT="$CONTEXT_STORE_PORT" \
DOCUMENT_SERVER_STORAGE="$DATA_DIR/files" \
DOCUMENT_SERVER_DB="$DATA_DIR/documents.db" \
DOCUMENT_SERVER_PUBLIC_URL="http://localhost:$CONTEXT_STORE_PORT" \
SEMANTIC_SEARCH_ENABLED=false \
CORS_ORIGINS="*" \
uv run python -m src.main
