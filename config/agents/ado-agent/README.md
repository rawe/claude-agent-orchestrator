# Azure DevOps Agent

General-purpose agent for interacting with Azure DevOps. Suitable for simple tasks such as searching, reading, creating, and updating work items.

**MCP Server:** Azure DevOps MCP HTTP Server (local)

## Setup

**Important:** This agent requires the Azure DevOps MCP server running in HTTP mode.

See [../../mcp/README.md](../../mcp/README.md) for complete setup instructions including:
- Configuring Azure DevOps credentials in `.env`
- Starting the MCP server

## Capabilities

This agent has access to Azure DevOps tools and can:
- Search and read work items
- Create and update work items
- Manage work items as needed
