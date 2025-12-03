# Web Researcher Agent

Research agent for searching and analyzing web content using iterative searches and content fetching.

**MCP Server:** None required (uses built-in web tools)

## How It Works

The agent follows an iterative research pattern:
1. **Initial Search** - Formulates web search queries based on the question
2. **Fetch & Evaluate** - Retrieves content from top results and evaluates relevance
3. **Iterate** - Refines search queries if information is insufficient
4. **Generate Output** - Creates result markdown and sources JSON with documented findings

## Setup

**No setup required.** This agent uses built-in web search and fetch capabilities.

Unlike Atlassian agents, no MCP server or Docker configuration is needed.

## Output

Results are saved to `research-results/[yyyy-mm-dd]-[topic]/` by default:
- `research-sources.json` - Documented web sources with URLs and relevance
- `research-result.md` - Research findings summary
