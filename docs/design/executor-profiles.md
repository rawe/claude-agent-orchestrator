# Executor Profiles

**Status:** Draft
**Date:** 2025-01-03

## Problem Statement

The Agent Orchestrator's executor system has two limitations:

1. **No executor configuration** - Settings like `permission_mode`, `setting_sources`, and `model` are hardcoded in each executor implementation. Different use cases require different configurations.

2. **Tight coupling** - The executor type (e.g., `claude-code`) is both an implementation detail and the coordination identifier. This prevents having multiple configurations of the same executor.

### Examples

| Use Case | Executor | Configuration Need |
|----------|----------|-------------------|
| Autonomous coding | claude-code | `permission_mode: bypassPermissions`, `model: opus` |
| Supervised editing | claude-code | `permission_mode: acceptEdits`, `model: sonnet` |
| Research tasks | claude-code | `permission_mode: default`, `setting_sources: [project]` |
| Fast prototyping | openai-codex | `model: gpt-4-turbo`, `temperature: 0.3` |

Today, all Claude Code runs use identical hardcoded settings. We need a way to configure executors without modifying their code.

## Design Principles

### Knowledge Boundary

Clear separation between coordinator and runner responsibilities:

| Component | Knows | Uses For Decisions | Doesn't Know |
|-----------|-------|-------------------|--------------|
| **Coordinator** | Profile name, executor details | Profile name only (demand matching) | How to interpret executor config |
| **Agent Runner** | Profile name → (type, config) | Executor resolution, config passing | How config is applied |
| **Executor** | Config values | Applying configuration | Profile name, where config came from |
| **Agent Blueprint** | Profile name (via demands) | Demand matching | Executor type, config |

The coordinator receives executor details during registration for **observability only** (API responses, dashboard). It uses only the profile name for demand matching. The runner is the sole interpreter of what a profile means.

Agent blueprints specify `executor_profile` in their demands to route runs to runners with matching profiles.

### Backward Compatibility

When no `--profile` flag is provided, the runner uses a hardcoded default:
- Executor: `executors/claude-code/ao-claude-code-exec`
- No config passed to executor
- Executor uses its internal hardcoded defaults
- Registers with coordinator as `executor_profile: "claude-code"`

This ensures existing deployments work without changes.

## Design

### Executor Profiles

A profile bundles an executor type with its configuration:

```
servers/agent-runner/profiles/
├── coding.json
├── research.json
└── supervised.json
```

**Profile file format:**

```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "bypassPermissions",
    "setting_sources": ["project", "local"],
    "model": "opus"
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Executor type name (for coordinator visibility, e.g., `claude-code`) |
| `command` | Yes | Relative path from agent-runner to executor script |
| `config` | No | Executor-specific configuration (passed as-is). If omitted, executor uses its internal defaults. |

The `command` field explicitly specifies which executor script to run. No path resolution or convention-based lookup is needed.

### Runner CLI

The `--profile` parameter selects an executor profile:

```bash
# Use profile "coding" (loads profiles/coding.json)
./agent-runner --profile coding

# Use profile "research"
./agent-runner --profile research

# List available profiles
./agent-runner --profile-list
```

**Behavior:**

| Flag | Behavior |
|------|----------|
| `--profile <name>` | Load `profiles/<name>.json`. **Fail if not found.** |
| No `--profile` | Use hardcoded default executor (`claude-code`), no config. |
| `--profile-list` | List available profiles and exit. |

```
--profile coding
    ↓
profiles/coding.json exists?
    ├── Yes → Load profile → command: "executors/claude-code/ao-claude-code-exec"
    │                      → config: { permission_mode: "bypassPermissions", ... }
    │
    └── No → ERROR: Profile 'coding' not found. Available: research, supervised
             Runner does not start.
```

```
(no --profile flag)
    ↓
Use hardcoded default:
    → Executor: executors/claude-code/ao-claude-code-exec
    → Config: None (executor uses its internal defaults)
    → Register with coordinator as executor_profile: "claude-code"
