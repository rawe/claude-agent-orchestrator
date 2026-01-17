# Agent Runner Base Image
#
# Base image for the Agent Runner with Python 3.12, uv, and core dependencies.
# Executor-specific images extend this base.
#
# Build: docker build -t agent-runner-base:latest -f servers/agent-runner/docker/base/Dockerfile .

FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN pip install uv

# Create app directory structure
WORKDIR /app

# Copy agent-runner main script
COPY servers/agent-runner/agent-runner /app/servers/agent-runner/agent-runner

# Copy agent-runner library
COPY servers/agent-runner/lib/ /app/servers/agent-runner/lib/

# Create profiles directory (executor images add their compatible profiles)
RUN mkdir -p /app/servers/agent-runner/profiles

# Copy entrypoint script
COPY servers/agent-runner/docker/base/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create workspace directory (mount point for projects)
RUN mkdir -p /workspace

# Environment defaults
ENV AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765
ENV PROJECT_DIR=/workspace
ENV PROFILE=""

# Expose no ports by default (runner is a client)
# MCP server port can be exposed if needed via docker-compose

ENTRYPOINT ["/entrypoint.sh"]
