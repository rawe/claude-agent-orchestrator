# Executor Profiles

**Status:** Implemented
**Version:** 1.0

## Overview

Executor Profiles provide configurable executor configurations for the Agent Runner. Instead of hardcoding executor settings, profiles allow operators to define named configurations that control how executors behave—including permission modes, model selection, and setting sources.

Each runner instance runs exactly one profile, and agent blueprints can specify which profile they require via the demand matching system.

## Motivation

### The Problem: Hardcoded Executor Settings

The Agent Runner executes agent runs via executors (e.g., Claude Code). Before profiles, executor settings were hardcoded:

```python
# Hardcoded in executor
options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",  # Always bypass
    model="sonnet",                        # Always sonnet
    setting_sources=["user", "project", "local"],
)
```

This created limitations:

| Use Case | Desired Configuration | Problem |
|----------|----------------------|---------|
| Autonomous coding | `permission_mode: bypassPermissions`, `model: opus` | Can't change model |
| Supervised editing | `permission_mode: acceptEdits`, `model: sonnet` | Can't change permission mode |
| Research tasks | `permission_mode: default`, restricted settings | Can't restrict settings |

**The core issue:** Different use cases require different executor configurations, but there was no way to configure this without modifying code.

### The Solution: Named Profiles

Executor Profiles solve this by separating configuration from implementation:

```
┌──────────────────────────────────────────────────────────────────┐
│  Before: Hardcoded                                               │
│  ┌────────────────────────┐                                      │
│  │ ao-claude-code-exec    │                                      │
│  │ permission: bypass     │  ← Can't change without code changes │
│  │ model: sonnet          │                                      │
│  └────────────────────────┘                                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  After: Profile-Driven                                           │
│                                                                   │
│  profiles/coding.json      profiles/research.json                │
│  ┌──────────────────┐      ┌──────────────────┐                  │
│  │ permission: bypass│      │ permission: default│                │
│  │ model: opus       │      │ model: sonnet     │                │
│  └────────┬─────────┘      └────────┬─────────┘                  │
│           │                         │                             │
│           ▼                         ▼                             │
│  ┌────────────────────────────────────────────────┐              │
│  │ ao-claude-code-exec                            │              │
│  │ Reads config from invocation, applies settings │              │
│  └────────────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Executor Profile

A **profile** is a named configuration bundle that specifies:

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Executor type (e.g., `claude-code`) |
| `command` | Yes | Relative path to executor script |
| `config` | No | Executor-specific settings passed at runtime |

**Example profile (`profiles/coding.json`):**

```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "bypassPermissions",
    "setting_sources": ["project", "local"],
    "model": "opus"
  }
}
```

### One Profile Per Runner

Each runner instance supports exactly one profile. To support multiple profiles, run multiple runner instances:

```bash
# Runner for autonomous coding
./agent-runner --profile coding --project-dir /workspace/coding

# Runner for supervised editing (separate instance)
./agent-runner --profile supervised --project-dir /workspace/editing
```

The Agent Coordinator routes runs to the appropriate runner based on profile matching.

### Demand Matching

Agent blueprints specify which executor profile they require via demands:

```json
{
  "name": "code-generator",
  "description": "Generates production code",
  "demands": {
    "executor_profile": "coding",
    "tags": ["python"]
  }
}
```

When a run is created, the coordinator matches it to a runner whose profile satisfies the demands.

### Runner Gateway

Executors communicate with the Agent Coordinator through the **Runner Gateway**—a local HTTP server that handles authentication and enriches requests with runner-owned data (hostname, executor profile).

This decouples executors from coordinator API details. See [Runner Gateway](./runner-gateway.md) for architecture and implementation details.

## Storage Structure

### Directory Layout

Profiles are stored in the runner's `profiles/` directory:

```
servers/agent-runner/
├── agent-runner                    # CLI with --profile flag
├── profiles/                       # Executor profiles
│   ├── coding.json
│   ├── research.json
│   └── supervised.json
├── executors/                      # Executor implementations
│   └── claude-code/
│       ├── ao-claude-code-exec
│       └── lib/
└── lib/
    ├── executor.py                 # Profile loading
    ├── runner_gateway.py           # Local HTTP gateway
    └── session_client.py           # Executor-to-gateway client
```

### Profile File Format

Each profile is a JSON file with the following schema:

```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "bypassPermissions",
    "setting_sources": ["project", "local"],
    "model": "opus"
  }
}
```

**Claude Code executor config options:**

| Option | Values | Description |
|--------|--------|-------------|
| `permission_mode` | `bypassPermissions`, `acceptEdits`, `default` | How the executor handles tool permissions |
| `setting_sources` | `["user", "project", "local"]` | Which Claude Code settings to load |
| `model` | `opus`, `sonnet`, etc. | Model to use (null = SDK default) |

## CLI Usage

### Starting with a Profile

```bash
# Start runner with specific profile
./agent-runner --profile coding --project-dir /workspace