```

**Removed CLI options:**
- `--executor` - Replaced by `--profile`
- `--executor-path` - Removed entirely
- `--executor-list` - Replaced by `--profile-list`

### One Profile Per Runner

Each runner instance supports exactly one executor profile:

```bash
# Runner for autonomous coding tasks
./agent-runner --profile coding --project-dir /workspace/coding

# Runner for supervised editing (separate instance)
./agent-runner --profile supervised --project-dir /workspace/editing
```

The coordinator routes runs to the appropriate runner based on profile name matching (via existing demand system).

### Invocation Schema

When a profile provides config, it's passed to the executor in the invocation payload. This extends the existing schema with an optional `executor_config` field:

```json
{
  "schema_version": "2.1",
  "mode": "start",
  "session_id": "ses_abc123",
  "prompt": "...",
  "project_dir": "/path/to/project",
  "agent_blueprint": { ... },
  "executor_config": {
    "permission_mode": "bypassPermissions",
    "setting_sources": ["project", "local"],
    "model": "opus"
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `executor_config` | No | Executor-specific configuration from profile. If omitted, executor uses its internal defaults. |

The profile name is **not** included—it's transparent to the executor.

**Note:** This bumps the schema version from 2.0 to 2.1. No backwards compatibility with 2.0 is maintained; all components are updated together.

### Executor Config Handling

Each executor reads `executor_config` and applies it with fallback to defaults:

```python
# In ao-claude-code-exec
def get_config(invocation: ExecutorInvocation) -> dict:
    config = invocation.executor_config or {}
    return {
        "permission_mode": config.get("permission_mode", "bypassPermissions"),
        "setting_sources": config.get("setting_sources", ["user", "project", "local"]),
        "model": config.get("model"),  # None = use SDK default
    }
```

Unknown config keys are ignored (forward compatibility).

### Registration

Runner registers with coordinator, providing both the profile name and full executor details:

**Registration payload:**
```json
POST /runner/register {
  "hostname": "dev-machine",
  "project_dir": "/workspace",
  "tags": ["python", "docker"],
  "executor_profile": "coding",
  "executor": {
    "type": "claude-code",
    "command": "executors/claude-code/ao-claude-code-exec",
    "config": {
      "permission_mode": "bypassPermissions",
      "setting_sources": ["project", "local"],
      "model": "opus"
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `executor_profile` | Profile name used for demand matching (e.g., "coding") |
| `executor` | Exact content of the profile JSON (no transformation) |

The `executor` object is passed through as-is from the profile file. No abstraction or mapping needed.

**Without profile (default executor):**
```json
POST /runner/register {
  "hostname": "dev-machine",
  "project_dir": "/workspace",
  "executor_profile": "claude-code",
  "executor": {
    "type": "claude-code",
    "command": "executors/claude-code/ao-claude-code-exec",
    "config": {}
  }
}
```

### Coordinator Behavior

The coordinator stores executor details but does **not** interpret them:

| Field | Coordinator Uses For |
|-------|---------------------|
| `executor_profile` | Demand matching (routing runs to runners) |
| `executor` | Stored and exposed via API (observability only) |

**Boundary principle:** The coordinator treats `executor` as an opaque JSON object. It:
- Stores it in the runner record
- Returns it in API responses (e.g., runner list, runner details)
- Displays it in the dashboard for visibility
- Does **NOT** use `executor.type` or `executor.config` for any decisions

This separation ensures:
1. Coordinator remains executor-agnostic
2. Dashboard can show executor details for operators
3. Future executor types require no coordinator changes

### Demand Matching

The existing demand system routes runs to runners. Profile name replaces executor type in the demands:

**Current demand properties (ADR-011):**

| Property | Match Type | Change |
|----------|------------|--------|
| `hostname` | Exact match | No change |
| `project_dir` | Exact match | No change |
| `executor_type` | Exact match | **Renamed to `executor_profile`** |
| `tags` | Runner must have ALL | No change |

**Blueprint demands example:**

```json
{
  "name": "web-researcher",
  "description": "Research agent",
  "demands": {
    "executor_profile": "coding",
    "tags": ["python", "playwright"]
  },
  "system_prompt": "..."
}
```

**Matching flow:**

```
Blueprint demands: { executor_profile: "coding", tags: ["python"] }
                    ↓
Runner capabilities: { executor_profile: "coding", tags: ["python", "docker"] }
                    ↓
Match! Run assigned to this runner.
```

### Tagged-Only Mode

Runners can optionally protect themselves from executing untagged or unrelated runs. When enabled, the runner rejects runs that don't share at least one tag with the runner.

**Note:** This is distinct from demand-based tag matching (ADR-011), where runs demand capabilities from runners. Tagged-Only Mode is the inverse—runners filtering which runs they will accept.

**CLI flag:**
```bash
./agent-runner --profile coding --require-matching-tags
```

**Registration payload:**
```json
POST /runner/register {
  "hostname": "dev-machine",
  "project_dir": "/workspace",
  "executor_profile": "coding",
  "executor": { ... },
  "tags": ["python", "docker"],
  "require_matching_tags": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `require_matching_tags` | boolean | `false` | If `true`, only accept runs with at least one tag matching the runner's tags |

**Behavior:**

| Runner Tags | Run Tags | `require_matching_tags` | Result |
|-------------|----------|------------------------|--------|
| `["python", "docker"]` | `["python"]` | `true` | ✓ Match (python matches) |
| `["python", "docker"]` | `["nodejs"]` | `true` | ✗ No match |
| `["python", "docker"]` | `[]` (no tags) | `true` | ✗ Rejected (run has no tags) |
| `["python", "docker"]` | `[]` (no tags) | `false` | ✓ Accepted (default behavior) |

**Design decision:** We require at least one matching tag (not all). This allows a runner with `["python", "docker"]` to accept runs tagged `["python"]` without requiring `["docker"]`. An alternative would be requiring all runner tags to be present in the run's tags—this remains open for reconsideration based on real-world usage.

> **TODO:** When implementing this feature, create an ADR to formalize the Tagged-Only Mode design decision.

**Coordinator impact:** The runner selection algorithm must incorporate this field when matching runs to runners. A runner with `require_matching_tags: true` should be excluded from candidates if the run has no tags or no matching tags.

## File Structure

```
servers/agent-runner/
├── agent-runner                    # Main entry point (CLI with --profile flag)
├── profiles/                       # NEW: Executor profiles
│   ├── coding.json
│   ├── research.json
│   └── supervised.json
├── executors/                      # Executor implementations
│   ├── claude-code/
│   │   ├── ao-claude-code-exec     # Default executor (used when no --profile)
│   │   └── lib/
│   ├── openai-codex/               # Future
│   │   └── ao-openai-codex-exec
│   └── deterministic/              # Future
│       └── ao-deterministic-exec
└── lib/
    ├── executor.py                 # Profile loading + executor resolution
    ├── invocation.py               # Schema 2.1 with executor_config
    └── ...
```

## Flow Diagrams

### With Profile

```
┌─────────────────────────────────────────────────────────────────┐
│  Runner Startup                                                 │
│                                                                 │
│  ./agent-runner --profile coding                                │
│                                                                 │
│  1. Load profiles/coding.json                                   │
│     {                                                           │
│       "type": "claude-code",                                    │
│       "command": "executors/claude-code/ao-claude-code-exec",   │
│       "config": { ... }                                         │
│     }                                                           │
│                                                                 │
│  2. Use command path directly (no resolution needed)            │
│                                                                 │
│  3. Register with coordinator:                                  │
│     POST /runner/register {                                     │
│       executor_profile: "coding",                               │
│       executor: { type: "claude-code", config: {...} }          │
│     }                                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Run Execution                                                  │
│                                                                 │
│  1. Runner claims run (executor_profile matches "coding")       │
│                                                                 │
│  2. Build invocation payload:                                   │
│     {                                                           │
│       "schema_version": "2.1",                                  │
│       "executor_config": {        ← From profile                │
│         "permission_mode": "bypassPermissions",                 │
│         "setting_sources": ["project", "local"],                │
│         "model": "opus"                                         │
│       },                                                        │
│       "agent_blueprint": { ... }                                │
│     }                                                           │
│                                                                 │
│  3. Spawn executor: uv run --script ao-claude-code-exec         │
│     Pass payload via stdin                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Executor                                                       │
│                                                                 │
│  1. Parse invocation, extract executor_config                   │
│                                                                 │
│  2. Apply config:                                               │
│     options = ClaudeAgentOptions(                               │
│       permission_mode=config["permission_mode"],                │
│       setting_sources=config["setting_sources"],                │
│       model=config["model"],                                    │
│       ...                                                       │
│     )                                                           │
│                                                                 │
│  3. Run agent with configured options                           │
└─────────────────────────────────────────────────────────────────┘
```

### Without Profile (Default Executor)

```
┌─────────────────────────────────────────────────────────────────┐
│  Runner Startup                                                 │
│                                                                 │
│  ./agent-runner                    # No --profile flag          │
│                                                                 │
│  1. No profile specified                                        │
│                                                                 │
│  2. Use hardcoded default executor:                             │
│     executors/claude-code/ao-claude-code-exec                   │
│                                                                 │
│  3. No config (executor_config = None)                          │
│                                                                 │
│  4. Register with coordinator:                                  │
│     POST /runner/register {                                     │
│       executor_profile: "claude-code",                          │
│       executor: { type: "claude-code", config: {} }             │
│     }                                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Run Execution                                                  │
│                                                                 │
│  1. Build invocation payload:                                   │
│     {                                                           │
│       "schema_version": "2.1",                                  │
│       // No executor_config field                               │
│       "agent_blueprint": { ... }                                │
│     }                                                           │
│                                                                 │
│  2. Spawn executor                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Executor                                                       │
│                                                                 │
│  1. Parse invocation, executor_config is None/missing           │
│                                                                 │
│  2. Use hardcoded defaults:                                     │
│     options = ClaudeAgentOptions(                               │
│       permission_mode="bypassPermissions",  # Default           │
│       setting_sources=["user", "project", "local"],  # Default  │
│       ...                                                       │
│     )                                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Profile Not Found (Error)

```
┌─────────────────────────────────────────────────────────────────┐
│  Runner Startup                                                 │
│                                                                 │
│  ./agent-runner --profile nonexistent                           │
│                                                                 │
│  1. Look for profiles/nonexistent.json → Not found              │
│                                                                 │
│  2. ERROR: Profile 'nonexistent' not found.                     │
│     Available profiles: coding, research, supervised            │
│                                                                 │
│  3. Runner exits with error code 1                              │
└─────────────────────────────────────────────────────────────────┘
```

## Example Profiles

### coding.json
```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "bypassPermissions",
    "setting_sources": ["project", "local"],
    "model": "opus"
  }
}
```

### research.json
```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "default",
    "setting_sources": ["project"],
    "model": "sonnet"
  }
}
```

### supervised.json
```json
{
  "type": "claude-code",
  "command": "executors/claude-code/ao-claude-code-exec",
  "config": {
    "permission_mode": "acceptEdits",
    "setting_sources": ["user", "project", "local"],
    "model": "sonnet"
  }
}
```

## Implementation Changes

### 1. Profile Loading (executor.py)

```python
from dataclasses import dataclass

