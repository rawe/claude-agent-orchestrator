FROM node:24-alpine3.21

# Install dependencies (from GitLab CI example)
RUN apk update && \
    apk add --no-cache git curl bash

# Install Claude Code via official installer
RUN curl -fsSL https://claude.ai/install.sh | bash

# Add Claude to PATH (installs to ~/.local/bin)
ENV PATH="/root/.local/bin:${PATH}"

# Skip onboarding when using CLAUDE_CODE_OAUTH_TOKEN (workaround for bug #8938)
# Copied into image so Claude can modify it at runtime
COPY claude-config/.claude.json /root/.claude.json

WORKDIR /workspace
