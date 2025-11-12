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

**Self-Contained Design**: The `commands/` directory contains both executables AND their shared `lib/` as a subdirectory. This enables:
- Skills deployment (copy entire `commands/` to `.claude/skills/`)
- Simple imports (`Path(__file__).parent / "lib"`)
- Portability (no external dependencies)

**Shared Logic**: Common functionality in `commands/lib/` modules:
- `config.py` - Configuration loading (CLI > ENV > Default precedence)
- `session.py` - Session operations (validation, state detection, metadata)
- `agent.py` - Agent loading (agent.json, system prompts, MCP config)
- `claude_client.py` - Claude SDK wrapper (using Python SDK directly)
- `utils.py` - Common utilities (error handling, I/O)

## Current Status

✅ Project structure created with `commands/` containing `lib/` subdirectory
✅ All command stubs written with uv script headers
✅ All lib module stubs written with function signatures
✅ Complete documentation (architecture, SDK investigation, development guide)
✅ **Decision Made: Use Claude Agent Python SDK (Option B)**
⏳ Implementation pending

## Claude Integration Decision: Python SDK ✅

**Decision**: Use Claude Agent Python SDK directly (Option B)

**Investigation Results** (see `CLAUDE_SDK_INVESTIGATION.md`):
- ✅ Session persistence/resumption - `ClaudeAgentOptions(resume=session_id)`
- ✅ Working directory context - `ClaudeAgentOptions(cwd=project_dir)`
- ✅ MCP tool integration - `ClaudeAgentOptions(mcp_servers={...})`
- ✅ Response streaming - Async iterator over messages
- ✅ SDK-native message format - Uses dataclass serialization for `.jsonl`

**Benefits**:
- Native Python integration (no subprocess overhead)
- Better error handling (exceptions vs exit codes)
- Programmatic control over all aspects
- Type safety with full type hints
- Long-term maintainability

**Implementation**: See `ARCHITECTURE_PLAN.md` for detailed guidance on `lib/claude_client.py` using SDK's `query()` function and `ClaudeAgentOptions`.

## Next Steps (Implementation Roadmap)

### Phase 1: Core Infrastructure (Read-Only)
1. Implement `commands/lib/config.py` - Configuration loading
2. Implement `commands/lib/utils.py` - Common utilities
3. Implement `commands/lib/session.py` - Session metadata and state detection
4. Implement `commands/ao-status` - Test with bash-created sessions
5. Implement `commands/ao-list-sessions` - Test listing
6. Implement `commands/ao-show-config` - Test config display

### Phase 2: Agent Loading
1. Implement `commands/lib/agent.py` - Agent configuration loading
2. Implement `commands/ao-list-agents` - Test agent listing

### Phase 3: Claude SDK Integration
1. Implement `commands/lib/claude_client.py` - SDK wrapper
2. Test basic session creation (no agent)
3. Validate `.jsonl` output format matches bash

### Phase 4: Write Operations
1. Implement `commands/ao-new` - Create new sessions
2. Implement `commands/ao-resume` - Resume sessions
3. Implement `commands/ao-get-result` - Extract results
4. Implement `commands/ao-clean` - Remove sessions

### Phase 5: Testing & Validation
1. Test interface compatibility (CLI parameters, environment variables)
2. Document file format divergence
3. Update user documentation

## Key Files

- **Bash Reference**: `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh`
- **Architecture Plan**: `ARCHITECTURE_PLAN.md` (comprehensive implementation guidance)
- **SDK Investigation**: `CLAUDE_SDK_INVESTIGATION.md` (SDK capabilities analysis)
- **Legacy Docs**: `docs/architecture.md`, `docs/development.md`, `docs/llm-prompts.md`

## Compatibility Model

**Interface Compatibility** (✅ MAINTAINED):
- Command names: `ao-new`, `ao-resume`, `ao-status`, etc. map to bash `new`, `resume`, `status`
- CLI parameters: `--sessions-dir`, `--agents-dir`, `--project-dir`, `-p` are identical
- Environment variables: 100% identical naming and behavior
  - `AGENT_ORCHESTRATOR_PROJECT_DIR`
  - `AGENT_ORCHESTRATOR_SESSIONS_DIR`
  - `AGENT_ORCHESTRATOR_AGENTS_DIR`
  - `AGENT_ORCHESTRATOR_ENABLE_LOGGING`
- Agent structure: `agent.json`, `agent.system-prompt.md`, `agent.mcp.json` (unchanged)

**File Format Divergence** (⚠️ INTENTIONAL):
- Python uses SDK-native `.jsonl` format (dataclass serialization)
- Bash uses CLI subprocess `.jsonl` format
- **Sessions are NOT cross-compatible** - Python sessions cannot be resumed by bash and vice versa
- **This is by design** - Python SDK provides superior error handling and type safety
- Each tool operates independently on its own session files

## Why This Matters

Progressive disclosure enables token-efficient LLM workflows. Instead of loading all commands upfront, LLMs discover → detail → execute progressively, ideal for Claude Code skills pattern.

---

**Current Status**: Architecture planning complete. Ready to begin Phase 1 implementation starting with `commands/lib/config.py`.

**Key Documents**:
- `ARCHITECTURE_PLAN.md` - Complete implementation guidance with detailed hints
- `CLAUDE_SDK_INVESTIGATION.md` - SDK capabilities and usage patterns
