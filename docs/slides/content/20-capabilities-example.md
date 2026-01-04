---
id: capabilities-example
title: "Real Example: Neo4j Knowledge Graph"
subtitle: "One capability, many agents"
---

## The neo4j-knowledge-graph Capability

Graph database access for agents.

### MCP Server Config

```yaml
neo4j-mcp:
  command: "npx neo4j-mcp"
  env:
    NEO4J_URI: "bolt://localhost:7687"
    NEO4J_USER: "neo4j"
    NEO4J_PASS: "${NEO4J_PASSWORD}"
```

### Allowed Tools

- `neo4j_query`
- `neo4j_create`
- `neo4j_update`
- `neo4j_delete`

## Agents Using This Capability

- **code-reviewer** - Stores review findings
- **doc-writer** - Queries architecture info
- **dependency-analyzer** - Maps code relationships

## The Benefit

**Change password once, all 3 agents updated automatically**
