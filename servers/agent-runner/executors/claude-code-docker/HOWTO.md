# Claude Code in Docker

Run Claude Code CLI inside a Docker container.

## Prerequisites

- Docker with Compose
- Claude Code installed locally with active subscription (Pro/Max)
- Long-lived OAuth token from `claude setup-token`

## Quick Start

```bash
# 1. Generate OAuth token (on host with logged-in Claude Code)
claude setup-token
# Copy the token (sk-ant-...)

# 2. Setup
cp .env.template .env
# Edit .env: paste CLAUDE_CODE_OAUTH_TOKEN

# 3. Build and run
docker compose up -d --build

# 4. Use Claude Code
docker exec -it claude-code-executor claude
```

## Key Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Node 24 Alpine + Claude Code CLI |
| `docker-compose.yml` | Container config with env vars |
| `.env` | OAuth token (git-ignored) |
| `claude-config/.claude.json` | Onboarding bypass flag |

## Important Facts

### Authentication
- Use `CLAUDE_CODE_OAUTH_TOKEN` only
- **Do NOT set `ANTHROPIC_API_KEY`** - they conflict and cause silent failures
- Token generated via `claude setup-token` from logged-in session

### Onboarding Bypass
Claude checks `hasCompletedOnboarding` flag before accepting OAuth token ([bug #8938](https://github.com/anthropics/claude-code/issues/8938)).

Solution: `claude-config/.claude.json` with `{"hasCompletedOnboarding": true}` is copied into image (see `Dockerfile`).

## Usage

```bash
# Interactive
docker exec -it claude-code-executor claude

# Non-interactive
docker exec claude-code-executor claude --print "Your prompt here"

# With project directory mounted
docker run -v /path/to/project:/workspace ...
```
