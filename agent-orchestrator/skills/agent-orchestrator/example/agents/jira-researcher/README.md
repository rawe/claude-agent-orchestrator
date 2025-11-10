# Jira Researcher Agent

This agent uses the **mcp-atlassian** MCP server for Jira integration.

**MCP Server:** [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)

## Environment Variables

This agent requires Jira credentials. Set these in `.claude/settings.local.json`:

```json
{
  "env": {
    "JIRA_URL": "https://your-domain.atlassian.net",
    "JIRA_USERNAME": "your-email@example.com",
    "JIRA_API_TOKEN": "your-jira-api-token"
  }
}
```

## Required Variables

- `JIRA_URL` - Your Jira instance URL
- `JIRA_USERNAME` - Your Jira email
- `JIRA_API_TOKEN` - Jira API token (generate at atlassian.com)

**Note:** If the MCP server also supports Confluence, you may need to include Confluence variables as well, but they are not required for Jira-only operations.
