# Azure DevOps Researcher Agent

Research agent for searching and analyzing Azure DevOps work items.

**MCP Server:** Azure DevOps MCP HTTP Server (local)

## How It Works

The agent follows an iterative research pattern:
1. **Search & Retrieve** - Uses ADO MCP server tools to search for work items based on the question
2. **Evaluate & Iterate** - Evaluates relevance and refines searches if information is insufficient
3. **Generate Output** - Creates result markdown and sources JSON with documented findings

## Setup

**Important:** This agent requires the Azure DevOps MCP server running in HTTP mode.

See [../../mcp/README.md](../../mcp/README.md) for complete setup instructions including:
- Configuring Azure DevOps credentials in `.env`
- Starting the MCP server

## Output

Results are saved to `research-results/[yyyy-mm-dd]-[topic]/` by default:
- `research-sources.json` - Documented Azure DevOps work items with URLs and relevance
- `research-result.md` - Research findings summary