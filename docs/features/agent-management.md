# Agent Management Architecture

**Status:** Active
**Version:** 2.0
**Date:** 2025-12-11

## Overview

This document describes the agent management system for the Agent Orchestrator Framework. It covers how agents are defined, stored, discovered, and filtered based on their tags.

## Key Concepts

### Agent Blueprint

An **Agent Blueprint** is a configuration template that defines an agent's:
- **Name**: Unique identifier (e.g., `jira-researcher`)
- **Description**: Human-readable explanation of the agent's purpose
- **System Prompt**: Instructions that guide the agent's behavior
- **MCP Servers**: External tools the agent can access
- **Skills**: Built-in capabilities (future feature)
- **Tags**: Categorization labels for filtering and discovery
- **Status**: `active` or `inactive`

### Tags System

Tags are flexible labels that control agent discovery and filtering:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Tag-Based Filtering                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Consumer Request: tags=internal                               │
│   ─────────────────────────────────────────────────────────    │
│                                                                 │
│   ┌─────────────────┐    MATCH    ┌─────────────────┐          │
│   │ jira-researcher │  ─────────> │ ["internal",    │          │
│   │                 │             │  "research",    │          │
│   │                 │             │  "atlassian"]   │          │
│   └─────────────────┘             └─────────────────┘          │
│                                                                 │
│   ┌─────────────────┐    MATCH    ┌─────────────────┐          │
│   │ simple-agent    │  ─────────> │ ["internal"]    │          │
│   └─────────────────┘             └─────────────────┘          │
│                                                                 │
│   ┌─────────────────┐  NO MATCH   ┌─────────────────┐          │
│   │ bug-evaluator   │  ─────────> │ ["external"]    │          │
│   └─────────────────┘             └─────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Filtering Logic (AND):** When multiple tags are requested (e.g., `tags=internal,research`), only agents that have **ALL** the specified tags are returned.

### Reserved Tags

Two tags have special meaning by convention:

| Tag | Purpose |
|-----|---------|
| `external` | Entry-point agents for end users (Claude Desktop, Dashboard Chat) |
| `internal` | Worker agents for the orchestrator framework |

Agents can have both tags if they're usable in either context.

### Custom Tags

Beyond reserved tags, you can create domain-specific tags:

| Example | Purpose |
|---------|---------|
| `research` | Research/investigation agents |
| `atlassian` | Jira/Confluence integration agents |
| `testing` | QA and testing agents |
| `devops` | DevOps tooling agents |

## Agent Configuration

### File Structure

Agents are stored in directories under `.agent-orchestrator/agents/`:

```
.agent-orchestrator/
└── agents/
    └── my-agent/
        ├── agent.json              # Required: name, description, tags
        ├── agent.system-prompt.md  # Optional: system prompt
        ├── agent.mcp.json          # Optional: MCP server config
        └── .disabled               # Optional: marks agent as inactive
```

### agent.json Schema

```json
{
  "name": "my-agent",
  "description": "Description of what this agent does",
  "tags": ["internal", "custom-tag"],
  "skills": []
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique agent identifier |
| `description` | string | Yes | Human-readable description |
| `tags` | string[] | No | Filtering labels (default: `[]`) |
| `skills` | string[] | No | Built-in capabilities (future) |

## API Endpoints

### List Agents

```
GET /agents?tags=<comma-separated-tags>
```

**Query Parameters:**
- `tags` (optional): Comma-separated tags to filter by. Agents must have ALL specified tags.

**Examples:**
```bash
# Get all agents (management UI)
GET /agents

# Get agents with 'external' tag (end users)
GET /agents?tags=external

# Get agents with 'internal' tag (orchestrator)
GET /agents?tags=internal

# Get research agents for internal use
GET /agents?tags=internal,research
```

**Response:**
```json
[
  {
    "name": "jira-researcher",
    "description": "...",
    "tags": ["internal", "research", "atlassian"],
    "status": "active",
    ...
  }
]
```

### Environment/Header Configuration

Consumers can configure default tag filtering via:

| Mode | Configuration |
|------|---------------|
| HTTP | `X-Agent-Tags` header |
| stdio | `AGENT_TAGS` environment variable |

## Usage Examples

### Dashboard Management UI

The management UI fetches all agents without tag filtering:

```typescript
// services/agentService.ts
async getAgents(): Promise<Agent[]> {
  const response = await api.get('/agents');
  return response.data;
}
```

### Chat Interface (End Users)

The chat interface filters to external-facing agents:

```typescript
// services/chatService.ts
async listBlueprints(): Promise<Agent[]> {
  const response = await api.get('/agents?tags=external');
  return response.data;
}
```

### Orchestrator Framework (Internal)

Worker agents filter to internal agents:

```bash
# CLI command
ao-list-blueprints --tags internal

# API call
GET /agents?tags=internal
```

### Multi-Tag Filtering

Find research agents that work with Atlassian tools:

```bash
ao-list-blueprints --tags internal,research,atlassian
```

## Migration from Visibility System

The previous `visibility` field has been replaced with the `tags` system:

| Old `visibility` | New `tags` |
|------------------|------------|
| `"public"` | `["external"]` |
| `"internal"` | `["internal"]` |
| `"all"` | `["external", "internal"]` |

### Migration Benefits

1. **Flexibility**: Arbitrary tags beyond just external/internal
2. **Composability**: Multiple tags per agent
3. **Extensibility**: Custom domain-specific tags
4. **AND Logic**: Filter by multiple criteria simultaneously

## Best Practices

### Tag Naming

- Use lowercase, hyphenated names: `web-research`, `code-analysis`
- Keep tags concise: prefer `testing` over `quality-assurance-testing`
- Use established conventions: `external`, `internal`, `research`

### Agent Organization

```
Recommended tag structure:
├── Access level (required for filtering)
│   ├── external    → User-facing agents
│   └── internal    → Framework-only agents
├── Domain (optional)
│   ├── atlassian   → Jira/Confluence
│   ├── devops      → CI/CD, deployment
│   └── testing     → QA, E2E tests
└── Capability (optional)
    └── research    → Investigation tasks
```

### Example Configurations

**Entry-point orchestrator (both contexts):**
```json
{
  "name": "agent-orchestrator",
  "tags": ["external", "internal"]
}
```

**Internal research agent:**
```json
{
  "name": "confluence-researcher",
  "tags": ["internal", "research", "atlassian"]
}
```

**User-facing evaluation agent:**
```json
{
  "name": "bug-evaluator",
  "tags": ["external"]
}
```
