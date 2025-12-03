# Confluence Researcher Agent

Research agent for searching and analyzing Confluence content using iterative CQL queries.

**MCP Server:** [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)

## How It Works

The agent follows an iterative research pattern:
1. **Initial Search** - Formulates CQL (Confluence Query Language) queries based on the question
2. **Fetch & Evaluate** - Retrieves Confluence pages from top results and evaluates relevance
3. **Iterate** - Refines CQL queries if information is insufficient
4. **Generate Output** - Creates result markdown and sources JSON with documented findings

## Setup

**Important:** This agent requires the mcp-atlassian server running in HTTP mode via Docker.

See [../../mcp/README.md](../../mcp/README.md) for complete setup instructions including:
- Configuring Atlassian credentials in `.env`
- Starting the centralized MCP server for all Atlassian agents

## Output

Results are saved to `research-results/[yyyy-mm-dd]-[topic]/` by default:
- `research-sources.json` - Documented Confluence pages with URLs and relevance
- `research-result.md` - Research findings summary
