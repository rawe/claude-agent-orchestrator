# Example Agent Blueprints

This directory contains example agent blueprints that demonstrate the Agent Orchestrator blueprint structure.

## Blueprint Structure

Each agent blueprint is a folder containing:

```
{agent-name}/
├── agent.json                   # Required: Agent configuration
├── agent.system-prompt.md       # Optional: System prompt
├── agent.mcp.json               # Optional: MCP configuration
└── README.md                    # Optional: Setup instructions
```

**agent.json** - Agent configuration
- Defines agent name and description
- Name must match the folder name

**agent.system-prompt.md** - System prompt
- Contains role definition, expertise areas, and behavioral guidelines
- Automatically prepended to user prompts when the agent is used

**agent.mcp.json** - MCP configuration
- Configures MCP servers for external tool access
- Not all agents require MCP configurations


## Creating Custom Blueprints

1. Create a new folder with your agent name
2. Add `agent.json` with name and description
3. Add `agent.system-prompt.md` with role definition
4. Optionally add `agent.mcp.json` for external tools
5. The Agent Registry will automatically detect the new blueprint
