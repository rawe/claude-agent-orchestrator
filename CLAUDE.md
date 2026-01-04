# Claude AI Assistant Guidelines

## Critical Rules

### 1. Git Commit Policy

**NEVER create git commits without explicit user approval.**

- Always present changes and wait for approval before committing
- Show the user what files have changed and what the commit message will be
- Only create a commit after receiving explicit confirmation from the user

### 2. No Silent Fallbacks

**NEVER implement fallback behavior without explicit user approval.**

- Always ask the user before adding fallback/backward-compatibility code
- Fallbacks can hide bugs and make it harder to verify new implementations work correctly
- If a feature fails, it should fail explicitly - not silently fall back to old behavior
- When in doubt, raise an error instead of falling back

## Python info

**CRITICAL: Always use `uv run` to execute Python scripts and commands.**

* Use `uv run python` instead of `python` or `python3` directly
* Use `uv run --script <script.py>` to run Python scripts (--script is required for Windows compatibility)
* NEVER use `pip`, `pip3`, or `uv sync` - the `uv run` command handles everything automatically
* Examples:
  - `uv run python -m main` (run a module)
  - `uv run --script script.py --arg value` (run a script with arguments)

## Testing

Integration tests for Agent Coordinator and Agent Runner without UI.

Use SlashCommands `/tests/setup`, `/tests/case`, `/tests/run`, `/tests/teardown`.

See `tests/README.md`.

## Running Services (No Auth)

**Agent Coordinator** (port 8765):
```bash
cd servers/agent-coordinator && AUTH_ENABLED=false CORS_ORIGINS=* AGENT_ORCHESTRATOR_AGENTS_DIR=$(pwd)/../../config/agents uv run python -m main
```

**Dashboard** (port 3000):
```bash
cd dashboard && VITE_AUTH0_DOMAIN= VITE_AUTH0_CLIENT_ID= VITE_AUTH0_AUDIENCE= npm run dev
```

**Agent Runner**:
```bash
mkdir -p .agent-orchestrator/runner-project && PROJECT_DIR=.agent-orchestrator/runner-project ./servers/agent-runner/agent-runner
```