# Package 05: Orchestrator Plugin

## Goal
Rename agent-orchestrator plugin to orchestrator plugin.

## Source → Target
```
plugins/agent-orchestrator/ → plugins/orchestrator/
```

## Steps

1. **Rename plugin directory**
   - Rename `plugins/agent-orchestrator/` → `plugins/orchestrator/`

2. **Rename skill directory**
   - Rename `skills/agent-orchestrator/` → `skills/orchestrator/`

3. **Update skill.md**
   - Update name and references to "Orchestrator"

4. **Update manifest/plugin config**
   - Update `.claude-plugin/` or `manifest.json` with new skill path

5. **Update command lib imports**
   - Update any internal path references in `commands/lib/`

## Note
MCP server is NOT moved in this step. It remains at its current location temporarily and will be moved in Package 06.

## Verification
- All ao-* commands work from new location
- Skill is discoverable by Claude Code
- MCP server still works (paths will be updated in next package)

## References
- Target structure: See [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure) → `/plugins/orchestrator/`
- Component details: See [ARCHITECTURE.md](./ARCHITECTURE.md#orchestrator-plugin)