# Hardcoded default executor (used when no --profile flag)
DEFAULT_EXECUTOR_PATH = "executors/claude-code/ao-claude-code-exec"
DEFAULT_EXECUTOR_TYPE = "claude-code"


@dataclass
class ExecutorProfile:
    """Loaded executor profile."""
    name: str           # Profile name (e.g., "coding")
    type: str           # Executor type (e.g., "claude-code")
    command: str        # Relative path to executor script
    config: dict        # Executor-specific configuration


def list_profiles() -> list[str]:
    """List available profile names."""
    profiles_dir = get_runner_dir() / "profiles"
    if not profiles_dir.exists():
        return []
    return sorted([
        p.stem for p in profiles_dir.glob("*.json")
    ])


def load_profile(name: str) -> ExecutorProfile:
    """Load executor profile by name.

    Args:
        name: Profile name (must match profiles/<name>.json)

    Returns:
        ExecutorProfile with type, command, and config

    Raises:
        RuntimeError: If profile file not found or invalid
    """
    profile_path = get_runner_dir() / "profiles" / f"{name}.json"

    if not profile_path.exists():
        available = ", ".join(list_profiles()) or "none"
        raise RuntimeError(
            f"Profile '{name}' not found. Available: {available}"
        )

    with open(profile_path) as f:
        profile = json.load(f)

    # Validate required fields
    for field in ("type", "command"):
        if field not in profile:
            raise RuntimeError(f"Profile '{name}' missing required '{field}' field")

    # Validate command path exists
    command_path = get_runner_dir() / profile["command"]
    if not command_path.exists():
        raise RuntimeError(
            f"Profile '{name}' command not found: {profile['command']}"
        )

    return ExecutorProfile(
        name=name,
        type=profile["type"],
        command=profile["command"],
        config=profile.get("config", {}),
    )
