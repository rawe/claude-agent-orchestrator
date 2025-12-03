# Atlassian Agent

General-purpose agent for interacting with Jira and Confluence. Suitable for tasks beyond research such as creating issues, updating pages, and managing content.

**MCP Server:** [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)

## Setup

**Important:** This agent requires the mcp-atlassian server running in HTTP mode via Docker.

See [../../mcp/README.md](../../mcp/README.md) for complete setup instructions including:
- Configuring Atlassian credentials in `.env`
- Starting the centralized MCP server for all Atlassian agents

## Capabilities

This agent has full access to Atlassian tools and can:
- Search and read Confluence pages
- Create and update Confluence content
- Search and read Jira issues
- Create and update Jira issues
- Manage both platforms as needed
