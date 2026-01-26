# MCP Resolution at Coordinator Level

**Status:** Draft
**Date:** 2026-01-27
**Prerequisite for:** [MCP Server Registry](mcp-server-registry.md)

## Overview

This document describes the architectural change required to move MCP server configuration resolution from the Runner/Executor level to the Coordinator level. This is a prerequisite for implementing the full MCP Server Registry with placeholder support.

## Goal

Include the fully resolved agent blueprint in the run payload sent to the Runner. The Runner receives a self-contained payload with no additional API calls or placeholder resolution needed (with one exception: `${runner.orchestrator_mcp_url}`).

## Current State

### Flow (Fragmented)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Agent Coordinator                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  create_run()                                                                │
│  ├─ Load agent blueprint from file                                          │
│  ├─ Merge capabilities (system_prompt, mcp_servers)                         │
│  ├─ Store Run with agent_name only (NO resolved blueprint)                  │
│  └─ Return run_id, session_id                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ Run payload (agent_name only)
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Agent Runner                                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Poller receives Run                                                         │
│  ├─ Calls GET /agents/{agent_name} to fetch agent blueprint                 │
│  ├─ BlueprintResolver resolves placeholders:                                │
│  │   ├─ ${AGENT_SESSION_ID} → session_id                                    │
│  │   └─ ${AGENT_ORCHESTRATOR_MCP_URL} → mcp_server_url                      │
│  └─ Passes partially resolved blueprint to executor                         │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ Executor invocation payload
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Claude Code Executor                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  _process_mcp_servers()                                                      │
│  ├─ Regex replacement: ${VAR} → os.environ.get(VAR)                         │
│  └─ Redundant (placeholders should already be resolved)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Run Payload Structure

What the Runner receives from `GET /runner/runs`:

```json
{
  "run_id": "run_abc123",
  "type": "start_session",
  "session_id": "ses_abc123def456",
  "agent_name": "my-agent",
  "parameters": {"prompt": "..."},
  "project_dir": "/path/to/project",
  "parent_session_id": null,
  "execution_mode": "autonomous",
  "demands": {...},
  "status": "pending"
}
```

**Problem**: No agent blueprint included. Runner must:
1. Make additional API call to fetch blueprint
2. Resolve placeholders locally

### Current Placeholder Resolution

| Placeholder | Resolved By | Location |
|-------------|-------------|----------|
| `${AGENT_SESSION_ID}` | Runner | `BlueprintResolver._resolve_blueprint()` |
| `${AGENT_ORCHESTRATOR_MCP_URL}` | Runner | `BlueprintResolver._resolve_blueprint()` |
| Any `${VAR}` | Executor | `_process_mcp_servers()` (redundant) |

### Key Files

| File | Purpose |
|------|---------|
| `servers/agent-coordinator/main.py` | `create_run()` - run creation |
| `servers/agent-coordinator/services/run_queue.py` | `Run` model definition |
| `servers/agent-runner/lib/blueprint_resolver.py` | Placeholder resolution |
| `servers/agent-runner/lib/executor.py` | `_build_payload()` - executor invocation |
| `servers/agent-runner/claude-code/lib/claude_client.py` | `_process_mcp_servers()` |

## Target State

### Placeholder Sources

With the new design, there are **5 placeholder sources**:

| Source | Syntax | Resolved By | Description |
|--------|--------|-------------|-------------|
| `params` | `${params.X}` | Coordinator | Agent input parameters |
| `scope` | `${scope.X}` | Coordinator | Run scope (LLM-invisible) |
| `env` | `${env.X}` | Coordinator | Coordinator's environment variables |
| `runtime` | `${runtime.X}` | Coordinator | Framework context (session_id, run_id) |
| `runner` | `${runner.X}` | **Runner** | Runner-specific values (orchestrator_mcp_url) |

The `runner` source is special - it contains values only the Runner knows at execution time.

### Runtime Keys (Coordinator)

| Key | Description |
|-----|-------------|
| `session_id` | Current session identifier |
| `run_id` | Current run identifier |

### Runner Keys (Runner)

| Key | Description |
|-----|-------------|
| `orchestrator_mcp_url` | URL of embedded Orchestrator MCP (dynamic port) |

