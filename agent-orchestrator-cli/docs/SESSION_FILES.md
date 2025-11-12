# Session Files and Status Detection

## Session Directory Location

### Default Location
```
{project_dir}/.agent-orchestrator/agent-sessions/
```

Where `{project_dir}` defaults to your current working directory (PWD).

### Configuration Precedence

The session directory can be configured using (highest to lowest priority):

1. **CLI Parameter**: `--sessions-dir /path/to/sessions`
2. **Environment Variable**: `AGENT_ORCHESTRATOR_SESSIONS_DIR`
3. **Default**: `{project_dir}/.agent-orchestrator/agent-sessions/`

### Project Directory Configuration

The project directory can also be configured:

1. **CLI Parameter**: `--project-dir /path/to/project`
2. **Environment Variable**: `AGENT_ORCHESTRATOR_PROJECT_DIR`
3. **Default**: Current working directory (PWD)

### Examples

**Default (relative to PWD):**
```bash
# If you're in /home/user/myproject/
# Sessions are stored in: /home/user/myproject/.agent-orchestrator/agent-sessions/
ao-new mysession -p "Hello"
```

**Custom sessions directory:**
```bash
# Override with CLI parameter
ao-new mysession --sessions-dir /tmp/sessions -p "Hello"

# Or set environment variable
export AGENT_ORCHESTRATOR_SESSIONS_DIR=/tmp/sessions
ao-new mysession -p "Hello"
```

---

## File Naming Convention

Each session creates **two files** in the sessions directory:

### 1. Metadata File: `{session-name}.meta.json`
```
.agent-orchestrator/agent-sessions/mysession.meta.json
```

**Purpose**: Stores session configuration and metadata

**Structure**:
```json
{
  "session_name": "mysession",
  "session_id": "c68eb198-b150-4ecd-a249-501f82bb1649",
  "agent": null,
  "project_dir": "/Users/you/project",
  "agents_dir": "/Users/you/project/.agent-orchestrator/agents",
  "created_at": "2025-11-12T15:54:52.399854Z",
  "last_resumed_at": "2025-11-12T15:54:52.399854Z",
  "schema_version": "1.0"
}
```

### 2. Session File: `{session-name}.jsonl`
```
.agent-orchestrator/agent-sessions/mysession.jsonl
```

**Purpose**: Stores conversation history (JSONL format - one JSON object per line)

**Contains**: User messages, Claude responses, tool calls, and results

See [JSONL_FORMAT.md](JSONL_FORMAT.md) for detailed message structure.

---

## Session Status Detection

### Three Statuses

| Status | Meaning |
|--------|---------|
| `not_existent` | Session doesn't exist |
| `running` | Session in progress |
| `finished` | Session completed with result |

### Detection Algorithm

```
┌─────────────────────────────────┐
│ 1. Check .meta.json exists?     │
│    NO  → "not_existent"          │
│    YES → Continue...             │
└─────────────────────────────────┘
         ↓
┌─────────────────────────────────┐
│ 2. Check .jsonl exists AND      │
│    has content (size > 0)?      │
│    NO  → "running"               │
│    YES → Continue...             │
└─────────────────────────────────┘
         ↓
┌─────────────────────────────────┐
│ 3. Read last line of .jsonl     │
│    Has "subtype": "success"     │
│    AND "result" field?          │
│    YES → "finished"              │
│    NO  → "running"               │
└─────────────────────────────────┘
```

### Files Used for Detection

| File | Purpose in Status Detection |
|------|----------------------------|
| `.meta.json` | Determines if session exists |
| `.jsonl` | Last line determines if session completed |

### Example Status Checks

```bash
# Check if session exists and its status
ao-status mysession
# Output: "not_existent", "running", or "finished"

# Get result only works for finished sessions
ao-get-result mysession
# Error if session is "running" or "not_existent"
```

---

## Complete File Structure Example

```
myproject/
├── .agent-orchestrator/
│   ├── agent-sessions/           ← Session files
│   │   ├── mysession.meta.json   ← Session metadata
│   │   ├── mysession.jsonl       ← Conversation history
│   │   ├── debug-001.meta.json
│   │   └── debug-001.jsonl
│   └── agents/                   ← Agent definitions
│       ├── researcher/
│       └── coder/
└── your-code-here/
```

---

## Session Lifecycle

### 1. Creating a Session (`ao-new`)

**Before Claude runs:**
- Creates `{session-name}.meta.json` (without `session_id`)
- Status: `running` (no .jsonl yet)

**During Claude execution:**
- Creates `{session-name}.jsonl` with messages
- Updates `.meta.json` with `session_id` (from SDK)
- Status: `running`

**After completion:**
- Last line of `.jsonl` has result message
- Status: `finished`

### 2. Resuming a Session (`ao-resume`)

**Requirements:**
- `.meta.json` must exist
- `.meta.json` must contain `session_id`

**Process:**
- Reads `session_id` from `.meta.json`
- Appends new messages to `.jsonl`
- Updates `last_resumed_at` in `.meta.json`

### 3. Reading Results (`ao-get-result`)

**Requirements:**
- Session status must be `finished`

**Process:**
- Reads last line of `.jsonl`
- Extracts `result` field
- Prints to stdout

---

## Environment Variables Reference

| Variable | Purpose | Default |
|----------|---------|---------|
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | Base project directory | Current directory (PWD) |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | Where sessions are stored | `{project_dir}/.agent-orchestrator/agent-sessions` |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | Where agent definitions are stored | `{project_dir}/.agent-orchestrator/agents` |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | Enable command logging (`1`/`true`/`yes`) | Disabled |

---

## Common Issues

### "Session not found"
**Cause**: Wrong sessions directory
**Solution**: Check with `ao-show-config {session-name}` or verify `--sessions-dir` parameter

### "Session is still running"
**Cause**: `.jsonl` file doesn't have result message yet
**Solution**: Wait for session to complete or check actual file contents

### "No result found"
**Cause**: Last line of `.jsonl` doesn't have `"subtype": "success"` + `"result"`
**Solution**: Session may have errored - check `.jsonl` contents manually