```

### 2. Invocation Schema (invocation.py)

```python
SCHEMA_VERSION = "2.1"

@dataclass
class ExecutorInvocation:
    schema_version: str
    mode: Literal["start", "resume"]
    session_id: str
    prompt: str
    project_dir: Optional[str] = None
    agent_blueprint: Optional[dict[str, Any]] = None
    executor_config: Optional[dict[str, Any]] = None  # NEW
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 3. Executor Config Application (ao-claude-code-exec)

```python
def build_claude_options(invocation: ExecutorInvocation, ...) -> ClaudeAgentOptions:
    config = invocation.executor_config or {}

    return ClaudeAgentOptions(
        cwd=str(project_dir),
        permission_mode=config.get("permission_mode", "bypassPermissions"),
        setting_sources=config.get("setting_sources", ["user", "project", "local"]),
        model=config.get("model"),  # None = SDK default
        mcp_servers=resolved_mcp_servers,
        hooks=hooks,
        resume=resume_session_id,
    )
```

## Migration

### Rename: `executor_type` → `executor_profile`

This design renames `executor_type` to `executor_profile` across the system. This has broader implications that require analysis:

**Agent Coordinator:**
- Registration API: `executor_type` field → `executor_profile`
- Registration API: new `executor` object field
- Registration API: new `require_matching_tags` boolean field
- Runner model/storage: field rename + new fields
- Demand matching logic: property rename
- Runner selection algorithm: incorporate `require_matching_tags` logic
- API responses: all endpoints returning runner data
- Internal logic: **not fully analyzed** - there may be additional code paths using `executor_type`

**Dashboard (Frontend):**
- Runner list/details views
- Demand configuration UI
- API client types/interfaces
- **Full impact not yet analyzed** - requires codebase search

**Agent Runner:**
- Registration payload
- CLI parameter naming (already covered: `--executor` → `--profile`)

**Action required:** Before implementation, perform a comprehensive search for `executor_type` in:
1. `servers/agent-coordinator/` - all Python files
2. `dashboard/` - all TypeScript/React files
3. API schemas and OpenAPI definitions
4. Database migrations (if applicable)

This ensures no references are missed during the rename.

## References

- [ADR-010](../adr/ADR-010-session-identity-and-executor-abstraction.md) - Session Identity and Executor Abstraction
- [ADR-011](../adr/ADR-011-runner-capabilities-and-run-demands.md) - Runner Capabilities and Run Demands
- [Deterministic Task Execution](./deterministic-task-execution.md) - Related executor pattern
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk) - Configuration options for claude-code executor