### Flow (Centralized)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Agent Coordinator                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  create_run()                                                                │
│  ├─ Load agent blueprint from file                                          │
│  ├─ Merge capabilities (system_prompt, mcp_servers)                         │
│  ├─ Resolve placeholders:                                                   │
│  │   ├─ ${params.X} → from run parameters                                   │
│  │   ├─ ${scope.X} → from run scope                                         │
│  │   ├─ ${env.X} → from Coordinator environment                             │
│  │   └─ ${runtime.session_id}, ${runtime.run_id} → from run context         │
│  ├─ Leave ${runner.X} unresolved (Runner will handle)                       │
│  ├─ Validate required values present (fail fast)                            │
│  ├─ Store Run WITH resolved agent blueprint                                 │
│  └─ Return run_id, session_id                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ Run payload (includes resolved agent blueprint)
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Agent Runner                                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Poller receives Run                                                         │
│  ├─ Agent blueprint already resolved (no API call needed)                   │
│  ├─ Resolve ONLY: ${runner.orchestrator_mcp_url}                            │
│  │   (Runner spawns Orchestrator MCP on dynamic port)                       │
│  └─ Pass fully resolved blueprint to executor                               │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ Executor invocation payload (fully resolved)
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Claude Code Executor                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Receives fully resolved agent blueprint                                     │
│  No placeholder resolution needed                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Target Run Payload Structure

```json
{
  "run_id": "run_abc123",
  "type": "start_session",
  "session_id": "ses_abc123def456",
  "agent_name": "my-agent",
  "parameters": {"prompt": "..."},
  "scope": {"context_id": "ctx-123"},
  "project_dir": "/path/to/project",
  "parent_session_id": null,
  "execution_mode": "autonomous",
  "demands": {...},
  "status": "pending",
  "resolved_agent_blueprint": {
    "name": "my-agent",
    "system_prompt": "You are a research assistant...",
    "mcp_servers": {
      "context-store": {
        "type": "http",
        "url": "http://localhost:9501/mcp",
        "config": {
          "context_id": "ctx-123",
          "api_key": "sk-actual-key-from-coordinator-env"
        }
      },
      "orchestrator": {
        "type": "http",
        "url": "${runner.orchestrator_mcp_url}",
        "config": {
          "run_id": "run_abc123"
        }
      }
    }
  }
}
```

**Note**: `${runner.orchestrator_mcp_url}` is the ONLY unresolved placeholder. It uses the `runner` prefix to clearly indicate it must be resolved by the Runner (not Coordinator) because only the Runner knows the dynamic port of the embedded Orchestrator MCP server.

### Target Placeholder Resolution

| Placeholder | Resolved By | Reason |
|-------------|-------------|--------|
| `${params.X}` | Coordinator | Params available at run creation |
| `${scope.X}` | Coordinator | Scope available at run creation |
| `${env.X}` | Coordinator | Use Coordinator's environment |
| `${runtime.session_id}` | Coordinator | Known at run creation |
| `${runtime.run_id}` | Coordinator | Known at run creation |
| `${runner.orchestrator_mcp_url}` | **Runner** | Only Runner knows the dynamic port |

## Changes Required

### 1. Extend Run Model

**File**: `servers/agent-coordinator/services/run_queue.py`

Add fields to `Run` dataclass:

```python
@dataclass
class Run:
    run_id: str
    type: RunType
    session_id: str
    agent_name: Optional[str]
    parameters: dict
    project_dir: Optional[str]
    parent_session_id: Optional[str] = None
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS
    demands: Optional[dict] = None
    status: RunStatus = RunStatus.PENDING
    runner_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    claimed_at: Optional[str] = None

    # NEW FIELDS
    scope: Optional[dict] = None  # Run scope (LLM-invisible)
    resolved_agent_blueprint: Optional[dict] = None  # Fully resolved agent config
```

### 2. Add Scope to Run Creation API

**File**: `servers/agent-coordinator/main.py`

Update `RunCreate` model:

```python
class RunCreate(BaseModel):
    type: RunType
    agent_name: Optional[str] = None
    session_name: Optional[str] = None
    prompt: Optional[str] = None
    parameters: Optional[dict] = None
    project_dir: Optional[str] = None
    callback: bool = False

    # NEW FIELD
    scope: Optional[dict] = None  # Run scope (LLM-invisible)
```

### 3. Add Placeholder Resolution at Coordinator

**File**: `servers/agent-coordinator/services/placeholder_resolver.py` (NEW)

