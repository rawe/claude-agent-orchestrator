---
id: capabilities-problem
title: "The Configuration Problem"
subtitle: "Duplication leads to inconsistency"
---

## The Problem

When multiple agents need the same tool (like Neo4j), you duplicate:

### 1. MCP Server Config

```json
// code-reviewer/agent.mcp.json
{
  "mcpServers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9501/mcp"
    }
  }
}

// doc-writer/agent.mcp.json
{
  "mcpServers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9501/mcp"
    }
  }
}

// test-writer/agent.mcp.json
{
  "mcpServers": {
    "neo4j": {
      "type": "http",
      "url": "http://localhost:9501/mcp"
    }
  }
}
```

### 2. Usage Knowledge

Each agent's system prompt repeats how to use it:

> "The Neo4j graph has nodes: Person, Project, Module. Use MATCH patterns to query relationships like AUTHORED and DEPENDS_ON..."

## The Pain

- **Config drift** - MCP endpoints diverge across blueprints
- **Knowledge drift** - Agents learn different "truths" about the schema
- **Update nightmare** - Endpoint changes? Update every blueprint manually
