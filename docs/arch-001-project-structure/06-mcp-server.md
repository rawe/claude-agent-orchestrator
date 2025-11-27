# Package 06: MCP Server

## Goal
Move MCP server to `/interfaces/agent-orchestrator-mcp-server/`.

## Source → Target
```
plugins/agent-orchestrator/mcp-server/ → interfaces/agent-orchestrator-mcp-server/
```

Note: Source is the OLD location (before Package 05 renamed the plugin). If Package 05 is already applied, source is `plugins/orchestrator/mcp-server/`.

## Steps

1. **Create target directory**
   - Create `/interfaces/agent-orchestrator-mcp-server/`

2. **Move MCP server files**
   - Move `mcp-server/` contents → `interfaces/agent-orchestrator-mcp-server/`

3. **Update command paths**
   - Update `agent-orchestrator-mcp.py`: path to commands directory
   - Commands are now at `plugins/orchestrator/skills/orchestrator/commands/`

4. **Update libs references**
   - Update any path constants in `libs/constants.py` or `libs/utils.py`

5. **Remove from plugin**
   - Delete `plugins/orchestrator/mcp-server/` (now empty)

## Verification
- MCP server starts from new location
- All MCP tools work (list agents, start session, etc.)
- Claude Desktop can connect and use tools

## References
- Target structure: See [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure) → `/interfaces/agent-orchestrator-mcp-server/`
- Component details: See [ARCHITECTURE.md](./ARCHITECTURE.md#mcp-server)
