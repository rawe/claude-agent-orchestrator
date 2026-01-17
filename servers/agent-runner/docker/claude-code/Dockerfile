# Agent Runner with Claude Code CLI Executor
#
# Extends agent-runner-base with Claude Code CLI.
# Uses OAuth token authentication (CLAUDE_CODE_OAUTH_TOKEN).
#
# Build:
#   docker build -t agent-runner-base:latest -f servers/agent-runner/docker/base/Dockerfile .
#   docker build -t agent-runner-claude-code:latest \
#     --build-arg BASE_IMAGE=agent-runner-base:latest \
#     -f servers/agent-runner/docker/claude-code/Dockerfile .

ARG BASE_IMAGE=agent-runner-base:latest
FROM ${BASE_IMAGE}

# Install Node.js (required for Claude Code CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI via official installer
RUN curl -fsSL https://claude.ai/install.sh | bash

# Add Claude to PATH (installs to ~/.local/bin)
ENV PATH="/root/.local/bin:${PATH}"

# Copy onboarding bypass config (workaround for bug #8938)
# Claude checks hasCompletedOnboarding before accepting OAuth token
COPY servers/agent-runner/docker/claude-code/claude-config/.claude.json /root/.claude.json

# Copy Claude Code executor
COPY servers/agent-runner/executors/claude-code/ /app/servers/agent-runner/executors/claude-code/

# Copy compatible profiles (only profiles that use claude-code executor)
COPY servers/agent-runner/docker/claude-code/profiles/ /app/servers/agent-runner/profiles/

# Default to best profile
ENV PROFILE=best

# Note: CLAUDE_CODE_OAUTH_TOKEN must be provided at runtime
# Do NOT set ANTHROPIC_API_KEY - it conflicts with OAuth token
