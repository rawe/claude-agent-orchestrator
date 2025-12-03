# MCP HTTP Servers

Docker-based MCP (Model Context Protocol) servers exposing services via HTTP transport.

**Why HTTP Mode?** Agents in this project use HTTP-mode MCP servers. The stdio transport is not supported due to subprocess handling limitations when agents start their own MCP server instances.

---

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials for the services you need.

### 2. Start All Servers

```bash
docker compose up -d
```

### 3. Verify

```bash
docker compose ps
curl http://127.0.0.1:9000  # Atlassian server
curl http://127.0.0.1:3000/health  # ADO server
```

---

## Available Servers

### Atlassian MCP Server (Port 9000)

**Services:** Confluence and Jira integration

**Configuration:**
```bash
CONFLUENCE_URL=https://your-site.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token
JIRA_URL=https://your-site.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-api-token
```

**Endpoints:**
- Base URL: `http://127.0.0.1:9000`

**Create API Token:** https://id.atlassian.com/manage-profile/security/api-tokens

**Source:** [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)

---

### Azure DevOps MCP Server (Port 3000)

**Services:** Work Items access only

**Configuration:**
```bash
# Organization name from https://dev.azure.com/{org}
ADO_ORG=your-organization-name

# PAT with Work Items (Read) + Project and Team (Read)
ADO_PAT=your-personal-access-token
```

**Endpoints:**
- MCP Endpoint: `http://127.0.0.1:3000/mcp`
- Health Check: `http://127.0.0.1:3000/health`

**Create PAT:** https://dev.azure.com/{org}/_usersSettings/tokens

**Required Permissions:**
- Work Items (Read)
- Project and Team (Read)

**Details:** See `ado/README.md` for implementation details and `ado/docs/` for architecture and development guides.

---

## Management

**Start all servers:**
```bash
docker compose up -d
```

**Start specific server:**
```bash
docker compose up -d mcp-atlassian  # Atlassian only
docker compose up -d mcp-ado        # Azure DevOps only
```

**Stop all servers:**
```bash
docker compose down
```

**View logs:**
```bash
docker compose logs -f              # All servers
docker compose logs -f mcp-atlassian  # Atlassian only
docker compose logs -f mcp-ado        # ADO only
```

**Restart after config changes:**
```bash
docker compose restart
```

**Rebuild ADO server after code changes:**
```bash
docker compose up -d --build mcp-ado
```

**Check status:**
```bash
docker compose ps
```

---

## Troubleshooting

### Atlassian Server Issues

**Check logs:**
```bash
docker compose logs mcp-atlassian
```

**Common issues:**
- Invalid API token → Regenerate at Atlassian
- Wrong URL format → Use full URL with `/wiki` for Confluence
- Network issues → Check firewall/VPN

### ADO Server Issues

**Check logs:**
```bash
docker compose logs mcp-ado
```

**Health check:**
```bash
curl http://127.0.0.1:3000/health
# Expected: {"status":"healthy","mcp_process":"running"}
```

**Common issues:**
- Invalid PAT → Check permissions and expiration
- Wrong organization name → Use short name only (e.g., `contoso`, not URL)
- Container unhealthy → MCP process not started yet (starts on first request)

**Development guide:** See `ado/docs/DEVELOPMENT.md`

---

## Network & Security

**Local Access Only:** All servers bind to `127.0.0.1` (localhost). Not accessible from network.

**Shared Network:** Services can communicate via `mcp-network` bridge.

**Port Summary:**
- `127.0.0.1:9000` → Atlassian MCP
- `127.0.0.1:3000` → Azure DevOps MCP

---

## Adding More Servers

Add new services to `docker-compose.yml`:

```yaml
services:
  mcp-new-service:
    image: your-image:latest
    container_name: mcp-new-service
    ports:
      - "127.0.0.1:PORT:PORT"
    env_file:
      - .env
    restart: unless-stopped
    networks:
      - mcp-network
```

Add configuration to `.env.example` and `.env`.
