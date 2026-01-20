#!/bin/bash
set -e

echo "Starting Context Store services..."

# Always start the Context Store server
echo "Starting Context Store API on port ${DOCUMENT_SERVER_PORT:-8766}..."
python -m src.main &
CONTEXT_STORE_PID=$!

# Optionally start the MCP server
if [ "${MCP_ENABLED:-false}" = "true" ]; then
    echo "MCP server enabled, starting on port ${MCP_HTTP_PORT:-9501}..."

    # Configure MCP to connect to local Context Store
    export CONTEXT_STORE_HOST=localhost
    export CONTEXT_STORE_PORT=${DOCUMENT_SERVER_PORT:-8766}
    export CONTEXT_STORE_SCHEME=http

    # Wait for Context Store to be ready
    echo "Waiting for Context Store to be ready..."
    for i in {1..30}; do
        if python -c "import urllib.request; urllib.request.urlopen('http://localhost:${DOCUMENT_SERVER_PORT:-8766}/health')" 2>/dev/null; then
            echo "Context Store is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "Warning: Context Store health check timed out, starting MCP anyway..."
        fi
        sleep 1
    done

    # Start MCP server in HTTP mode
    cd /app/mcp-server
    python context-store-mcp.py --http-mode --host "${MCP_HTTP_HOST:-0.0.0.0}" --port "${MCP_HTTP_PORT:-9501}" &
    MCP_PID=$!
    echo "MCP server started (PID: $MCP_PID)"
    echo "MCP endpoint: http://${MCP_HTTP_HOST:-0.0.0.0}:${MCP_HTTP_PORT:-9501}/mcp"
    cd /app
else
    echo "MCP server disabled (set MCP_ENABLED=true to enable)"
fi

# Handle shutdown gracefully
shutdown() {
    echo "Shutting down..."
    if [ -n "$MCP_PID" ]; then
        kill $MCP_PID 2>/dev/null || true
    fi
    kill $CONTEXT_STORE_PID 2>/dev/null || true
    exit 0
}

trap shutdown SIGTERM SIGINT

# Wait for Context Store process (main process)
wait $CONTEXT_STORE_PID
