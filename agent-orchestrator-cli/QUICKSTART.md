# Quick Start Guide

## What You Have

A complete **stub/template** implementation of the Agent Orchestrator CLI with:

✅ **8 command scripts** (`bin/ao-*`) - Executable, self-documenting stubs
✅ **5 shared modules** (`lib/*.py`) - Function stubs with TODOs
✅ **Progressive disclosure architecture** - Optimized for LLM workflows
✅ **Complete documentation** - Architecture and development guides

## Next Steps

### 1. Test the Structure

```bash
cd agent-orchestrator-cli

# Verify commands are executable
./bin/ao-new --help

# Should show: Help text from typer (once uv downloads dependencies)
```

### 2. Choose Implementation Approach

**Option A: Implement Everything Yourself**
- Follow `docs/development.md` for implementation order
- Each stub has TODO comments showing what to implement
- Reference bash script for behavior

**Option B: LLM-Assisted Implementation**
- Give LLM context: architecture docs + bash script
- Implement module by module (see Phase 1-5 in development.md)
- Each module is small and focused

**Option C: Hybrid (Recommended)**
- Implement core utilities yourself (config, utils)
- Use LLM for repetitive patterns (commands)
- Review and test all LLM output

### 3. Start with Core Infrastructure

```bash
# Implement in this order:
1. lib/config.py - Configuration loading
2. lib/utils.py - Basic utilities
3. lib/session.py - Session validation
```

Then test:
```bash
python -c "import sys; sys.path.insert(0, 'lib'); from config import load_config; print('OK')"
```

### 4. Implement Simple Commands First

```bash
# Start with read-only commands:
1. bin/ao-status
2. bin/ao-list-sessions
3. bin/ao-list-agents
```

Test each:
```bash
./bin/ao-status --help
./bin/ao-status testsession  # Should handle gracefully
```

### 5. Add Claude Integration

```bash
# Complex commands:
1. lib/claude_client.py
2. bin/ao-new
3. bin/ao-resume
```

## How Progressive Disclosure Works

### Traditional CLI (Token Heavy)
```
LLM loads: All 8 commands × all parameters = 500+ tokens
```

### Progressive CLI (Token Efficient)
```
Step 1: LLM sees command list (50 tokens)
Step 2: LLM calls ao-new --help (50 tokens)
Step 3: LLM executes ao-new ... (50 tokens)
Total: 150 tokens
```

**70% reduction in context!**

## Key Design Decisions

### Why Split Commands?
- **Token efficiency**: Load details only when needed
- **Extensibility**: New commands don't increase baseline context
- **LLM-friendly**: Smaller files easier to understand and modify
- **Maintainability**: Clear boundaries, focused responsibility

### Why uv?
- **Self-contained**: No separate virtualenv needed
- **Fast**: Quick startup for short-lived scripts
- **Dependencies**: Easy to specify per-script requirements
- **Modern**: Embraces latest Python tooling

### Why Shared `lib/`?
- **DRY principle**: Don't repeat configuration logic
- **Consistency**: All commands use same validation
- **Testability**: Can test modules independently
- **Evolution**: Easy to refactor shared code

## Usage Pattern for LLMs

When integrated with Claude Code or MCP:

```
1. User: "Create a new agent session"
2. LLM: Knows about ao-* commands
3. LLM: Runs `ao-new --help` to see parameters
4. LLM: Executes `ao-new mysession -p "..."`
5. User: Gets result
```

Only loads what's needed, when it's needed!

## Testing Your Implementation

```bash
# Create test project
mkdir -p /tmp/test-ao-project
cd /tmp/test-ao-project

# Add bin to PATH
export PATH="/path/to/agent-orchestrator-cli/bin:$PATH"

# Test full workflow
ao-new testsession -p "Write hello world in Python"
ao-status testsession
ao-get-result testsession
ao-list-sessions
ao-show-config testsession
ao-clean
```

## Integration Examples

### As Claude Code Skills

Create `.claude/skills/` entries:

```markdown
---
command: ao-new
description: Create new agent orchestrator session
---
Run `ao-new --help` for details.
```

### As MCP Server Tools

Expose discovery tool:

```typescript
{
  name: "list_ao_commands",
  description: "List available agent orchestrator commands",
  // Returns: ao-new, ao-resume, etc.
}

// Individual commands self-document via --help
```

### Direct CLI Usage

```bash
# Add to PATH permanently
echo 'export PATH="$PATH:/path/to/agent-orchestrator-cli/bin"' >> ~/.bashrc

# Use anywhere
ao-new mysession --agent researcher -p "Research topic"
```

## File Compatibility

All file formats match the bash script exactly:

- Session metadata: `.metadata.json`
- Session files: `session.txt`
- Agent structure: `agent.json`, `agent.system-prompt.md`, `agent.mcp.json`

You can resume sessions created by the bash script!

## Getting Help

- **Architecture**: See `docs/architecture.md`
- **Development**: See `docs/development.md`
- **Commands**: Run any `ao-* --help`
- **Bash reference**: `../agent-orchestrator/skills/agent-orchestrator/agent-orchestrator.sh`

## Current Status

```
[✅] Architecture designed
[✅] Stubs created
[✅] Documentation complete
[⏳] Implementation pending (your turn!)
```

---

**You now have a complete template for a modern, LLM-optimized CLI tool. Start implementing, and enjoy the progressive disclosure benefits!**
