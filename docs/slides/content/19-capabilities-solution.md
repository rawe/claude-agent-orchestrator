---
id: capabilities-solution
title: "Capabilities"
subtitle: "Extract common config into reusable modules"
---

## The Solution

Instead of duplicating config, extract it into a **Capability** that blueprints can reference.

## How It Works

**Blueprint** references a capability by name:

```yaml
# code-reviewer blueprint
capabilities:
  - neo4j-kg
own_config:
  prompt: "Review code..."
  metadata: {...}
```

**Capability** contains the shared configuration:

```yaml
# neo4j-kg capability
mcp_servers:
  neo4j:
    url: bolt://...
    user: neo4j
allowed_tools:
  - neo4j_query
  - neo4j_write
```

## At Runtime: Merge

The system merges the blueprint's own config with all referenced capabilities to create the **Resolved Agent**:

- **From Blueprint**: prompt, metadata
- **From Capability**: neo4j connection, allowed tools
