# Executor Profiles

Profiles use a composable naming pattern with three dimensions:

## Naming Dimensions

| Dimension | Term A | Term B | Description |
|-----------|--------|--------|-------------|
| **Permission** | `full-access` | `restricted` | bypassPermissions vs default |
| **Context** | `project` | `isolated` | loads project/local settings vs no settings |
| **Model** | `best` | `quick` | opus vs haiku |

## Naming Pattern

```
{permission}-{context}-{model}
```

## Available Profiles

| Profile | Permission Mode | Setting Sources | Model |
|---------|-----------------|-----------------|-------|
| `full-access-project-best` | bypassPermissions | project, local | opus |
| `full-access-isolated-best` | bypassPermissions | *(none)* | opus |
| `restricted-project-best` | default | project, local | opus |
| `full-access-project-quick` | bypassPermissions | project, local | haiku |

## Configuration Reference

### Permission Modes

- `bypassPermissions` - No permission prompts, full autonomous operation
- `acceptEdits` - Auto-accept file edits, prompt for other permissions
- `default` - Prompt for all permissions

### Setting Sources

- `project` - Load settings from `.claude/settings.json` in project directory
- `local` - Load settings from `.claude/settings.local.json`
- `user` - Load user-level settings
- *(empty array)* - No settings loaded, isolated execution

### Models

- `opus` - Most capable model, best for complex tasks
- `sonnet` - Balanced capability and speed
- `haiku` - Fastest model, best for simple tasks
