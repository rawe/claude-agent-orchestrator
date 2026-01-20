# Neo4j MCP Server

Docker-based MCP server for Neo4j graph database integration via HTTP transport.

---

## Neo4j Browser (UI)

The Neo4j container started by the main `docker-compose.yml` includes a browser UI:

- **URL:** http://localhost:7475
- **Credentials:** `neo4j` / `agent-orchestrator`

Use the browser to explore the graph, run Cypher queries interactively, and inspect data.

---

## Quick Start

**Works out-of-the-box with the local Neo4j container** from the main `docker-compose.yml`. No configuration required.

```bash
# From project root
make start-mcp-neo4j

# Or directly
cd mcps/neo4j && docker compose up -d
```

**Verify:**
```bash
curl http://127.0.0.1:9003/mcp/
```

### Custom Configuration (Optional)

To connect to an external Neo4j instance instead of the local container:

```bash
cp .env.example .env
# Edit .env with your Neo4j credentials
docker compose up -d
```

---

## Configuration

### Environment Variables

**Neo4j Connection:** (defaults connect to local Neo4j container)
- `NEO4J_URL` - Bolt URL (default: `bolt://host.docker.internal:7688`)
- `NEO4J_USERNAME` - Username (default: `neo4j`)
- `NEO4J_PASSWORD` - Password (default: `agent-orchestrator`)
- `NEO4J_DATABASE` - Database name (default: `neo4j`)
- `NEO4J_NAMESPACE` - Optional namespace for queries

**MCP Server:**
- `NEO4J_TRANSPORT` - Transport type (`http` for HTTP mode)
- `NEO4J_MCP_SERVER_HOST` - Bind host (default: `0.0.0.0`)
- `NEO4J_MCP_SERVER_PATH` - MCP endpoint path (default: `/mcp/`)

**CORS:**
- `NEO4J_MCP_SERVER_ALLOW_ORIGINS` - Allowed origins for CORS
- `NEO4J_MCP_SERVER_ALLOWED_HOSTS` - Allowed hosts

**Query Settings:**
- `NEO4J_READ_TIMEOUT` - Query timeout in seconds (default: `30`)
- `NEO4J_RESPONSE_TOKEN_LIMIT` - Max tokens in response (default: `10000`)
- `NEO4J_READ_ONLY` - Read-only mode (`true`/`false`)
- `NEO4J_SCHEMA_SAMPLE_SIZE` - Sample size for schema inspection (default: `1000`)

---

## API Usage

### Endpoint

- **Base URL:** `http://127.0.0.1:9003/mcp/`

### MCP Configuration

Use `neo4j-http.mcp.json` to configure Claude Code:
```json
{
  "mcpServers": {
    "neo4j-cypher": {
      "type": "http",
      "url": "http://localhost:9003/mcp/"
    }
  }
}
```

---

## Management

**Start:**
```bash
docker compose up -d
```

**Stop:**
```bash
docker compose down
```

**View logs:**
```bash
docker compose logs -f
```

**Restart:**
```bash
docker compose restart
```

---

## Troubleshooting

**Check logs:**
```bash
docker compose logs neo4j-mcp
```

**Common issues:**
- Connection refused - Ensure Neo4j is running and accessible
- Authentication failed - Check username/password in `.env`
- Schema tool error - Install APOC plugin in Neo4j for schema inspection

**Note:** The `get_neo4j_schema` tool requires the APOC plugin installed in Neo4j.

---

## Security Notes

- Server binds to `127.0.0.1` (local access only)
- Never commit `.env` file
- Use strong passwords for Neo4j

---

## Source

[neo4j-contrib/mcp-neo4j](https://github.com/neo4j-contrib/mcp-neo4j)
