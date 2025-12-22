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
ARG VITE_AGENT_ORCHESTRATOR_API_KEY
ARG VITE_AGENT_BLUEPRINT
ARG VITE_APP_TITLE
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_AGENT_ORCHESTRATOR_API_KEY=$VITE_AGENT_ORCHESTRATOR_API_KEY
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
