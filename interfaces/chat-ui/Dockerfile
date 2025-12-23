# Multi-stage build for Chat UI
# Stage 1: Build the React application
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code and environment file
COPY . .

# Vite env vars must be available at build time
ARG VITE_API_URL
# DEPRECATED: Use Auth0 OIDC instead. Will be removed in future version.
ARG VITE_AGENT_ORCHESTRATOR_API_KEY
# Auth0 OIDC
ARG VITE_AUTH0_DOMAIN
ARG VITE_AUTH0_CLIENT_ID
ARG VITE_AUTH0_AUDIENCE
# App configuration
ARG VITE_AGENT_BLUEPRINT
ARG VITE_APP_TITLE
ENV VITE_API_URL=$VITE_API_URL
# DEPRECATED: Use Auth0 OIDC instead. Will be removed in future version.
ENV VITE_AGENT_ORCHESTRATOR_API_KEY=$VITE_AGENT_ORCHESTRATOR_API_KEY
# Auth0 OIDC
ENV VITE_AUTH0_DOMAIN=$VITE_AUTH0_DOMAIN
ENV VITE_AUTH0_CLIENT_ID=$VITE_AUTH0_CLIENT_ID
ENV VITE_AUTH0_AUDIENCE=$VITE_AUTH0_AUDIENCE
# App configuration
ENV VITE_AGENT_BLUEPRINT=$VITE_AGENT_BLUEPRINT
ENV VITE_APP_TITLE=$VITE_APP_TITLE

# Build the application
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine AS production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 3010

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3010/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
