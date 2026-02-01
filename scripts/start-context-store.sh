#!/bin/bash
# =============================================================================
# Start Context Store Server - Development Mode
# =============================================================================
# URL: http://localhost:8766
# Data: .agent-orchestrator/context-store-data/
#
# Options:
#   --semantic    Enable semantic search (requires Elasticsearch + Ollama)
#
# Prerequisites for semantic search:
#   - Elasticsearch running on localhost:9200 (see docker-compose.yml)
#   - Ollama running on localhost:11434 with nomic-embed-text model
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
SEMANTIC_SEARCH_ENABLED="false"
for arg in "$@"; do
    case $arg in
        --semantic)
            SEMANTIC_SEARCH_ENABLED="true"
            shift
            ;;
    esac
done

# Configuration
CONTEXT_STORE_HOST="0.0.0.0"
CONTEXT_STORE_PORT="8766"
DATA_DIR="$PROJECT_ROOT/.agent-orchestrator/context-store-data"

# Semantic search configuration
ELASTICSEARCH_URL="http://localhost:9200"
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_EMBEDDING_MODEL="nomic-embed-text"
# NOTE: Using separate index for local dev mode to avoid conflicts with Docker Compose.
# Docker Compose uses "context-store-vectors" with its own document storage volume,
# while local dev uses .agent-orchestrator/context-store-data/ for files.
ELASTICSEARCH_INDEX="context-store-vectors-dev"

mkdir -p "$DATA_DIR/files"

if [ "$SEMANTIC_SEARCH_ENABLED" = "true" ]; then
    echo "Starting Context Store with semantic search enabled..."
    echo "  Elasticsearch: $ELASTICSEARCH_URL"
    echo "  Ollama: $OLLAMA_BASE_URL (model: $OLLAMA_EMBEDDING_MODEL)"
else
    echo "Starting Context Store (semantic search disabled)"
fi

cd "$PROJECT_ROOT/servers/context-store"

# Build uv run command
# --extra semantic: Installs optional dependency group "semantic" from pyproject.toml
# which includes langchain-ollama and langchain-elasticsearch packages required
# for vector embeddings and semantic search functionality.
if [ "$SEMANTIC_SEARCH_ENABLED" = "true" ]; then
    UV_CMD="uv run --extra semantic"
else
    UV_CMD="uv run"
fi

DOCUMENT_SERVER_HOST="$CONTEXT_STORE_HOST" \
DOCUMENT_SERVER_PORT="$CONTEXT_STORE_PORT" \
DOCUMENT_SERVER_STORAGE="$DATA_DIR/files" \
DOCUMENT_SERVER_DB="$DATA_DIR/documents.db" \
DOCUMENT_SERVER_PUBLIC_URL="http://localhost:$CONTEXT_STORE_PORT" \
SEMANTIC_SEARCH_ENABLED="$SEMANTIC_SEARCH_ENABLED" \
ELASTICSEARCH_URL="$ELASTICSEARCH_URL" \
OLLAMA_BASE_URL="$OLLAMA_BASE_URL" \
OLLAMA_EMBEDDING_MODEL="$OLLAMA_EMBEDDING_MODEL" \
ELASTICSEARCH_INDEX="$ELASTICSEARCH_INDEX" \
CORS_ORIGINS="*" \
$UV_CMD python -m src.main
