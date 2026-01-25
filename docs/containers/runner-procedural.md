# AOF Runner (Procedural)

The Procedural Runner is an agent execution engine that polls the Coordinator for work and executes agent runs using CLI commands and scripts.

## Image

```
ghcr.io/rawe/aof-runner-procedural:<version>
```

## Quick Start

```bash
docker run -d \
  --name aof-runner-procedural \
  -e AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765 \
  -v $(pwd)/workspace:/workspace \
  ghcr.io/rawe/aof-runner-procedural:<version>
```

## Overview

The procedural executor runs predefined CLI commands or scripts based on agent definitions. Unlike the Claude Code executor which uses AI for dynamic task execution, the procedural executor:

- Executes commands/scripts defined in agent blueprints
- Passes parameters as `--key value` CLI arguments
- Returns structured JSON output
- Supports script-based agents with centralized script management

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_ORCHESTRATOR_API_URL` | No | `http://host.docker.internal:8765` | Coordinator API URL |
| `PROJECT_DIR` | No | `/workspace` | Working directory for agent execution |
| `PROFILE` | No | `echo` | Executor profile name |
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

## Ports

The runner does not expose any ports by default. It operates as a polling client to the Coordinator.

## Volumes

| Path | Description |
|------|-------------|
| `/workspace` | Working directory for agent execution (mount your project here) |

## Profiles

The runner supports different execution profiles:

| Profile | Description |
|---------|-------------|
| `echo` | Example CLI command executor (default) |
| `test-procedural` | Test profile for procedural executor |

Set the profile via environment variable:

```bash
-e PROFILE=echo
```

## Runner Tags

Tags allow matching specific runners to specific agent blueprints. Use comma-separated values:

```bash
-e RUNNER_TAGS=procedural,cli
```

Agent blueprints can then specify required tags to route runs to appropriate runners.

## Example: Development Setup

```bash
docker run -d \
  --name aof-runner-procedural \
  -e AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765 \
  -e PROFILE=echo \
  -e VERBOSE=true \
  -v $(pwd)/workspace:/workspace \
  ghcr.io/rawe/aof-runner-procedural:<version>
```

## Example: Production Setup

```bash
docker run -d \
  --name aof-runner-procedural \
  --restart unless-stopped \
  -e AGENT_ORCHESTRATOR_API_URL=http://coordinator.internal:8765 \
  -e PROFILE=echo \
  -e RUNNER_TAGS=production,procedural \
  -v /var/lib/aof/workspace:/workspace \
  ghcr.io/rawe/aof-runner-procedural:<version>
```

## Docker Compose

```yaml
services:
  runner-procedural:
    image: ghcr.io/rawe/aof-runner-procedural:<version>
    environment:
      AGENT_ORCHESTRATOR_API_URL: http://coordinator:8765
      PROFILE: echo
      VERBOSE: "false"
    volumes:
      - ./workspace:/workspace
    depends_on:
      - coordinator
    restart: unless-stopped
```

### With Shared Workspace (Claude Code + Procedural)

When running both runners, share the workspace for file collaboration:

```yaml
services:
  runner:
    image: ghcr.io/rawe/aof-runner-claude-code:<version>
    environment:
      AGENT_ORCHESTRATOR_API_URL: http://coordinator:8765
      CLAUDE_CODE_OAUTH_TOKEN: ${CLAUDE_CODE_OAUTH_TOKEN}
    volumes:
      - ./workspace:/workspace
    depends_on:
      - coordinator

  runner-procedural:
    image: ghcr.io/rawe/aof-runner-procedural:<version>
    environment:
      AGENT_ORCHESTRATOR_API_URL: http://coordinator:8765
      PROFILE: echo
    volumes:
      - ./workspace:/workspace
    depends_on:
      - coordinator
```

### With Authentication Enabled

```yaml
services:
  runner-procedural:
    image: ghcr.io/rawe/aof-runner-procedural:<version>
    environment:
      AGENT_ORCHESTRATOR_API_URL: http://coordinator:8765
      PROFILE: echo
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

## Agent Definition

Procedural agents are defined with a `command` or `script` field:

### Command-based Agent

```json
{
  "name": "echo",
  "description": "Simple echo agent",
  "command": "scripts/echo/echo",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "message": {
        "type": "string",
        "description": "Message to echo"
      }
    },
    "required": ["message"]
  }
}
```

### Script-based Agent

```json
{
  "name": "my-script",
  "description": "Script-based agent",
  "script": "my-script",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "input": {
        "type": "string"
      }
    }
  }
}
```

Scripts are fetched from `{PROJECT_DIR}/scripts/{script_name}/`.

## Security Considerations

- The runner executes code as the `agent` user (non-root)
- Mount workspace directories with appropriate permissions
- Consider network isolation between runner and external services
- Validate agent command definitions to prevent command injection

## Troubleshooting

### Runner not picking up runs

1. Check the Coordinator URL is accessible from the container
2. Check runner registration: `curl http://coordinator:8765/runners`
3. Enable verbose logging: `-e VERBOSE=true`
4. Verify agent profile matches: procedural agents need `type: procedural` in their profile

### Command not found

1. Verify the script/command exists in the workspace
2. Check file permissions (must be executable)
3. Ensure paths are relative to the executor directory

### Connection refused to Coordinator

When running on Docker Desktop (Mac/Windows), use `host.docker.internal`:

```bash
-e AGENT_ORCHESTRATOR_API_URL=http://host.docker.internal:8765
```

When running in Docker Compose, use the service name:

```bash
-e AGENT_ORCHESTRATOR_API_URL=http://coordinator:8765
```
