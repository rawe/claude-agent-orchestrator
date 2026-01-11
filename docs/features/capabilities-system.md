# Capabilities System

**Status:** Implemented
**Version:** 1.0
**Date:** 2025-12-30

## Overview

This document describes the Capabilities System for the Agent Orchestrator Framework. It introduces reusable capability definitions that can be shared across multiple agents, enabling better modularity and reducing configuration duplication.

## Motivation

### The Problem: Shared Knowledge Across Agents

Consider a common scenario: You have a Neo4j knowledge graph database that multiple agents need to work with. Each agent has a different role (researcher, analyst, reporter), but they all need to:

1. **Connect** to the same Neo4j database (MCP server configuration)
2. **Understand** the same data model (ontology/schema documentation)
3. **Follow** the same query patterns and best practices

Currently, agent configuration combines all concerns in a single place:

```
agents/graph-researcher/
├── agent.json              # name, description, tags
├── agent.system-prompt.md  # Role + ontology docs + query patterns (all mixed)
└── agent.mcp.json          # Neo4j MCP server config
```

This leads to several problems:

1. **Duplication**: Every agent working with Neo4j must duplicate the MCP configuration AND the ontology documentation
2. **Inconsistency**: When the schema changes, every agent's system prompt must be updated manually
3. **Tight Coupling**: The agent's core identity/role is mixed with domain knowledge (the ontology)
4. **No Reusability**: Common knowledge cannot be shared or composed

### Solution: Capabilities

A **Capability** is a reusable knowledge package that encapsulates:
- **MCP Server Configuration**: How to connect to the external system
- **Domain Knowledge**: Schema/ontology documentation, query patterns, best practices

Agents reference capabilities by name, and the system merges them at runtime.

**Example**: A `neo4j-knowledge-graph` capability contains:
- MCP config: Neo4j connection details
- Text: Complete ontology (nodes, relationships, properties) + query patterns + best practices

Any agent that needs to work with this database simply adds the capability. They all share:
- The same connection configuration
- The same understanding of the data model
- The same best practices

This provides:

1. **Reusability**: Define the ontology once, use in many agents
2. **Consistency**: Update the schema docs in one place, all agents get the change
3. **Separation of Concerns**: Agent identity (who am I?) vs. domain knowledge (what do I work with?)
4. **Composability**: An agent can work with multiple data sources by adding multiple capabilities

## Key Concepts

### Capability

A **Capability** is a self-contained configuration unit that provides:
- **Name**: Unique identifier (e.g., `playwright-browser`)
- **Description**: Human-readable explanation of what the capability provides
- **Text** (optional): Instructions to append to the agent's system prompt
- **MCP Servers** (optional): One or more MCP server configurations

### Capability Resolution

When an agent is loaded, capabilities are resolved and merged:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Agent Resolution Flow                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Agent Configuration              Capability Definition             │
│   ┌──────────────────┐            ┌────────────────────────┐        │
│   │ graph-researcher │            │ neo4j-knowledge-graph  │        │
│   │                  │            │                        │        │
│   │ system_prompt:   │            │ - text: ontology docs, │        │
│   │   "You are a     │            │   query patterns,      │        │
│   │    research..."  │            │   best practices       │        │
│   │                  │            │                        │        │
│   │ capabilities:    │───────────>│ - mcp: neo4j           │        │
│   │   - neo4j-       │            │                        │        │
│   │     knowledge-   │            └────────────────────────┘        │
│   │     graph        │                                              │
│   │                  │                                              │
│   │ mcp_servers:     │                                              │
│   │   (none)         │                                              │
│   └──────────────────┘                                              │
│            │                                                         │
│            ▼                                                         │
│   ┌──────────────────────────────────────────────────────┐          │
│   │              Merged Agent (API Response)              │          │
│   │                                                       │          │
│   │  system_prompt:                                       │          │
│   │    "You are a research..."                            │          │
│   │    ---                                                │          │
│   │    "## Knowledge Graph Ontology                       │          │
│   │     Node Types: Person, Team, Project...              │          │
│   │     Relationships: MEMBER_OF, WORKS_ON...             │          │
│   │     Query Patterns: MATCH (p:Person)..."              │          │
│   │                                                       │          │
│   │  mcp_servers:                                         │          │
│   │    neo4j: { type: http, url: ... }                    │          │
│   └──────────────────────────────────────────────────────┘          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Merging Rules

#### System Prompt Merging

The final system prompt is constructed by concatenating:
1. Agent's own system prompt (from `agent.system-prompt.md`)
2. Each capability's text, in declaration order

