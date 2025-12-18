# Claude AI Assistant Guidelines

## Critical Rules

### 1. Git Commit Policy

**NEVER create git commits without explicit user approval.**

- Always present changes and wait for approval before committing
- Show the user what files have changed and what the commit message will be
- Only create a commit after receiving explicit confirmation from the user

## Python info

**CRITICAL: Always use `uv run` to execute Python scripts and commands.**

* Use `uv run python` instead of `python` or `python3` directly
* Use `uv run --script <script.py>` to run Python scripts (--script is required for Windows compatibility)
* NEVER use `pip`, `pip3`, or `uv sync` - the `uv run` command handles everything automatically
* Examples:
  - `uv run python -m main` (run a module)
  - `uv run --script script.py --arg value` (run a script with arguments)
  - `uv run --script mcps/agent-orchestrator/agent-orchestrator-mcp.py --http-mode` (run MCP server)

## Testing

Integration tests for Agent Coordinator and Agent Runner without UI. 

Use SlashCommands `/tests/setup`, `/tests/case`, `/tests/run`, `/tests/teardown`. 

See `tests/README.md`.