```python
"""Resolve placeholders in agent blueprint configuration."""

import os
import re
from typing import Any, Optional

PLACEHOLDER_PATTERN = re.compile(r'\$\{([^}]+)\}')

# Placeholders with these prefixes are NOT resolved at Coordinator
RUNNER_PREFIXES = {'runner.'}


class PlaceholderResolver:
    """Resolves ${source.key} placeholders in agent blueprint."""

    def __init__(
        self,
        params: dict,
        scope: dict,
        run_id: str,
        session_id: str,
    ):
        self.params = params or {}
        self.scope = scope or {}
        self.run_id = run_id
        self.session_id = session_id

    def resolve(self, agent_blueprint: dict) -> dict:
        """Resolve all placeholders in agent blueprint.

        Placeholders with 'runner.' prefix are left unresolved
        (they will be resolved by the Runner).

        Returns:
            Resolved blueprint with placeholders replaced.

        Raises:
            ValueError: If required placeholder value is missing.
        """
        return self._resolve_dict(agent_blueprint)

    def _resolve_dict(self, d: dict) -> dict:
        """Recursively resolve placeholders in dict."""
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = self._resolve_dict(value)
            elif isinstance(value, str):
                result[key] = self._resolve_string(value)
            elif isinstance(value, list):
                result[key] = [
                    self._resolve_dict(item) if isinstance(item, dict)
                    else self._resolve_string(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _resolve_string(self, s: str) -> str:
        """Resolve placeholders in a string value."""
        def replace_match(match: re.Match) -> str:
            placeholder = match.group(1)  # e.g., "scope.context_id"

            # Skip runner.* placeholders (resolved by Runner)
            if any(placeholder.startswith(prefix) for prefix in RUNNER_PREFIXES):
                return match.group(0)  # Keep as-is

            value = self._get_value(placeholder)
            if value is None:
                # Unresolved placeholder - keep as-is for now
                # Validation will catch missing required values
                return match.group(0)
            return str(value)

        return PLACEHOLDER_PATTERN.sub(replace_match, s)

    def _get_value(self, placeholder: str) -> Optional[Any]:
        """Get value for a placeholder like 'scope.context_id'."""
        parts = placeholder.split('.', 1)
        if len(parts) != 2:
            return None

        source, key = parts

        if source == 'params':
            return self.params.get(key)
        elif source == 'scope':
            return self.scope.get(key)
        elif source == 'env':
            return os.environ.get(key)
        elif source == 'runtime':
            if key == 'session_id':
                return self.session_id
            elif key == 'run_id':
                return self.run_id

        return None
```

### 4. Update create_run() to Resolve Blueprint

**File**: `servers/agent-coordinator/main.py`

In `create_run()` function, after loading and merging agent blueprint:

```python
from services.placeholder_resolver import PlaceholderResolver

async def create_run(run_create: RunCreate, ...):
    # ... existing code to load agent, merge capabilities ...

    # NEW: Resolve placeholders in agent blueprint
    if agent:
        resolver = PlaceholderResolver(
            params=run_create.parameters or {},
            scope=run_create.scope or {},
            run_id=run_id,
            session_id=session_id,
        )

        # Convert agent to dict for resolution
        agent_dict = agent.model_dump()

        # Resolve placeholders
        resolved_blueprint = resolver.resolve(agent_dict)

        # Store resolved blueprint in run
        run.resolved_agent_blueprint = resolved_blueprint
        run.scope = run_create.scope

    # ... rest of existing code ...
```

### 5. Simplify Runner (Remove Blueprint Fetch)

**File**: `servers/agent-runner/lib/executor.py`

Update `_build_payload()` to use resolved blueprint from run:

```python
def _build_payload(self, run: Run, mode: str) -> dict:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "session_id": run.session_id,
        "parameters": run.parameters,
    }

    if mode == "start":
        project_dir = run.project_dir or self.default_project_dir
        payload["project_dir"] = project_dir

    if run.agent_name:
        payload["agent_name"] = run.agent_name

    if self.executor_config:
        payload["executor_config"] = self.executor_config

    # NEW: Use resolved blueprint from run payload
    if run.resolved_agent_blueprint:
        # Resolve ONLY the runner.* placeholders
        resolved = self._resolve_runner_placeholders(run.resolved_agent_blueprint)
        payload["agent_blueprint"] = resolved

    return payload

def _resolve_runner_placeholders(self, blueprint: dict) -> dict:
    """Resolve ${runner.*} placeholders.

    This is the ONLY placeholder resolution at Runner level.
    Currently only ${runner.orchestrator_mcp_url} is supported.
    """
    import copy
    import re

    RUNNER_PLACEHOLDER = re.compile(r'\$\{runner\.([^}]+)\}')

    def resolve_string(s: str) -> str:
        def replace_match(match: re.Match) -> str:
            key = match.group(1)
            if key == 'orchestrator_mcp_url':
                return self.mcp_server_url
            # Unknown runner.* placeholder - keep as-is
            return match.group(0)
        return RUNNER_PLACEHOLDER.sub(replace_match, s)

    def resolve_dict(d: dict) -> dict:
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = resolve_dict(value)
            elif isinstance(value, str):
                result[key] = resolve_string(value)
            elif isinstance(value, list):
                result[key] = [
                    resolve_dict(item) if isinstance(item, dict)
                    else resolve_string(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    return resolve_dict(copy.deepcopy(blueprint))
```

### 6. Remove BlueprintResolver

**File**: `servers/agent-runner/lib/blueprint_resolver.py`

This file can be deleted or deprecated. Its functionality is replaced by:
- Placeholder resolution at Coordinator level
- Runner placeholder resolution in `_resolve_runner_placeholders()`

