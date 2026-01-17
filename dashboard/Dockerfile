# Build arguments for versioning and labels
ARG VERSION=dev
ARG COMPONENT_VERSION=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
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
