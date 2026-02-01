# =============================================================================
# Dashboard Docker Build
# =============================================================================
# This is a multi-stage build that produces a minimal nginx image serving
# only the compiled static files.
#
# MONOREPO BUILD CONTEXT
# ----------------------
# The dashboard depends on workspace packages (@rawe/agent-orchestrator-sdk,
# @rawe/context-store-sdk) that are part of this monorepo. To resolve these
# dependencies during Docker build, we must:
#   1. Use the repository root as the Docker build context (not apps/dashboard/)
#   2. Copy the root package.json and package-lock.json (defines workspaces)
#   3. Copy the packages/ directory (contains the SDK source code)
#   4. Copy the dashboard source (apps/dashboard/)
#   5. Run npm ci from the root to install all workspace dependencies
#
# This ensures the Docker build uses the exact same SDK code as local development,
# without requiring the packages to be published to npm first.
#
# Build command (from repo root):
#   docker build -f apps/dashboard/Dockerfile .
# =============================================================================

# Build arguments for versioning and labels
ARG VERSION=dev
ARG COMPONENT_VERSION=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

FROM node:22-alpine AS build
WORKDIR /app

# Copy monorepo structure required for workspace resolution
COPY package.json package-lock.json ./
COPY packages/ ./packages/
COPY apps/dashboard/ ./apps/dashboard/

# Install all workspace dependencies from root
RUN npm ci

# Build SDK packages first - they must be compiled before the dashboard
# because the dashboard imports from their dist/ directories.
# Order matters: SDKs first, then dashboard (which depends on them).
RUN npm run build -w @rawe/agent-orchestrator-sdk -w @rawe/context-store-sdk

# Vite env vars must be available at build time
ARG VITE_AGENT_ORCHESTRATOR_API_URL
ARG VITE_DOCUMENT_SERVER_URL
# Auth0 OIDC (optional - enables login UI)
ARG VITE_AUTH0_DOMAIN
ARG VITE_AUTH0_CLIENT_ID
ARG VITE_AUTH0_AUDIENCE
ENV VITE_AGENT_ORCHESTRATOR_API_URL=$VITE_AGENT_ORCHESTRATOR_API_URL
ENV VITE_DOCUMENT_SERVER_URL=$VITE_DOCUMENT_SERVER_URL
ENV VITE_AUTH0_DOMAIN=$VITE_AUTH0_DOMAIN
ENV VITE_AUTH0_CLIENT_ID=$VITE_AUTH0_CLIENT_ID
ENV VITE_AUTH0_AUDIENCE=$VITE_AUTH0_AUDIENCE

# Build the dashboard
WORKDIR /app/apps/dashboard
RUN npm run build

# =============================================================================
# Production image - nginx serving static files only
# =============================================================================
FROM nginx:alpine

# Re-declare ARGs after FROM (they don't persist across stages)
ARG VERSION
ARG COMPONENT_VERSION
ARG GIT_COMMIT
ARG BUILD_DATE

# OCI Image Labels (https://github.com/opencontainers/image-spec/blob/main/annotations.md)
LABEL org.opencontainers.image.title="AOF Dashboard" \
      org.opencontainers.image.description="Agent Orchestration Framework - Web UI for agent management, sessions, and monitoring" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.source="https://github.com/rawe/claude-agent-orchestrator" \
      org.opencontainers.image.vendor="rawe" \
      org.opencontainers.image.licenses="MIT" \
      aof.component="dashboard" \
      aof.component.version="${COMPONENT_VERSION}"

# Copy only the built static files from the build stage
COPY --from=build /app/apps/dashboard/dist /usr/share/nginx/html
COPY apps/dashboard/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
