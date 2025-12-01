---
name: Create Commit Message
description: Create commit messages without AI attribution.
---

Create a concise commit message, do not do the commit.
/
## Commit Message Guidelines

When generating commit messages, please adhere to the following guidelines:

**NEVER include AI attribution in commit messages.**

Do NOT include:
- "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
- "Co-Authored-By: Claude <noreply@anthropic.com>"
- Any other AI-related attribution or signatures

Commit messages should be:
- Professional and concise
- Focused on the technical changes
- Written in conventional commit format (feat:, fix:, chore:, etc.)
- Free of emojis and AI attribution


## Examples

### Good Commit Message
```
feat: Implement ao-list-agents command

Add command to list all available agent blueprints with bash-compatible
output format. Includes alphabetical sorting and empty directory handling.
```

### Bad Commit Message (NEVER DO THIS)
```
feat: Implement ao-list-agents command

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```