# Confluence Researcher Agent

This agent uses the **mcp-atlassian** MCP server for Confluence integration.

**MCP Server:** [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)

## Environment Variables

This agent requires Atlassian credentials. Set these in `.claude/settings.local.json`:

```json
{
  "env": {
    "CONFLUENCE_URL": "https://your-domain.atlassian.net",
    "CONFLUENCE_USERNAME": "your-email@example.com",
    "CONFLUENCE_API_TOKEN": "your-confluence-api-token"
  }
}
```

## Required Variables

- `CONFLUENCE_URL` - Your Confluence instance URL
- `CONFLUENCE_USERNAME` - Your Confluence email
- `CONFLUENCE_API_TOKEN` - Confluence API token (generate at atlassian.com)

**Note:** The tokens can be the same if using a unified Atlassian account.