Separator between sections: `\n\n---\n\n`

```
{agent.system_prompt}

---

{capability_1.text}

---

{capability_2.text}
```

#### MCP Server Merging

MCP server configurations from all sources are merged into a single `mcp_servers` dictionary:
1. All capability MCP servers (in declaration order)
2. Agent-level MCP servers (from `agent.mcp.json`)

**Conflict Resolution**: If the same MCP server name appears in multiple sources (capabilities or agent), an **error** is raised. This prevents silent overwrites and ensures explicit configuration.

> **Note**: In future versions, agent-level MCP configuration (`agent.mcp.json`) will be phased out in favor of capabilities-only configuration.

### Validation Rules

1. **Missing Capability**: If an agent references a capability that doesn't exist, loading the agent **fails with an error**
2. **MCP Server Name Conflict**: If multiple sources define the same MCP server name, loading **fails with an error**
3. **Capability Name Format**: Same rules as agent names (1-60 chars, alphanumeric + hyphens/underscores, starts with letter/number)

## Storage Structure

### Directory Layout

Capabilities are stored alongside agents in the configuration directory:

```
.agent-orchestrator/
├── agents/
│   └── {agent-name}/
│       ├── agent.json                # + new "capabilities" array
│       ├── agent.system-prompt.md    # Agent's core system prompt
│       └── agent.mcp.json            # Agent-level MCP (optional, legacy)
└── capabilities/
    └── {capability-name}/
        ├── capability.json           # name, description
        ├── capability.text.md        # Optional: usage instructions
        └── capability.mcp.json       # Optional: MCP server configs
```

### Capability Files

#### capability.json (Required)

```json
{
  "name": "playwright-browser",
  "description": "Browser automation and testing via Playwright MCP server"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique capability identifier |
| `description` | string | Yes | Human-readable description |

#### capability.text.md (Optional)

Plain markdown file with instructions to append to the system prompt:

```markdown
## Browser Automation

Use the Playwright MCP server for browser automation tasks:
- `browser_navigate`: Navigate to URLs
- `browser_click`: Click elements
- `browser_screenshot`: Capture screenshots

Always wait for page load before interacting with elements.
```

#### capability.mcp.json (Optional)

MCP server configuration in the same format as `agent.mcp.json`:

```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

A capability can define multiple MCP servers:

```json
{
  "mcpServers": {
    "context-store-http": {
      "type": "http",
      "url": "http://localhost:8766/mcp/"
    },
    "context-store-search": {
      "type": "http",
      "url": "http://localhost:8766/search/"
    }
  }
}
```

### Agent Configuration

#### Updated agent.json Schema

