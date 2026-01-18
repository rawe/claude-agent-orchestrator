# AOF Runner (Claude Code)

The Runner is the agent execution engine that polls the Coordinator for work and executes agent runs using Claude Code as the executor.

## Image

```
ghcr.io/rawe/aof-runner-claude-code:<version>
```

## Quick Start

```bash
docker run -d \
  --name aof-runner \
  -e AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765 \
  -e CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token \
  -v $(pwd)/workspace:/workspace \
  ghcr.io/rawe/aof-runner-claude-code:<version>
```

## Prerequisites

**Claude Code OAuth Token:** Required for authentication with Claude Code.

Generate a token using the Claude Code CLI:

```bash
claude auth token
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | **Yes** | - | OAuth token for Claude Code authentication |
| `AGENT_ORCHESTRATOR_API_URL` | No | `http://host.docker.internal:8765` | Coordinator API URL |
| `PROJECT_DIR` | No | `/workspace` | Working directory for agent execution |
| `PROFILE` | No | `best` | Executor profile name |
| `RUNNER_TAGS` | No | - | Comma-separated tags for runner matching |
| `POLL_TIMEOUT` | No | `30` | Polling timeout in seconds |
| `HEARTBEAT_INTERVAL` | No | `60` | Heartbeat interval in seconds |
| `VERBOSE` | No | `false` | Enable verbose logging |

### Auth0 M2M Authentication

When the Coordinator has authentication enabled (`AUTH_ENABLED=true`), the runner needs M2M credentials:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH0_DOMAIN` | When auth enabled | - | Auth0 tenant domain (e.g., `your-org.auth0.com`) |
| `AUTH0_AUDIENCE` | When auth enabled | - | API identifier (must match Coordinator) |
| `AUTH0_RUNNER_CLIENT_ID` | When auth enabled | - | M2M application client ID |
| `AUTH0_RUNNER_CLIENT_SECRET` | When auth enabled | - | M2M application client secret |

See [Auth0 Setup Guide](../setup/auth0-setup.md) for configuration details.

**Important:** Do NOT set `ANTHROPIC_API_KEY` - it conflicts with the OAuth token.

## Ports

The runner does not expose any ports by default. It operates as a polling client to the Coordinator.

Optional: Expose the embedded MCP server for Claude Desktop integration:

| Port | Protocol | Description |
|------|----------|-------------|
| 9500 | HTTP | Embedded MCP server (optional) |

## Volumes

| Path | Description |
|------|-------------|
| `/workspace` | Working directory for agent execution (mount your project here) |

## Profiles

The runner supports different execution profiles that configure Claude Code behavior:

| Profile | Description |
|---------|-------------|
| `best` | Full access with Opus model (default) |
| `quick` | Full access with Sonnet model |
| `restricted-best` | Restricted permissions with Opus model |
| `restricted-quick` | Restricted permissions with Sonnet model |

Set the profile via environment variable:

```bash
-e PROFILE=quick
```

## Runner Tags

Tags allow matching specific runners to specific agent blueprints. Use comma-separated values:

```bash
-e RUNNER_TAGS=gpu,high-memory
```

Agent blueprints can then specify required tags to route runs to appropriate runners.

## Example: Development Setup

```bash
docker run -d \
  --name aof-runner \
  -e AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765 \
  -e CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN} \
  -e PROFILE=best \
  -e VERBOSE=true \
  -v $(pwd)/workspace:/workspace \
  ghcr.io/rawe/aof-runner-claude-code:<version>
```

## Example: Production Setup

```bash
docker run -d \
  --name aof-runner \
  --restart unless-stopped \
  -e AGENT_ORCHESTRATOR_API_URL=http://coordinator.internal:8765 \
  -e CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN} \
  -e PROFILE=best \
  -e RUNNER_TAGS=production,region-us \
  -v /var/lib/aof/workspace:/workspace \
  ghcr.io/rawe/aof-runner-claude-code:<version>
```

## Example: With MCP Server Exposed

For Claude Desktop integration, expose the embedded MCP server:

```bash
docker run -d \
  --name aof-runner \
  -p 9500:9500 \
  -e AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765 \
  -e CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN} \
  -v $(pwd)/workspace:/workspace \
  ghcr.io/rawe/aof-runner-claude-code:<version> \
  --mcp-port 9500
```

## Docker Compose

```yaml
services:
  runner:
    image: ghcr.io/rawe/aof-runner-claude-code:<version>
    environment:
      AGENT_ORCHESTRATOR_API_URL: http://coordinator:8765
      CLAUDE_CODE_OAUTH_TOKEN: ${CLAUDE_CODE_OAUTH_TOKEN}
      PROFILE: best
      VERBOSE: "false"
    volumes:
      - ./workspace:/workspace
    depends_on:
      - coordinator
    restart: unless-stopped
```

### With Authentication Enabled

```yaml
services:
  runner:
    image: ghcr.io/rawe/aof-runner-claude-code:<version>
    environment:
      AGENT_ORCHESTRATOR_API_URL: http://coordinator:8765
      CLAUDE_CODE_OAUTH_TOKEN: ${CLAUDE_CODE_OAUTH_TOKEN}
      PROFILE: best
      VERBOSE: "false"
      # Auth0 M2M credentials (required when coordinator has AUTH_ENABLED=true)
      AUTH0_DOMAIN: ${AUTH0_DOMAIN}
      AUTH0_AUDIENCE: ${AUTH0_AUDIENCE}
      AUTH0_RUNNER_CLIENT_ID: ${AUTH0_RUNNER_CLIENT_ID}
      AUTH0_RUNNER_CLIENT_SECRET: ${AUTH0_RUNNER_CLIENT_SECRET}
    volumes:
      - ./workspace:/workspace
    depends_on:
      - coordinator
    restart: unless-stopped
```

## Security Considerations

- The runner executes code as the `agent` user (non-root)
- Mount workspace directories with appropriate permissions
- Store the OAuth token securely (use Docker secrets or environment files)
- Consider network isolation between runner and external services

## Troubleshooting

### Runner not picking up runs

1. Check the Coordinator URL is accessible from the container
2. Verify the OAuth token is valid: `claude auth status`
3. Check runner registration: `curl http://coordinator:8765/runners`
4. Enable verbose logging: `-e VERBOSE=true`

### OAuth token errors

1. Regenerate the token: `claude auth token`
2. Ensure no `ANTHROPIC_API_KEY` is set (conflicts with OAuth)
3. Check token hasn't expired

### Connection refused to Coordinator

When running on Docker Desktop (Mac/Windows), use `host.docker.internal`:

```bash
-e AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765
```

When running in Docker Compose, use the service name:

```bash
-e AGENT_ORCHESTRATOR_API_URL=http://coordinator:8765
```
