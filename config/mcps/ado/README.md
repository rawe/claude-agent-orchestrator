# Azure DevOps MCP HTTP Wrapper

HTTP wrapper for the official Azure DevOps MCP server, enabling remote access to work items via Streamable HTTP transport.

---

## Quick Start (Standalone)

If you want to run only the ADO MCP server:

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with ADO_ORG and ADO_PAT
   ```

2. **Start server:**
   ```bash
   docker-compose up -d
   ```

3. **Verify:**
   ```bash
   curl http://127.0.0.1:3000/health
   ```

---

## Multi-Server Setup (Recommended)

**To run both ADO and Atlassian MCP servers together**, use the parent `docker-compose.yml`:

```bash
# From the parent mcp/ directory
cd ..
cp .env.example .env
# Edit .env with all credentials
docker compose up -d
```

See `../README.md` for complete multi-server setup instructions.

---

## Configuration

### Environment Variables

**Required:**
- `ADO_ORG` - Azure DevOps organization name (e.g., `contoso` from `https://dev.azure.com/contoso`)
- `ADO_PAT` - Personal Access Token

**Optional:**
- `PORT` - HTTP server port (default: 3000)

### Creating a Personal Access Token (PAT)

1. Navigate to: `https://dev.azure.com/{org}/_usersSettings/tokens`
2. Click "New Token"
3. Set expiration (recommend 90 days with rotation)
4. Select scopes:
   - **Work Items** - Read
   - **Project and Team** - Read
5. Copy token (only shown once)

---

## API Usage

### Endpoints

**Health Check:**
```bash
curl http://127.0.0.1:3000/health
```

**MCP Endpoint:**
```bash
curl -X POST http://127.0.0.1:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

### Health Status

- **503 (unhealthy)** - MCP process not started (expected on first startup)
- **200 (healthy)** - MCP process running and ready

The MCP process starts lazily on the first `/mcp` request.

---

## Architecture

**Pattern:** stdio-to-HTTP bridge (adapter/proxy)

```
HTTP Client → Express Server → stdin/stdout Bridge → @azure-devops/mcp → Azure DevOps API
```

**Key Components:**
- `src/server.ts` - HTTP server & request routing
- `src/utils/process-manager.ts` - MCP child process lifecycle
- `src/utils/error-handler.ts` - Error handling & logging
- `src/config.ts` - Environment configuration

**Design Principles:**
- KISS - Keep implementation minimal
- YAGNI - No premature optimization
- Single long-running MCP process
- Local use only (127.0.0.1 binding)

See `docs/ado-mcp-http-wrapper-architecture.md` for detailed architecture.

---

## Development

### Local Development (without Docker)

```bash
npm install
cp .env.example .env
# Edit .env
npm run dev
```

### Docker Development

```bash
# Rebuild and restart
docker-compose up -d --build

# View logs
docker logs -f ado-mcp-http

# Shell into container
docker exec -it ado-mcp-http sh
```

### Debugging

Enable verbose logging by checking container logs:

```bash
docker logs ado-mcp-http --tail=100
```

Look for:
- `[MCP Request]` - Incoming requests
- `[MCP stdout chunk]` - Raw MCP responses
- `[MCP Response]` - Parsed responses
- `[ERROR]` - Error details

**Development Guide:** See `docs/DEVELOPMENT.md` for:
- Critical implementation details
- Common issues & solutions
- Testing strategies
- Performance considerations
- Modification examples

---

## Troubleshooting

### Container fails to start

**Check environment:**
```bash
docker exec ado-mcp-http env | grep ADO
```

**View logs:**
```bash
docker logs ado-mcp-http
```

### Health check fails

- MCP process may be initializing (wait 10-30s)
- Check PAT permissions and expiration
- Verify organization name is correct

### Authentication errors

- Verify PAT has required scopes (Work Items Read, Project and Team Read)
- Regenerate PAT if expired
- Ensure `ADO_ORG` is the short name only (e.g., `contoso`, not full URL)

### Timeout on requests

- Check logs for `[MCP Request]` and `[MCP Response]` entries
- Ensure MCP process is running: `docker exec ado-mcp-http ps aux | grep mcp`
- Restart container: `docker-compose restart`

**Full troubleshooting guide:** See `docs/DEVELOPMENT.md` section "Common Issues & Solutions"

---

## Management

**Start:**
```bash
docker-compose up -d
```

**Stop:**
```bash
docker-compose down
```

**View logs:**
```bash
docker logs -f ado-mcp-http
```

**Restart:**
```bash
docker-compose restart
```

**Rebuild after code changes:**
```bash
docker-compose up -d --build
```

---

## Security Notes

- Server binds to `127.0.0.1` (local access only)
- Never commit `.env` file
- Rotate PAT regularly (90 days recommended)
- Not designed for production/external exposure

---

## Documentation

- **Architecture:** `docs/ado-mcp-http-wrapper-architecture.md` - Complete design document
- **Development:** `docs/DEVELOPMENT.md` - Implementation details, debugging, troubleshooting
- **Multi-server setup:** `../README.md` - Running with other MCP servers

---

## Technical Details

**Runtime:** Node.js 20 LTS + TypeScript
**Framework:** Express.js
**MCP Backend:** [@azure-devops/mcp](https://github.com/microsoft/azure-devops-mcp)
**Transport:** JSON-RPC 2.0 over stdio, exposed via HTTP
**Scope:** Work items domain only
**Image Size:** ~150MB (Alpine-based)