# Profile is loaded from profiles/coding.json
```

### Listing Available Profiles

```bash
./agent-runner --profile-list

# Output:
# Available profiles:
#   coding
#   research
#   supervised
```

### Default Behavior (No Profile)

When no `--profile` flag is provided:

1. Uses hardcoded default executor: `executors/claude-code/ao-claude-code-exec`
2. No config passed (executor uses internal defaults)
3. Registers with coordinator as `executor_profile: "claude-code"`

This ensures backward compatibility with existing deployments.

### Profile Not Found

If a specified profile doesn't exist, the runner exits with an error:

```bash
./agent-runner --profile nonexistent

# ERROR: Profile 'nonexistent' not found.
# Available profiles: coding, research, supervised
# Exit code: 1
```

## Registration and Routing

### Runner Registration

When a runner starts, it registers with the coordinator:

```http
POST /runner/register
{
  "hostname": "dev-machine",
  "project_dir": "/workspace",
  "executor_profile": "coding",
  "executor": {
    "type": "claude-code",
    "command": "executors/claude-code/ao-claude-code-exec",
    "config": {
      "permission_mode": "bypassPermissions",
      "model": "opus"
    }
  },
  "tags": ["python", "docker"],
  "require_matching_tags": false
}
```

| Field | Description |
|-------|-------------|
| `executor_profile` | Profile name for demand matching |
| `executor` | Full profile content (for observability) |
| `require_matching_tags` | If true, only accept runs with matching tags |

### Demand Matching Flow

```
Agent Blueprint                          Runner
┌─────────────────────┐                 ┌─────────────────────┐
│ demands:            │                 │ executor_profile:   │
│   executor_profile: │                 │   "coding"          │
│     "coding"        │ ──── matches ───│                     │
│   tags: ["python"]  │                 │ tags: ["python",    │
│                     │                 │        "docker"]    │
└─────────────────────┘                 └─────────────────────┘
         │
         ▼
Run assigned to this runner
```

### Tagged-Only Mode

Runners can protect themselves from unrelated runs with `--require-matching-tags`:

```bash
./agent-runner --profile coding --require-matching-tags --tags python,docker
```

With this flag:

| Run Tags | Runner Tags | Result |
|----------|-------------|--------|
| `["python"]` | `["python", "docker"]` | Match (python matches) |
| `["nodejs"]` | `["python", "docker"]` | Rejected (no overlap) |
| `[]` (no tags) | `["python", "docker"]` | Rejected |

## Invocation Flow

When a run is assigned to a runner:

```
1. Runner receives run from coordinator
         │
         ▼
2. Runner builds invocation payload with executor_config from profile
   {
     "schema_version": "2.1",
     "mode": "start",
     "session_id": "ses_abc123",
     "prompt": "...",
     "executor_config": {          ← From profile
       "permission_mode": "bypassPermissions",
       "model": "opus"
     }
   }
         │
         ▼
3. Runner spawns executor with payload via stdin
   uv run --script ao-claude-code-exec < payload.json
         │
         ▼
4. Executor reads executor_config, applies settings
   options = ClaudeAgentOptions(
     permission_mode=config["permission_mode"],
     model=config["model"],
   )
         │
         ▼
5. Executor runs agent with configured options
```

## Example Profiles

### coding.json - Autonomous Development

For fully autonomous coding tasks with maximum permissions:

```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "bypassPermissions",
    "setting_sources": ["project", "local"],
    "model": "opus"
  }
}
```

### research.json - Supervised Research

For research tasks with restricted permissions:

```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "default",
    "setting_sources": ["project"],
    "model": "sonnet"
  }
}
```

### supervised.json - Human-in-the-Loop

For tasks requiring human approval of edits:

```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "acceptEdits",
    "setting_sources": ["user", "project", "local"],
    "model": "sonnet"
  }
}
```

## Coordinator Behavior

The coordinator stores executor details but treats them as opaque:

| Field | Coordinator Uses For |
|-------|---------------------|
| `executor_profile` | Demand matching (routing runs to runners) |
| `executor` | Stored and exposed via API (observability only) |

The coordinator does **not** interpret `executor.type` or `executor.config`—this separation ensures:

1. Coordinator remains executor-agnostic
2. Dashboard can show executor details
3. New executor types require no coordinator changes

## References

- [Runner Gateway](./runner-gateway.md) - Executor-coordinator communication architecture
- [ADR-010: Session Identity and Executor Abstraction](../adr/ADR-010-session-identity-and-executor-abstraction.md)
- [ADR-011: Runner Capabilities and Run Demands](../adr/ADR-011-runner-capabilities-and-run-demands.md)
- [Claude Agent SDK Documentation](https://docs.anthropic.com/en/docs/claude-code/sdk)
