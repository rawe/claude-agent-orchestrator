---
id: capabilities-solution
title: "Capabilities"
subtitle: "Reusable modules that bundle config and knowledge"
---

## The Solution

Extract shared configuration and knowledge into a **Capability** that blueprints reference.

## A Capability Contains

### 1. MCP Server Config
Which tool endpoint to use:

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

### 2. Text (Domain Knowledge)
How to use it properly:

> "The knowledge graph contains nodes: Person, Project, Module. Relations include AUTHORED, DEPENDS_ON, and WORKS_ON. Always use parameterized Cypher queries..."

## Blueprint References Capability

```json
{
  "name": "code-reviewer",
  "description": "Reviews code for quality",
  "capabilities": ["neo4j-knowledge-graph"]
}
```

## At Runtime: Merge

The system merges the blueprint with all referenced capabilities:

- **System prompt** = blueprint prompt + capability text
- **MCP servers** = blueprint servers + capability servers
