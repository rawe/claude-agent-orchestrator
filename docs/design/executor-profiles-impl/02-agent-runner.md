# Session 2: Agent Runner

**Component:** `servers/agent-runner/`

## Objective

Add profile loading infrastructure, update the invocation schema to 2.1, implement `--profile` CLI flag, and update registration to send the new fields.

## Prerequisites

- **Session 1 complete**: Executor can read `executor_config`

## Files to Modify

| File | Change |
|------|--------|
| `lib/invocation.py` | Bump schema to 2.1, add `executor_config` field |
| `lib/executor.py` | Add profile loading functions |
| `agent-runner` | Add `--profile`, `--profile-list`, `--require-matching-tags` flags |
| `profiles/` | **NEW** directory with example profile JSON files |

## Key Changes

### 1. Invocation Schema (lib/invocation.py)

```python
SCHEMA_VERSION = "2.1"  # Was 2.0

@dataclass
class ExecutorInvocation:
    # ... existing fields ...
    executor_config: Optional[dict[str, Any]] = None  # NEW
```

### 2. Profile Loading (lib/executor.py)

Add profile infrastructure:

```python
DEFAULT_EXECUTOR_PATH = "executors/claude-code/ao-claude-code-exec"
DEFAULT_EXECUTOR_TYPE = "claude-code"

@dataclass
class ExecutorProfile:
    name: str           # "coding"
    type: str           # "claude-code"
    command: str        # "executors/claude-code/ao-claude-code-exec"
    config: dict        # { permission_mode: "...", ... }

def list_profiles() -> list[str]: ...
def load_profile(name: str) -> ExecutorProfile: ...
```

See design doc lines 532-602 for full implementation.

### 3. CLI Changes (agent-runner)

| Flag | Behavior |
|------|----------|
| `--profile <name>` | Load `profiles/<name>.json`. **Fail if not found.** |
| No `--profile` | Use hardcoded default (`claude-code`), no config |
| `--profile-list` | List available profiles and exit |
| `--require-matching-tags` | Only accept runs with matching tags |

**Remove these flags:**
- `--executor` (replaced by `--profile`)
- `--executor-path` (removed)
- `--executor-list` (replaced by `--profile-list`)

### 4. Registration Payload

Update what gets sent to coordinator:

```json
{
  "hostname": "...",
  "project_dir": "...",
  "executor_profile": "coding",
  "executor": {
    "type": "claude-code",
    "command": "executors/claude-code/ao-claude-code-exec",
    "config": { "permission_mode": "bypassPermissions", ... }
  },
  "tags": ["python"],
  "require_matching_tags": false
}
```

**Without --profile (default):**
```json
{
  "executor_profile": "claude-code",
  "executor": { "type": "claude-code", "command": "...", "config": {} }
}
```

### 5. Create Profiles Directory

```
servers/agent-runner/profiles/
├── coding.json
├── research.json
└── supervised.json
```

See design doc lines 489-528 for example profile contents.

## Design Doc References

- **Profile file format**: lines 56-86
- **Runner CLI**: lines 89-128
- **One Profile Per Runner**: lines 140-147
- **Invocation Schema**: lines 149-176
- **Profile Loading implementation**: lines 532-602
- **Registration payload**: lines 195-236
- **Flow Diagrams**: lines 364-487

## Backward Compatibility

When no `--profile` flag is provided:
1. Use hardcoded default executor path
2. No config passed (executor uses its internal defaults)
3. Register as `executor_profile: "claude-code"`

This ensures existing deployments work without changes.

## Testing

```bash
# List profiles
./servers/agent-runner/agent-runner --profile-list

# Start with profile (should fail - coordinator not updated yet)
./servers/agent-runner/agent-runner --profile coding --project-dir /tmp/test

# Start without profile (backward compat - should work)
./servers/agent-runner/agent-runner --project-dir /tmp/test
```

Verify:
- Profile loading works (reads JSON, validates fields)
- Missing profile = clear error with available profiles listed
- Default behavior unchanged when no --profile
- Invocation payload includes `executor_config` when profile has config

## Definition of Done

- [ ] `lib/invocation.py`: Schema 2.1 with `executor_config` field
- [ ] `lib/executor.py`: `load_profile()`, `list_profiles()`, `ExecutorProfile` dataclass
- [ ] CLI: `--profile`, `--profile-list`, `--require-matching-tags` flags
- [ ] CLI: Removed `--executor`, `--executor-path`, `--executor-list`
- [ ] `profiles/` directory with 3 example profiles
- [ ] Registration sends `executor_profile` + `executor` object
- [ ] Backward compatible when no --profile flag

## Note on Integration

After this session, the Runner will send `executor_profile` instead of `executor_type`. The Coordinator (Session 3) must be updated to accept this. Until then, registration may fail or ignore the new fields.
