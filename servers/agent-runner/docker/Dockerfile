# Agent Runner Multi-Stage Dockerfile
#
# Combines base + all executors in one file for convenient docker-compose usage.
# Use --target to build specific executor images.
#
# NOTE: For standalone builds or external extensibility, use the separate
# Dockerfiles in base/, claude-code/, procedural/ directories.
#
# Build examples:
#   docker build --target base -t agent-runner-base:latest -f servers/agent-runner/docker/Dockerfile .
#   docker build --target claude-code -t agent-runner-claude-code:latest -f servers/agent-runner/docker/Dockerfile .
#   docker build --target procedural -t agent-runner-procedural:latest -f servers/agent-runner/docker/Dockerfile .

# ==============================================================================
# STAGE: base
# ==============================================================================
FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN pip install uv

# Create non-root user (some coding agents refuse to run in YOLO mode as root)
RUN useradd -m -s /bin/bash agent

# Create app directory structure
WORKDIR /app

# Copy agent-runner main script
COPY servers/agent-runner/agent-runner /app/servers/agent-runner/agent-runner

# Copy agent-runner library
COPY servers/agent-runner/lib/ /app/servers/agent-runner/lib/

# Create profiles directory (executor stages add their compatible profiles)
RUN mkdir -p /app/servers/agent-runner/profiles

# Copy entrypoint script
COPY servers/agent-runner/docker/base/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create workspace directory (mount point for projects)
RUN mkdir -p /workspace

# Set ownership for non-root user
RUN chown -R agent:agent /app /workspace

# Environment defaults
ENV AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765
ENV PROJECT_DIR=/workspace
ENV PROFILE=""

ENTRYPOINT ["/entrypoint.sh"]

# ==============================================================================
# STAGE: claude-code
# ==============================================================================
FROM base AS claude-code

# Switch back to root for apt-get
USER root

# Install Node.js (required for Claude Code)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Switch to non-root user for Claude Code installation
USER agent

# Install Claude Code via official installer (installs to ~/.local/bin)
RUN curl -fsSL https://claude.ai/install.sh | bash

# Add Claude to PATH
ENV PATH="/home/agent/.local/bin:${PATH}"

# Copy onboarding bypass config (workaround for bug #8938)
# Claude checks hasCompletedOnboarding before accepting OAuth token
COPY --chown=agent:agent servers/agent-runner/docker/claude-code/claude-config/.claude.json /home/agent/.claude.json

# Copy Claude Code executor
COPY --chown=agent:agent servers/agent-runner/executors/claude-code/ /app/servers/agent-runner/executors/claude-code/

# Copy compatible profiles (only profiles that use claude-code executor)
COPY --chown=agent:agent servers/agent-runner/docker/claude-code/profiles/ /app/servers/agent-runner/profiles/

# Default to best profile
ENV PROFILE=best

# Note: CLAUDE_CODE_OAUTH_TOKEN must be provided at runtime
# Do NOT set ANTHROPIC_API_KEY - it conflicts with OAuth token

# ==============================================================================
# STAGE: procedural
# ==============================================================================
FROM base AS procedural

# Copy procedural executor
COPY --chown=agent:agent servers/agent-runner/executors/procedural-executor/ /app/servers/agent-runner/executors/procedural-executor/

# Copy compatible profiles (only profiles that use procedural executor)
COPY --chown=agent:agent servers/agent-runner/docker/procedural/profiles/ /app/servers/agent-runner/profiles/

# Default to echo profile (example procedural agent)
ENV PROFILE=echo

# Run as non-root user
USER agent
