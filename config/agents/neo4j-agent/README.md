# Neo4j Agent

General-purpose agent for interacting with Neo4j graph database. Suitable for querying, creating nodes and relationships, and managing graph data.

**MCP Server:** [neo4j-contrib/mcp-neo4j](https://github.com/neo4j-contrib/mcp-neo4j)

## Setup

**Important:** This agent requires the neo4j-cypher MCP server running in HTTP mode via Docker.

See [../../mcps/neo4j/README.md](../../mcps/neo4j/README.md) for complete setup instructions including:
- Configuring Neo4j credentials in `.env`
- Starting the MCP server

## Capabilities

This agent has full access to Neo4j tools and can:
- Execute read Cypher queries
- Execute write Cypher queries
- Inspect database schema (requires APOC plugin)
- Create and manage nodes and relationships
- Query and analyze graph data
