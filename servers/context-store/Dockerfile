FROM python:3.11-slim

# Build arguments for versioning and labels
ARG VERSION=dev
ARG COMPONENT_VERSION=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

# OCI Image Labels (https://github.com/opencontainers/image-spec/blob/main/annotations.md)
LABEL org.opencontainers.image.title="AOF Context Store" \
      org.opencontainers.image.description="Agent Orchestration Framework - Document management and synchronization for agent sessions" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.source="https://github.com/rawe/claude-agent-orchestrator" \
      org.opencontainers.image.vendor="rawe" \
      org.opencontainers.image.licenses="MIT" \
      aof.component="context-store" \
      aof.component.version="${COMPONENT_VERSION}"

# Install UV package manager
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy Context Store dependency files and install
COPY servers/context-store/pyproject.toml ./
RUN uv pip install --system -e ".[semantic]"

# Install MCP server dependencies
RUN uv pip install --system "mcp>=1.7.0" "fastmcp>=2.0.0" "pydantic>=2.0.0" "httpx>=0.27.0"

# Copy Context Store application code
COPY servers/context-store/src ./src

# Copy MCP server code
COPY mcps/context-store/context-store-mcp.py ./mcp-server/
COPY mcps/context-store/lib ./mcp-server/lib

# Copy entrypoint script
COPY servers/context-store/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose ports:
# - 8766: Context Store REST API
# - 9501: MCP HTTP server (optional, enabled via MCP_ENABLED=true)
EXPOSE 8766 9501

# Environment variables
ENV DOCUMENT_SERVER_HOST=0.0.0.0 \
    DOCUMENT_SERVER_PORT=8766 \
    MCP_ENABLED=false \
    MCP_HTTP_HOST=0.0.0.0 \
    MCP_HTTP_PORT=9501

# Health check (Context Store API)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8766/health')" || exit 1

# Run via entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]
