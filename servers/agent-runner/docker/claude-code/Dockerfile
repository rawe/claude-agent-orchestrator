# Agent Runner with Claude Code Executor
#
# Extends agent-runner-base with Claude Code.
# Uses OAuth token authentication (CLAUDE_CODE_OAUTH_TOKEN).
#
# Build:
#   docker build -t agent-runner-base:latest -f servers/agent-runner/docker/base/Dockerfile .
#   docker build -t agent-runner-claude-code:latest \
#     --build-arg BASE_IMAGE=agent-runner-base:latest \
#     -f servers/agent-runner/docker/claude-code/Dockerfile .

ARG BASE_IMAGE=agent-runner-base:latest
FROM ${BASE_IMAGE}

# Install Node.js (required for Claude Code) - must run as root
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