```json
{
  "name": "graph-researcher",
  "description": "Explores the knowledge graph to find information",
  "tags": ["internal", "research"],
  "capabilities": ["neo4j-knowledge-graph"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique agent identifier |
| `description` | string | Yes | Human-readable description |
| `tags` | string[] | No | Filtering labels (default: `[]`) |
| `capabilities` | string[] | No | Capability references (default: `[]`) |
| `skills` | string[] | No | Built-in capabilities (future) |
| `demands` | object | No | Runner requirements (ADR-011) |

## API Design

### Capabilities API

New CRUD endpoints for managing capabilities:

#### List Capabilities

```
GET /capabilities
```

**Response:**
```json
[
  {
    "name": "neo4j-knowledge-graph",
    "description": "Company knowledge graph with organizational and project data",
    "has_text": true,
    "has_mcp": true,
    "mcp_server_names": ["neo4j"],
    "created_at": "2025-12-30T10:00:00Z",
    "modified_at": "2025-12-30T10:00:00Z"
  }
]
```

#### Get Capability

```
GET /capabilities/{name}
```

**Response:**
```json
{
  "name": "neo4j-knowledge-graph",
  "description": "Company knowledge graph with organizational and project data",
  "text": "## Knowledge Graph Ontology\n\nThis Neo4j database contains...",
  "mcp_servers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9003/mcp/"
    }
  },
  "created_at": "2025-12-30T10:00:00Z",
  "modified_at": "2025-12-30T10:00:00Z"
}
```

#### Create Capability

```
POST /capabilities
```

**Request Body:**
```json
{
  "name": "neo4j-knowledge-graph",
  "description": "Company knowledge graph with organizational and project data",
  "text": "## Knowledge Graph Ontology\n\n...",
  "mcp_servers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9003/mcp/"
    }
  }
}
```

#### Update Capability

```
PATCH /capabilities/{name}
```

**Request Body:** (partial update)
```json
{
  "description": "Updated description",
  "text": "Updated instructions..."
}
```

#### Delete Capability

```
DELETE /capabilities/{name}
```

**Response:** `204 No Content`

**Note:** Deletion should warn or fail if the capability is referenced by agents.

### Agents API (Unchanged Interface)

The `GET /agents/{name}` endpoint returns the **merged** agent with resolved capabilities:

```json
{
  "name": "graph-researcher",
  "description": "Explores the knowledge graph to find information",
  "system_prompt": "You are a research specialist...\n\n---\n\n## Knowledge Graph Ontology\n\nThis Neo4j database contains...",
  "mcp_servers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9003/mcp/"
    }
  },
  "tags": ["internal", "research"],
  "status": "active",
  "created_at": "2025-12-30T10:00:00Z",
  "modified_at": "2025-12-30T10:00:00Z"
}
```

The API consumer sees a single, merged `system_prompt` and `mcp_servers` - the capabilities abstraction is transparent.

### Extended Agent Response (Optional)

For management UIs that need to see the raw configuration:

```
GET /agents/{name}?include_raw=true
```

**Response:** (includes both merged and raw)
```json
{
  "name": "graph-researcher",
  "description": "Explores the knowledge graph to find information",
  "system_prompt": "... (merged) ...",
  "mcp_servers": { ... (merged) ... },
  "raw": {
    "system_prompt": "You are a research specialist...",
    "mcp_servers": null,
    "capabilities": ["neo4j-knowledge-graph"]
  }
}
```

## Dashboard Integration

### Capabilities Management Page

New page for CRUD operations on capabilities:

- **List View**: Table of all capabilities with name, description, MCP server count
- **Create/Edit Form**:
  - Name field (validated)
  - Description textarea
  - Text editor (markdown) for usage instructions
  - MCP servers editor (JSON or form-based)
- **Delete**: With confirmation and usage check

### Agent Edit Form

Updated agent edit form with capability selection:

- **Existing Fields**: Name, description, tags, system prompt, MCP servers
- **New Field**: Capabilities multi-select dropdown
  - Shows all available capabilities
  - Selected capabilities shown as chips/tags
  - Order determined by selection order

### Preview Panel

When editing an agent, show a preview of the merged result:
- Final system prompt (agent + capability texts)
- Final MCP servers (merged from all sources)
- Highlight any conflicts (for error cases)

## Example Configurations

This example demonstrates the core use case: multiple agents sharing the same Neo4j knowledge graph capability.

### Capability: neo4j-knowledge-graph

```
capabilities/neo4j-knowledge-graph/
├── capability.json
├── capability.text.md
└── capability.mcp.json
```

**capability.json:**
```json
{
  "name": "neo4j-knowledge-graph",
  "description": "Company knowledge graph with organizational and project data"
}
```

**capability.text.md:**
```markdown
## Knowledge Graph Ontology

This Neo4j database contains organizational and project information.

### Node Types

| Label | Properties | Description |
|-------|------------|-------------|
| `Person` | `id`, `name`, `email`, `role`, `department` | Employees and contractors |
| `Team` | `id`, `name`, `description`, `created_at` | Organizational teams |
| `Project` | `id`, `name`, `status`, `start_date`, `end_date` | Active and completed projects |
| `Document` | `id`, `title`, `type`, `url`, `created_at` | Documentation artifacts |
| `Technology` | `id`, `name`, `category`, `version` | Tech stack components |

### Relationship Types

| Type | From | To | Properties | Description |
|------|------|-----|------------|-------------|
| `MEMBER_OF` | Person | Team | `since`, `role` | Team membership |
| `MANAGES` | Person | Team | `since` | Team leadership |
| `WORKS_ON` | Person | Project | `role`, `allocation` | Project assignment |
| `OWNS` | Team | Project | `since` | Project ownership |
| `AUTHORED` | Person | Document | `date` | Document authorship |
| `USES` | Project | Technology | `version`, `purpose` | Tech stack usage |
| `DEPENDS_ON` | Project | Project | `type` | Project dependencies |

### Query Patterns

**Find team members:**
```cypher
MATCH (p:Person)-[r:MEMBER_OF]->(t:Team {name: $teamName})
RETURN p.name, p.role, r.since
```

**Find person's projects:**
```cypher
MATCH (p:Person {email: $email})-[w:WORKS_ON]->(proj:Project)
RETURN proj.name, proj.status, w.role
```

**Find project tech stack:**
```cypher
MATCH (proj:Project {name: $projectName})-[u:USES]->(tech:Technology)
RETURN tech.name, tech.category, u.purpose
```

