# Atlassian MCP Server

Docker-based MCP server for Confluence and Jira integration via HTTP transport.

---

## Quick Start

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Atlassian credentials
   ```

2. **Start server:**
   ```bash
   docker compose up -d
   ```

3. **Verify:**
   ```bash
   curl http://127.0.0.1:9000
   ```

---

## Configuration

### Environment Variables

**Confluence:**
- `CONFLUENCE_URL` - Your Confluence URL (e.g., `https://your-site.atlassian.net/wiki`)
- `CONFLUENCE_USERNAME` - Your email address
- `CONFLUENCE_API_TOKEN` - API token

**Jira:**
- `JIRA_URL` - Your Jira URL (e.g., `https://your-site.atlassian.net`)
- `JIRA_USERNAME` - Your email address
- `JIRA_API_TOKEN` - API token

### Creating an API Token

1. Navigate to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a descriptive label
4. Copy the token (only shown once)

---

## API Usage

### Endpoint

- **Base URL:** `http://127.0.0.1:9000`

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
docker compose logs mcp-atlassian
```

**Common issues:**
- Invalid API token - Regenerate at Atlassian
- Wrong URL format - Use full URL with `/wiki` for Confluence
- Network issues - Check firewall/VPN

---

## Security Notes

- Server binds to `127.0.0.1` (local access only)
- Never commit `.env` file
- Rotate API tokens regularly

---

## Source

[sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)
