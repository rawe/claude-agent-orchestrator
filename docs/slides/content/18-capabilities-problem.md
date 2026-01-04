---
id: capabilities-problem
title: "The Configuration Problem"
subtitle: "Copy-pasting leads to inconsistency"
---

## The Problem

When multiple agents need the same MCP server configuration (like Neo4j), you end up copying the same config across all blueprints:

```yaml
# code-reviewer blueprint
neo4j-server:
  url: bolt://...
  user: neo4j
  pass: ****

# doc-writer blueprint
neo4j-server:
  url: bolt://...
  user: neo4j
  pass: ****

# test-writer blueprint
neo4j-server:
  url: bolt://...
  user: neo4j
  pass: ****
```

## Problems

- **Duplication** - Same config copied across many blueprints
- **Update Nightmare** - Change password? Update every blueprint manually
- **Drift Risk** - Configs diverge over time, causing bugs
