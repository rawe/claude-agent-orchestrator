# Package 02: Context Store Plugin

## Goal
Rename document-sync plugin to context-store plugin.

## Source → Target
```
plugins/document-sync/ → plugins/context-store/
```

## Steps

1. **Rename plugin directory**
   - Rename `plugins/document-sync/` → `plugins/context-store/`

2. **Rename skill directory**
   - Rename `skills/document-sync/` → `skills/context-store/`

3. **Update skill.md**
   - Update name and description to reference "Context Store"

4. **Update manifest/plugin config**
   - Update `.claude-plugin/` or `manifest.json` with new skill path

5. **Update command lib imports**
   - Update any internal path references in `commands/lib/`

## Verification
- All doc-* commands work from new location
- Skill is discoverable by Claude Code

## References
- Target structure: See [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure) → `/plugins/context-store/`
- Component details: See [ARCHITECTURE.md](./ARCHITECTURE.md#context-store-plugin)
