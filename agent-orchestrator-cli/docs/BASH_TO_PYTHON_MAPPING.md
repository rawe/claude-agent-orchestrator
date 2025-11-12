# Bash to Python Migration Guide

**Target Audience**: Developers who previously integrated with `agent-orchestrator.sh` and need to migrate to Python commands.

---

## Command Migration

Replace bash script calls with Python command equivalents:

| Before (Bash) | After (Python) |
|---------------|----------------|
| `./agent-orchestrator.sh new ...` | `ao-new ...` |
| `./agent-orchestrator.sh resume ...` | `ao-resume ...` |
| `./agent-orchestrator.sh status ...` | `ao-status ...` |
| `./agent-orchestrator.sh get-result ...` | `ao-get-result ...` |
| `./agent-orchestrator.sh list` | `ao-list-sessions` |
| `./agent-orchestrator.sh list-agents` | `ao-list-agents` |
| `./agent-orchestrator.sh show-config ...` | `ao-show-config ...` |
| `./agent-orchestrator.sh clean` | `ao-clean` |

---

## What Stays the Same

### ✅ CLI Parameters (100% Compatible)

All flags and parameters work identically:

```bash
# Bash
./agent-orchestrator.sh new my-session --agent researcher -p "Query" --sessions-dir /custom

# Python (same parameters)
ao-new my-session --agent researcher -p "Query" --sessions-dir /custom
```

**Available parameters**: `--sessions-dir`, `--agents-dir`, `--project-dir`, `-p/--prompt`, `--agent`

### ✅ Environment Variables (100% Compatible)

```bash
export AGENT_ORCHESTRATOR_PROJECT_DIR=/my/project
export AGENT_ORCHESTRATOR_SESSIONS_DIR=/custom/sessions
export AGENT_ORCHESTRATOR_AGENTS_DIR=/custom/agents
export AGENT_ORCHESTRATOR_ENABLE_LOGGING=true

# Both bash and Python respect these variables
```

### ✅ Agent Definitions (100% Compatible)

Agent directory structure is identical:

```
agents/my-agent/
├── agent.json              # Required: name, description
├── agent.system-prompt.md  # Optional: system prompt
└── agent.mcp.json          # Optional: MCP servers config
```

Both tools read the same agent definitions - no changes needed.

### ✅ Behavior (100% Compatible)

- Exit codes match (0 = success, 1 = error)
- Error messages formatted similarly
- Validation rules identical (session names, etc.)
- Configuration precedence: CLI > ENV > DEFAULT

---

## What Changes

### ⚠️ Session Files (NOT Compatible)

**Critical**: Python and bash sessions are **separate and incompatible**.

```bash
# ❌ This will NOT work:
./agent-orchestrator.sh new my-session -p "Start"  # Creates bash session
ao-resume my-session                                # Cannot resume bash session

# ✅ This works:
ao-new my-session -p "Start"                        # Creates Python session
ao-resume my-session                                # Resumes Python session
```

**Why?** Python uses Claude Agent SDK (native format), bash uses `claude` CLI (different format).

**Solution**: Choose one tool and stick with it. Don't mix bash and Python for the same session.

### 📁 File Format Differences

| File | Bash Format | Python Format | Impact |
|------|-------------|---------------|--------|
| `.jsonl` | CLI subprocess output | SDK dataclass serialization | Cannot parse across tools |
| `.meta.json` | Schema v1.0 | Schema v2.0, adds `last_resumed_at` | Minor structural differences |

**Practical impact**: Use separate `--sessions-dir` if running both tools:

```bash
# Bash sessions
export AGENT_ORCHESTRATOR_SESSIONS_DIR=~/.ao/bash-sessions

# Python sessions
export AGENT_ORCHESTRATOR_SESSIONS_DIR=~/.ao/python-sessions
```

---

## Migration Examples

### Example 1: Basic Session Creation

**Before:**
```bash
./agent-orchestrator.sh new research-task -p "Research topic X"
```

**After:**
```bash
ao-new research-task -p "Research topic X"
```

### Example 2: With Agent

**Before:**
```bash
./agent-orchestrator.sh new analysis --agent data-analyst -p "Analyze dataset"
```

**After:**
```bash
ao-new analysis --agent data-analyst -p "Analyze dataset"
```

### Example 3: Environment Variables

**Before:**
```bash
export AGENT_ORCHESTRATOR_SESSIONS_DIR=/project/sessions
./agent-orchestrator.sh list
```

**After:**
```bash
export AGENT_ORCHESTRATOR_SESSIONS_DIR=/project/sessions
ao-list-sessions
```

### Example 4: Stdin Input

**Before:**
```bash
echo "Complex prompt text" | ./agent-orchestrator.sh new task
```

**After:**
```bash
echo "Complex prompt text" | ao-new task
```

---

## MCP Integration Notes

If you're integrating with MCP (Model Context Protocol):

### Agent MCP Configuration (Unchanged)

The `agent.mcp.json` file structure is **identical**:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-package"],
      "env": {"API_KEY": "value"}
    }
  }
}
```

### How It Works

Both tools:
1. Read `agents/{agent-name}/agent.mcp.json`
2. Parse the JSON structure
3. Pass MCP servers to Claude

**Difference**: Internal implementation (file path vs parsed dict), but from your perspective as a user, it's transparent.

---

## Testing Your Migration

Run the interface compatibility tests:

```bash
cd agent-orchestrator-cli
./test_interface_compatibility.sh
```

This verifies:
- Environment variables work identically
- CLI parameters work identically
- Agent structure is compatible

---

## Quick Migration Checklist

- [ ] Replace `./agent-orchestrator.sh` calls with `ao-*` commands
- [ ] Keep all CLI parameters unchanged (they work the same)
- [ ] Keep all environment variables unchanged (they work the same)
- [ ] Keep agent definitions unchanged (they work the same)
- [ ] Decide: migrate all sessions to Python OR run tools separately
- [ ] If running both: use separate `--sessions-dir` for each tool
- [ ] Test with `./test_interface_compatibility.sh`

---

## Summary

| Aspect | Compatibility | Action Required |
|--------|---------------|-----------------|
| Command names | Different names, same function | Update script calls |
| CLI parameters | 100% identical | None - works as-is |
| Environment variables | 100% identical | None - works as-is |
| Agent definitions | 100% identical | None - works as-is |
| Session files | Incompatible | Don't mix bash/Python sessions |

**Bottom line**: Update command names, everything else just works. Keep sessions separate.