### 7. Simplify Executor Placeholder Processing

**File**: `servers/agent-runner/claude-code/lib/claude_client.py`

The `_process_mcp_servers()` function becomes a no-op or can be removed:

```python
def _process_mcp_servers(mcp_servers: dict) -> dict:
    """Process MCP server configuration.

    Note: With Coordinator-level resolution, all placeholders should
    already be resolved. This function is kept for defensive programming
    but should be a no-op.
    """
    # Simply return as-is - all placeholders already resolved
    return mcp_servers
```

## Scope Inheritance for Child Runs

When a parent agent spawns a child agent via the Orchestrator MCP:

1. Orchestrator MCP receives `run_id` from config
2. Orchestrator MCP calls Coordinator to create child run
3. Coordinator looks up parent run by `run_id`
4. Coordinator copies parent's `scope` to child run
5. Child run's blueprint resolved with inherited scope

```python
# In Coordinator, when creating child run from Orchestrator MCP
async def create_child_run(parent_run_id: str, agent_name: str, prompt: str):
    # Look up parent run
    parent_run = await run_queue.get_run(parent_run_id)

    # Inherit scope from parent
    child_scope = parent_run.scope.copy() if parent_run.scope else {}

    # Create child run with inherited scope
    child_run = await create_run(RunCreate(
        type=RunType.START_SESSION,
        agent_name=agent_name,
        prompt=prompt,
        scope=child_scope,  # Inherited from parent
    ))

    return child_run
```

## Validation

Required placeholders must be validated at run creation:

```python
def validate_required_config(
    agent_blueprint: dict,
    resolved_blueprint: dict,
    mcp_registry: dict,
) -> None:
    """Validate all required config values are resolved.

    Raises:
        ValueError: If required value is missing.
    """
    mcp_servers = agent_blueprint.get("mcp_servers", {})
    resolved_servers = resolved_blueprint.get("mcp_servers", {})

    for server_name, server_config in mcp_servers.items():
        ref = server_config.get("ref")
        if not ref:
            continue

        registry_entry = mcp_registry.get(ref)
        if not registry_entry:
            continue

        config_schema = registry_entry.get("config_schema", {})
        resolved_config = resolved_servers.get(server_name, {}).get("config", {})

        for key, schema in config_schema.items():
            if schema.get("required") and key not in resolved_config:
                raise ValueError(
                    f"Missing required value for MCP server '{server_name}' "
                    f"config key '{key}'"
                )
```

## Migration Path

### Phase 1: Extend Run Model
- Add `scope` and `resolved_agent_blueprint` fields to Run
- Fields are optional for backward compatibility
- No breaking changes

### Phase 2: Coordinator Resolution
- Add PlaceholderResolver
- Update `create_run()` to resolve and include blueprint
- Run payload now includes resolved blueprint

### Phase 3: Update Runner
- Check for `resolved_agent_blueprint` in run payload
- If present, use it (only resolve `${runner.*}` placeholders)
- If absent, fall back to existing behavior (backward compatibility)

### Phase 4: Remove Legacy Code
- Remove BlueprintResolver from Runner
- Remove `_process_mcp_servers()` placeholder logic from Executor
- Remove fallback behavior in Runner

## Testing

### Unit Tests

1. **PlaceholderResolver**
   - Resolves `${params.X}` correctly
   - Resolves `${scope.X}` correctly
   - Resolves `${env.X}` from environment
   - Resolves `${runtime.session_id}` and `${runtime.run_id}`
   - Leaves `${runner.orchestrator_mcp_url}` unresolved
   - Handles nested dicts and lists

2. **Run Creation**
   - `scope` field accepted and stored
   - `resolved_agent_blueprint` generated and stored
   - Validation fails for missing required values

3. **Runner**
   - Uses `resolved_agent_blueprint` from payload
   - Resolves `${runner.orchestrator_mcp_url}` correctly
   - No API call to fetch blueprint

### Integration Tests

1. **End-to-end Run**
   - Create run with scope
   - Verify blueprint resolved at Coordinator
   - Verify Runner receives resolved blueprint
   - Verify agent executes with correct MCP config

2. **Child Run Inheritance**
   - Parent run with scope
   - Parent spawns child via Orchestrator MCP
   - Verify child inherits parent's scope

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Blueprint in run payload** | No (agent_name only) | Yes (fully resolved) |
| **Runner fetches blueprint** | Yes (GET /agents/{name}) | No |
| **Placeholder resolution** | Runner + Executor | Coordinator (+ Runner for `${runner.*}` only) |
| **Validation timing** | Runtime (Executor) | Run creation (Coordinator) |
| **Environment variables** | Executor's env | Coordinator's env |
| **BlueprintResolver** | Required | Removed |
| **Scope inheritance** | N/A | Automatic via Coordinator |
