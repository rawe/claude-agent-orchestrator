# Phase 3: Command Migration

## Overall Context

We are migrating the Agent Orchestrator from file-based session storage to database-backed storage via the **Agent Session Manager** service. The Python commands (`ao-*`) currently use file operations via `lib/session.py`. We're switching them to use `lib/session_client.py` for API calls.

**Strategy:** API is primary, file operations become backup/fallback.

## This Phase's Goal

Migrate the `ao-*` commands to use `SessionClient` instead of file-based operations. After this phase, commands query the database via API instead of parsing files.

## Prerequisites

- Phase 1 complete (backend API exists)
- Phase 2 complete (SessionClient exists, config updated)

## Reference

Read these sections in `analysis.md`:
- "Phase 3: Migrate Commands" - command mapping table
- "File Backup Strategy" - how to handle fallback

## Tasks

### 1. Update ao-status

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/ao-status`

Current: Uses `get_session_status()` from `session.py` (parses .jsonl file)

Change to:
```python
from config import load_config
from session_client import SessionClient

config = load_config(...)
client = SessionClient(config.session_manager_url)
status = client.get_status(session_name)  # Note: need to map session_name to session_id
print(status)
```

**Challenge:** Current commands use `session_name`, but API uses `session_id`. Options:
1. Query sessions list to find session_id by session_name
2. Add endpoint to lookup by session_name
3. Store mapping locally

**Recommendation:** Add helper method to SessionClient:
```python
def get_session_by_name(self, session_name: str) -> Optional[Dict]:
    """Find session by name. Returns None if not found."""
    sessions = self.list_sessions()
    for s in sessions:
        if s['session_name'] == session_name:
            return s
    return None
```

### 2. Update ao-get-result

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/ao-get-result`

Current: Uses `extract_result()` from `session.py` (parses last line of .jsonl)

Change to:
```python
from config import load_config
from session_client import SessionClient, SessionNotFoundError

config = load_config(...)
client = SessionClient(config.session_manager_url)

# Find session by name
session = client.get_session_by_name(session_name)
if not session:
    error_exit(f"Session '{session_name}' does not exist")

# Check status
status = client.get_status(session['session_id'])
if status == "running":
    error_exit(f"Session '{session_name}' is still running")

# Get result
result = client.get_result(session['session_id'])
print(result)
```

### 3. Update ao-list-sessions

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/ao-list-sessions`

Current: Uses `list_all_sessions()` from `session.py` (globs .meta.json files)

Change to:
```python
from config import load_config
from session_client import SessionClient

config = load_config(...)
client = SessionClient(config.session_manager_url)
sessions = client.list_sessions()

if not sessions:
    print("No sessions found")
else:
    for s in sessions:
        print(f"{s['session_name']} (session-id: {s['session_id']}, project-dir: {s.get('project_dir', 'unknown')})")
```

### 4. Update ao-clean

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/ao-clean`

Current: Deletes files directly

Change to:
```python
from config import load_config
from session_client import SessionClient

config = load_config(...)
client = SessionClient(config.session_manager_url)

# Find session by name
session = client.get_session_by_name(session_name)
if not session:
    error_exit(f"Session '{session_name}' does not exist")

# Delete via API
deleted = client.delete_session(session['session_id'])

# Also delete backup files if they exist
# (keep file deletion as cleanup)
```

### 5. Error Handling Pattern

Use this pattern for all commands:

```python
from session_client import SessionClient, SessionClientError, SessionNotFoundError

try:
    client = SessionClient(config.session_manager_url)
    # ... API calls ...
except SessionNotFoundError:
    # Handle not found
    error_exit(f"Session '{session_name}' does not exist")
except SessionClientError as e:
    # API error - could fall back to file-based
    print(f"Warning: API error: {e}", file=sys.stderr)
    # Optionally fall back to file-based operation
```

### 6. Do NOT Migrate Yet

These commands will be migrated in Phase 4:
- `ao-new` - requires event flow changes
- `ao-resume` - requires event flow changes

## Success Criteria

1. `ao-status` returns status from API
2. `ao-get-result` returns result from API
3. `ao-list-sessions` lists sessions from API
4. `ao-clean` deletes via API
5. All commands handle API errors gracefully
6. Commands still work if session exists only in files (fallback)

## Verification

```bash
# Ensure backend is running
cd agent-orchestrator-observability/backend && uv run python main.py &

# Create a test session via API
curl -X POST http://localhost:8765/sessions \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-789", "session_name": "test-session", "project_dir": "/tmp"}'

# Add a message event (so result exists)
curl -X POST http://localhost:8765/sessions/test-789/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "message", "session_id": "test-789", "session_name": "test-session", "timestamp": "2024-01-01T00:00:00Z", "role": "assistant", "content": [{"type": "text", "text": "Test result"}]}'

# Add session_stop to finish it
curl -X POST http://localhost:8765/sessions/test-789/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "session_stop", "session_id": "test-789", "session_name": "test-session", "timestamp": "2024-01-01T00:00:01Z", "exit_code": 0, "reason": "completed"}'

# Test commands
cd plugins/agent-orchestrator/skills/agent-orchestrator/commands

./ao-list-sessions
# Should show test-session

./ao-status test-session
# Should show: finished

./ao-get-result test-session
# Should show: Test result

./ao-clean test-session
# Should delete
```

## Notes

- Keep imports from `session.py` for now - they're used by ao-new/ao-resume
- Don't remove any file-based code yet
- Focus on making API the primary path, files as fallback

## Guidelines

- **Follow the instructions above** - do not add features beyond what is specified
- **Embrace KISS** - keep implementations simple and straightforward
- **Embrace YAGNI** - do not build for hypothetical future requirements
- **Ask if there is any confusion** before proceeding with implementation