### Best Practices

1. Always use parameterized queries (never concatenate user input)
2. Use `OPTIONAL MATCH` when relationships may not exist
3. Limit results with `LIMIT` for exploration queries
4. Use `RETURN DISTINCT` to avoid duplicate results
```

**capability.mcp.json:**
```json
{
  "mcpServers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9003/mcp/"
    }
  }
}
```

---

### Agent: graph-researcher

A researcher agent that explores the knowledge graph to answer questions.

```
agents/graph-researcher/
├── agent.json
└── agent.system-prompt.md
```

**agent.json:**
```json
{
  "name": "graph-researcher",
  "description": "Explores the knowledge graph to find information",
  "tags": ["internal", "research"],
  "capabilities": ["neo4j-knowledge-graph"]
}
```

**agent.system-prompt.md:**
```markdown
You are a research specialist. Your role is to:
- Answer questions by querying the knowledge graph
- Explore relationships between entities
- Provide comprehensive, well-sourced answers

Be thorough in your research. Follow relationships to discover relevant context.
```

---

### Agent: graph-analyst

An analyst agent that performs deeper analysis on the same knowledge graph.

```
agents/graph-analyst/
├── agent.json
└── agent.system-prompt.md
```

**agent.json:**
```json
{
  "name": "graph-analyst",
  "description": "Analyzes patterns and insights from the knowledge graph",
  "tags": ["internal", "analysis"],
  "capabilities": ["neo4j-knowledge-graph"]
}
```

**agent.system-prompt.md:**
```markdown
You are a data analyst specialist. Your role is to:
- Identify patterns and trends in the knowledge graph
- Generate insights about team structures and project health
- Create summary reports with actionable recommendations

Focus on quantitative analysis and pattern recognition.
```

---

### Agent: graph-reporter

A reporter agent that creates formatted reports from the knowledge graph.

```
agents/graph-reporter/
├── agent.json
└── agent.system-prompt.md
```

**agent.json:**
```json
{
  "name": "graph-reporter",
  "description": "Creates formatted reports from knowledge graph data",
  "tags": ["external"],
  "capabilities": ["neo4j-knowledge-graph"]
}
```

**agent.system-prompt.md:**
```markdown
You are a report generation specialist. Your role is to:
- Query the knowledge graph for requested information
- Format results into clear, readable reports
- Present data with appropriate tables and summaries

Keep reports concise and well-structured.
```

---

### Resolved Output Example

When `graph-researcher` is loaded via `GET /agents/graph-researcher`, the API returns the merged result:

**Resolved system_prompt:**
```markdown
You are a research specialist. Your role is to:
- Answer questions by querying the knowledge graph
- Explore relationships between entities
- Provide comprehensive, well-sourced answers

Be thorough in your research. Follow relationships to discover relevant context.

---

## Knowledge Graph Ontology

This Neo4j database contains organizational and project information.

### Node Types

| Label | Properties | Description |
|-------|------------|-------------|
| `Person` | `id`, `name`, `email`, `role`, `department` | Employees and contractors |
| `Team` | `id`, `name`, `description`, `created_at` | Organizational teams |
...

(full ontology, relationships, query patterns, and best practices)
```

**Resolved mcp_servers:**
```json
{
  "neo4j": {
    "type": "http",
    "url": "http://localhost:9003/mcp/"
  }
}
```

All three agents (`graph-researcher`, `graph-analyst`, `graph-reporter`) share:
- The same Neo4j connection configuration
- The same ontology documentation
- The same query patterns and best practices

When the schema changes, update the capability once - all agents get the change automatically.

## Migration Path

### Phase 1: Additive (Current Proposal)

- Add capabilities as optional feature
- Existing agents continue to work unchanged
- New agents can use capabilities alongside agent-level MCP config
- Both coexist without breaking changes

### Phase 2: Encourage Adoption

- Dashboard defaults to capability-based configuration
- Document best practices for capability design
- Provide migration tooling for existing agents

### Phase 3: Deprecate Agent-Level MCP (Future)

- Warn when agent-level MCP config is used
- All MCP configuration should come from capabilities
- Agent-level `agent.mcp.json` becomes deprecated

## Implementation

This feature is **implemented**. For detailed implementation breakdown, see [Work Packages](./capabilities-system/README.md).

### Remaining Tasks

- [ ] Update ARCHITECTURE.md with capabilities concept
- [ ] Migration guide for existing agents
- [ ] Preview panel for merged result (optional enhancement)
