# Build arguments for versioning and labels
ARG VERSION=dev
ARG COMPONENT_VERSION=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

# SDK versions for production builds
# In local development, the dashboard uses npm workspace references ("*") to resolve
# @rawe packages from the monorepo. In Docker builds, we replace these with published
# npm package versions since the workspace context is not available.
ARG AGENT_ORCHESTRATOR_SDK_VERSION=0.1.0
ARG CONTEXT_STORE_SDK_VERSION=0.1.0

FROM node:18-alpine AS build

# Re-declare SDK version ARGs (ARGs before FROM are not available in build stages)
ARG AGENT_ORCHESTRATOR_SDK_VERSION
ARG CONTEXT_STORE_SDK_VERSION

WORKDIR /app
COPY package.json ./

# Replace workspace references with published npm package versions
RUN sed -i "s|\"@rawe/agent-orchestrator-sdk\": \"\*\"|\"@rawe/agent-orchestrator-sdk\": \"^${AGENT_ORCHESTRATOR_SDK_VERSION}\"|g" package.json && \
    sed -i "s|\"@rawe/context-store-sdk\": \"\*\"|\"@rawe/context-store-sdk\": \"^${CONTEXT_STORE_SDK_VERSION}\"|g" package.json

RUN npm install
COPY . .

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

RUN npm run build

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

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
