# AOF Dashboard

The Dashboard is the web-based user interface for managing agents, sessions, and monitoring runs in the Agent Orchestration Framework.

## Image

```
ghcr.io/rawe/aof-dashboard:<version>
```

## Quick Start

```bash
docker run -d \
  --name aof-dashboard \
  -p 3000:80 \
  ghcr.io/rawe/aof-dashboard:latest
```

## Build Arguments

The Dashboard is a static React application. Configuration is baked in at build time via build arguments.

When building custom images, use these build arguments:

| Build Argument | Default | Description |
|----------------|---------|-------------|
| `VITE_AGENT_ORCHESTRATOR_API_URL` | - | Coordinator API URL |
| `VITE_DOCUMENT_SERVER_URL` | - | Context Store URL (optional) |
| `VITE_AUTH0_DOMAIN` | - | Auth0 domain for OIDC (optional) |
| `VITE_AUTH0_CLIENT_ID` | - | Auth0 client ID (optional) |
| `VITE_AUTH0_AUDIENCE` | - | Auth0 API audience (optional) |

### Building a Custom Image

```bash
docker build \
  --build-arg VITE_AGENT_ORCHESTRATOR_API_URL=https://api.example.com \
  --build-arg VITE_AUTH0_DOMAIN=your-tenant.auth0.com \
  --build-arg VITE_AUTH0_CLIENT_ID=your-client-id \
  --build-arg VITE_AUTH0_AUDIENCE=https://your-api \
  -t my-aof-dashboard:latest \
  dashboard/
```

## Pre-built Image Configuration

The pre-built images from ghcr.io use default/empty configuration values. For production use, you have two options:

1. **Build a custom image** with your configuration baked in (recommended for production)
2. **Use nginx config override** to rewrite API endpoints at runtime

## Ports

| Port | Protocol | Description |
|------|----------|-------------|
| 80 | HTTP | Web UI served by nginx |

## Volumes

The Dashboard is a static application and doesn't require persistent storage.

Optional: Mount a custom nginx configuration:

| Path | Description |
|------|-------------|
| `/etc/nginx/conf.d/default.conf` | Custom nginx configuration |

## Example: Development Setup

For local development, the default image works with localhost:

```bash
docker run -d \
  --name aof-dashboard \
  -p 3000:80 \
  ghcr.io/rawe/aof-dashboard:latest
```

Access the dashboard at http://localhost:3000

The dashboard will attempt to connect to `http://localhost:8765` for the Coordinator API.

## Example: Production Setup

For production, build a custom image with your configuration:

```bash
# Build custom image
docker build \
  --build-arg VITE_AGENT_ORCHESTRATOR_API_URL=https://api.aof.example.com \
  --build-arg VITE_AUTH0_DOMAIN=example.auth0.com \
  --build-arg VITE_AUTH0_CLIENT_ID=abc123 \
  --build-arg VITE_AUTH0_AUDIENCE=https://api.aof.example.com \
  -t my-aof-dashboard:1.0.0 \
  dashboard/

# Run production image
docker run -d \
  --name aof-dashboard \
  -p 80:80 \
  my-aof-dashboard:1.0.0
```

## Docker Compose

### Development (No Authentication)

```yaml
services:
  dashboard:
    image: ghcr.io/rawe/aof-dashboard:1.0.0
    ports:
      - "3000:80"
    depends_on:
      - coordinator
```

### Production (With Custom Build)

```yaml
services:
  dashboard:
    build:
      context: ./dashboard
      args:
        VITE_AGENT_ORCHESTRATOR_API_URL: https://api.aof.example.com
        VITE_AUTH0_DOMAIN: example.auth0.com
        VITE_AUTH0_CLIENT_ID: ${AUTH0_CLIENT_ID}
        VITE_AUTH0_AUDIENCE: https://api.aof.example.com
    ports:
      - "80:80"
    depends_on:
      - coordinator
```

## Authentication

The Dashboard supports optional Auth0 authentication. When Auth0 is configured:

- Users must log in before accessing the dashboard
- API requests include the Auth0 access token
- The Coordinator must also be configured with matching Auth0 settings

### Disabling Authentication

To run without authentication, simply omit the Auth0 build arguments. The dashboard will function without a login screen.

## Nginx Configuration

The default nginx configuration proxies API requests appropriately. If you need to customize it, create a custom `nginx.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Optional: Proxy API requests
    location /api/ {
        proxy_pass http://coordinator:8765/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Mount it when running:

```bash
docker run -d \
  -p 3000:80 \
  -v $(pwd)/nginx.conf:/etc/nginx/conf.d/default.conf:ro \
  ghcr.io/rawe/aof-dashboard:latest
```

## Health Check

The container serves static files. Check health by requesting the root path:

```bash
curl -I http://localhost:3000/
```

## Features

- **Session Management:** Create, view, and manage agent sessions
- **Real-time Monitoring:** Watch agent runs in real-time via SSE
- **Agent Blueprints:** Browse and edit agent configurations
- **Run History:** View past runs and their outputs
- **Document Management:** Upload and manage documents (requires Context Store)
