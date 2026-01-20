# MCP Servers (Agent Capabilities)

MCP (Model Context Protocol) servers that provide capabilities to agents. These are the tools agents use to interact with external services and the framework itself.

**Why HTTP Mode?** Agents in this project use HTTP-mode MCP servers. The stdio transport is not supported due to subprocess handling limitations when agents start their own MCP server instances.

---

## Available Servers

| Server | Port | Description | Type | Requires .env |
|--------|------|-------------|------|---------------|
| Agent Orchestrator | embedded* | Agent orchestration + framework access | Embedded in Agent Runner | No |
| [Context Store](./context-store/) | 9501 | Document storage and retrieval | Internal (Python) | No |
| [Neo4j](./neo4j/) | 9003 | Graph database queries (Cypher) | External (Docker) | No (has defaults) |
| [Atlassian](./atlassian/) | 9000 | Confluence and Jira integration | External (Docker) | Yes |
| [Azure DevOps](./ado/) | 9001 | Work Items access | External (Docker) | Yes |

*\* The Agent Orchestrator MCP is embedded in the Agent Runner. For external clients, start the runner with `--mcp-port 9500` to expose a fixed endpoint.*

**Internal servers** are Python-based and run via `uv run`.
**External servers** are Docker-based. Neo4j works out-of-the-box with the local Neo4j container; Atlassian and ADO require credentials.

---

## Quick Start

From the project root, use Make commands:

```bash
# Start all MCP servers
make start-mcps

# Start individually
make start-mcp-context-store
make start-mcp-neo4j        # Works with defaults (local Neo4j container)
make start-mcp-atlassian    # Requires atlassian/.env
make start-mcp-ado          # Requires ado/.env

# Stop all
make stop-mcps
```

---

## Agent Orchestrator MCP

The Agent Orchestrator MCP provides tools for spawning sub-agents, managing sessions, and accessing the framework.

### Embedded in Agent Runner

The MCP server is **embedded in the Agent Runner**:
- No separate server needed
- Agent configurations use `${AGENT_ORCHESTRATOR_MCP_URL}` placeholder
- The placeholder is dynamically replaced at runtime

### External Clients

For external clients (Claude Desktop), start the Agent Runner with a fixed MCP port:

```bash
./servers/agent-runner/agent-runner --mcp-port 9500
```

This exposes the MCP endpoint at `http://localhost:9500/mcp` for any MCP-compatible client.

---

## Context Store MCP

Provides document management capabilities:
- Store documents with metadata and tags
- Query documents by name or tags
- Semantic search for documents by meaning
- Read document content (full or partial)
- Manage document relations

---

## Neo4j MCP

Provides graph database capabilities via Cypher queries:
- Execute read/write Cypher queries against Neo4j
- Inspect database schema (requires APOC plugin)
- Query knowledge graphs and relationships

**Default Configuration:** Connects to the local Neo4j container started by `docker-compose.yml` (port 7688, credentials: `neo4j/agent-orchestrator`). No `.env` file required for local use.

**Custom Configuration:** To connect to an external Neo4j instance:
```bash
cd neo4j
cp .env.example .env
# Edit .env with your Neo4j credentials
```

See [neo4j/README.md](./neo4j/README.md) for browser UI access and full configuration options.

---

## External Servers Setup

### Atlassian MCP Server

```bash
cd atlassian
cp .env.example .env
# Edit .env with your Atlassian credentials
docker compose up -d
```

### Azure DevOps MCP Server

```bash
cd ado
cp .env.example .env
# Edit .env with ADO_ORG and ADO_PAT
docker compose up -d
```

---

## Port Summary

| Service | Endpoint |
|---------|----------|
| Agent Orchestrator MCP | Embedded in Agent Runner (use `--mcp-port` for fixed port) |
| Context Store MCP | `http://127.0.0.1:9501/mcp` |
| Neo4j MCP | `http://127.0.0.1:9003/mcp/` |
| Atlassian MCP | `http://127.0.0.1:9000` |
| Azure DevOps MCP | `http://127.0.0.1:9001/mcp` |

---

## Documentation

- **Agent Orchestrator:** See `servers/agent-runner/README.md` (embedded in Agent Runner)
- **Context Store:** `context-store/README.md`
- **Neo4j:** `neo4j/README.md`
- **Atlassian:** `atlassian/README.md`
- **Azure DevOps:** `ado/README.md` and `ado/docs/`

---

## Network & Security

**Local Access Only:** All servers bind to `127.0.0.1` (localhost). Not accessible from network.

---

## Adding New Servers

1. Create a new subfolder (e.g., `newservice/`)
2. For Docker-based: Add `docker-compose.yml` and `.env.example`
3. For Python-based: Add the MCP server script
4. Add `README.md` with setup instructions
5. Add Make targets in the root `Makefile`
6. Update this README's "Available Servers" table
