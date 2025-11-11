# Project Context - Agent Orchestrator CLI

## Goal

Rewrite `agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh` as multiple Python scripts using `uv` for progressive disclosure architecture optimized for LLM workflows.

## Command Mapping: Bash → Python

| Bash Script Command | Python Script | Purpose |
|---------------------|---------------|---------|
| `new` | `commands/ao-new` | Create new session |
| `resume` | `commands/ao-resume` | Resume existing session |
| `status` | `commands/ao-status` | Check session state (running/finished/not_existent) |
| `get-result` | `commands/ao-get-result` | Extract result from completed session |
| `list` | `commands/ao-list-sessions` | List all sessions with metadata |
| `list-agents` | `commands/ao-list-agents` | List available agent definitions |
| `show-config` | `commands/ao-show-config` | Display session configuration |
| `clean` | `commands/ao-clean` | Remove all sessions |

## Architecture

**Progressive Disclosure**: Each command is a standalone script that loads details only when called, reducing LLM context window usage by ~70%.

**Shared Logic**: Common functionality in `lib/` modules:
- `config.py` - Configuration loading (CLI > ENV > Default precedence)
- `session.py` - Session operations (validation, state detection, metadata)
- `agent.py` - Agent loading (agent.json, system prompts, MCP config)
- `claude_client.py` - Claude API integration
- `utils.py` - Common utilities (error handling, I/O)

## Current Status

✅ Project structure created
✅ All command stubs written with TODO comments
✅ All lib module stubs written with function signatures
✅ Complete documentation (architecture, development guide, LLM prompts)
⏳ Implementation pending

## Major Decision Required: Claude Integration Strategy

### Option A: Direct CLI Invocation (Bash Script Approach)
**Current bash script does**: Shell out to `claude` CLI binary

**Pros**:
- Easy 1:1 port from bash
- Minimal changes to existing logic
- CLI handles all session management

**Cons**:
- Less flexible
- Harder to customize
- Depends on CLI installation
- Shell subprocess overhead

### Option B: Claude Agent Python SDK
**Alternative approach**: Use official Python SDK directly

**Pros**:
- More flexible and powerful
- Programmatic control over all aspects
- Better error handling
- Native Python integration
- Long-term maintainability

**Cons**:
- Requires understanding SDK session management
- Need to replicate some CLI behavior
- More complex implementation
- May require architecture adjustments

### Decision Impact

Affects `lib/claude_client.py` implementation primarily. Rest of architecture remains unchanged.

**Recommendation**: Investigate SDK session management capabilities before deciding. If SDK supports:
- Session persistence/resumption
- Working directory context
- MCP tool integration
- Response streaming to files

Then Option B (SDK) is superior long-term.

## Next Steps

1. **Decide**: CLI vs SDK for Claude integration
2. **Implement**: Core infrastructure (config, utils, session validation)
3. **Test**: Simple read-only commands (ao-status, ao-list-sessions)
4. **Integrate**: Claude API wrapper
5. **Complete**: Full command implementations

## Key Files

- **Reference**: `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh`
- **Architecture**: `docs/architecture.md`
- **Implementation Guide**: `docs/development.md`
- **LLM Prompts**: `docs/llm-prompts.md`

## File Format Compatibility

Must maintain 100% compatibility with bash script:
- Session metadata: `.metadata.json`
- Session files: `session.txt`
- Agent structure: `agent.json`, `agent.system-prompt.md`, `agent.mcp.json`
- State detection algorithm: Must match bash behavior exactly

## Why This Matters

Progressive disclosure enables token-efficient LLM workflows. Instead of loading all commands upfront, LLMs discover → detail → execute progressively, ideal for Claude Code skills pattern.

---

**Resume from here**: Decide on Claude integration approach, then start with `lib/config.py` implementation.
