---
id: capabilities-example
title: "Real Example: Neo4j Knowledge Graph"
subtitle: "One capability, many agents"
---

## The neo4j-knowledge-graph Capability

### MCP Server Config

```json
{
  "mcpServers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9501/mcp"
    }
  }
}
```

### Domain Knowledge (Text)

> **Ontology:**
> The knowledge graph contains the following structure:
>
> **Nodes:** Person, Project, Module, Document
>
> **Relations:**
> - AUTHORED (Person → Document)
> - WORKS_ON (Person → Project)
> - DEPENDS_ON (Module → Module)
> - BELONGS_TO (Module → Project)
>
> Always use parameterized Cypher queries. Prefer MATCH patterns over raw node IDs.

## Agents Using This Capability

| Agent | Purpose |
|-------|---------|
| code-reviewer | Queries architecture relationships |
| doc-writer | Finds documentation gaps |
| dependency-analyzer | Maps module dependencies |

## The Benefit

**Change endpoint or schema once → all agents updated automatically**
