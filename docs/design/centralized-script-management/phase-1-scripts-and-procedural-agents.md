# Phase 1: Scripts as Foundation for Procedural Agents

**Status:** Design
**Created:** 2025-01-24

## Overview

This document describes the implementation of centralized script management and its integration with procedural agents. Scripts become a first-class primitive stored in the Coordinator, and procedural agents reference scripts for execution.

---

## Scripts

### What is a Script

A script is a reusable, executable unit stored in the Coordinator. It defines:
- What it does (description)
- What input it needs (input schema)
- What output it produces (output schema)
- What execution environment it requires (demand tags)

Scripts are the **foundation** for procedural agents. A procedural agent references a script and adds agent-level configuration.

### Script Storage

Scripts are stored in the Coordinator following the same pattern as agents:

```
config/scripts/
└── {script_name}/
    ├── script.json       # Script metadata
    └── {script_file}     # The actual script (filename from script.json)
```

**Example:**
```
config/scripts/
└── send-notification/
    ├── script.json
    └── send-notification.py
```

### Script Model (`script.json`)

```json
{
  "name": "send-notification",
  "description": "Send a notification to a specified channel",
  "script_file": "send-notification.py",
  "parameters_schema": {
    "type": "object",
    "required": ["message", "channel"],
    "properties": {
      "message": {
        "type": "string",
        "description": "The notification message to send"
      },
      "channel": {
        "type": "string",
        "enum": ["slack", "email", "sms"],
        "description": "The channel to send the notification to"
      },
      "priority": {
        "type": "string",
        "enum": ["low", "normal", "high"],
        "default": "normal"
      }
    }
  },
  "demands": {
    "tags": ["uv"]
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier, must match folder name |
| `description` | string | Yes | Human-readable description |
| `script_file` | string | Yes | Filename of the script (e.g., `send-notification.py`, `deploy.sh`) |
| `parameters_schema` | object | No | JSON Schema for script parameters (CLI arguments) |
| `demands.tags` | array | No | Tags required from executor (e.g., `["uv"]`, `["python3"]`, `["bash"]`) |

### Script File

The script file (referenced by `script_file`) contains the executable code:

**UV script example (`send-notification.py`):**
```python
# /// script
# dependencies = ["click", "requests"]
# ///
import click
import json

@click.command()
@click.option('--message', required=True)
@click.option('--channel', required=True, type=click.Choice(['slack', 'email', 'sms']))
@click.option('--priority', default='normal', type=click.Choice(['low', 'normal', 'high']))
def main(message, channel, priority):
    # Send notification logic here
    result = {'sent': True, 'channel': channel, 'priority': priority}
    print(json.dumps(result))

if __name__ == '__main__':
    main()
```

**Bash script example (`deploy.sh`):**
```bash
#!/bin/bash
# Deploy script
echo "{\"status\": \"deployed\", \"target\": \"$1\"}"
```

---

## Procedural Agents

### Relationship to Scripts

A procedural agent **references** a script. The script provides the execution logic; the agent provides orchestration-level configuration.

```
Script (execution logic)
    │
    │ referenced by
    ▼
Procedural Agent (orchestration config)
    │
    │ called via
    ▼
Orchestrator MCP (start_agent_session)
```

### Procedural Agent Model

```json
{
  "name": "notifier",
  "type": "procedural",
  "description": "Send notifications to various channels",
  "script": "send-notification",
  "demands": {
    "tags": ["messaging-team"]
  },
  "hooks": {
    "on_run_start": { ... },
    "on_run_finish": { ... }
  }
}
```

### What Comes from Where

| Property | Source | Notes |
|----------|--------|-------|
| `name` | Agent | Agent's unique name |
| `description` | Agent | Can differ from script description |
| `script` | Agent | Reference to script name |
| `parameters_schema` | Script | Inherited, not configurable on agent |
| `demands.tags` | Merged | Agent tags + script tags combined |
| `hooks` | Agent | Agent-specific hooks |

### Demand Tag Merging

When a procedural agent is executed, demand tags are merged:

```
Script demands:  ["uv"]
Agent demands:   ["messaging-team"]
Effective:       ["uv", "messaging-team"]
```

The executor must satisfy **all** tags to claim the run.

### Dashboard Changes

Currently, procedural agents in the Dashboard are read-only (registered by runners). This changes:

**New behavior:**
- Procedural agents can be created/edited in Dashboard
- New field: Script selector (dropdown of available scripts)
- Parameters schema shown as read-only (from script)
- Hooks configurable
- Description configurable
- Demand tags configurable (merged with script's)

---

## Script Distribution

### Storage on Runner

When scripts are synced to a runner, they are stored in:

```
{project_dir}/.agent-orchestrator/scripts/
└── {script_name}/
    ├── script.json
    └── {script_file}
```

The entire script folder is copied from Coordinator to Runner.

### Sync Mechanism

Scripts are distributed via the existing long-poll mechanism.

**Current long-poll responses:**
- Runs to start
- Stop commands

**New addition:**
- Sync commands with script names

#### Sync Command Structure

```json
{
  "type": "sync_scripts",
  "scripts": ["send-notification", "deploy-service"]
}
```

The Coordinator decides which scripts to sync to which runner based on:
- Scripts referenced by procedural agents
- Demand tag compatibility with runner's executor

#### When Sync Occurs

| Trigger | Behavior |
|---------|----------|
| Runner registration | Full sync of all relevant scripts |
| Script created/updated | Coordinator queues sync command for relevant runners |
| Manual trigger (API) | Force sync to specific runner(s) |

#### Sync Flow

```
1. Runner registers
   │
   ▼
2. Coordinator determines relevant scripts
   (based on procedural agents and demand matching)
   │
   ▼
3. Coordinator queues sync command in long-poll response
   {
     "type": "sync_scripts",
     "scripts": ["send-notification", "deploy-service"]
   }
   │
   ▼
4. Runner receives sync command
   │
   ▼
5. Runner fetches script folders from Coordinator
   GET /scripts/{name}/download
   │
   ▼
6. Runner writes to local scripts directory
   {project_dir}/.agent-orchestrator/scripts/{name}/
   │
   ▼
7. Runner reports sync complete (optional)
```

#### Script Cleanup

When a script is deleted from Coordinator:
1. Coordinator queues cleanup command
2. Runner removes local script folder

```json
{
  "type": "remove_scripts",
  "scripts": ["old-script"]
}
```

---

## API Endpoints

### Script Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scripts` | GET | List all scripts |
| `/scripts` | POST | Create script (uploads folder) |
| `/scripts/{name}` | GET | Get script metadata |
| `/scripts/{name}` | PUT | Update script |
| `/scripts/{name}` | DELETE | Delete script |
| `/scripts/{name}/download` | GET | Download script folder (for runner sync) |

### Script Sync

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scripts/sync/trigger` | POST | Manually trigger sync to runners |

**Request:**
```json
{
  "scripts": ["send-notification"],
  "runners": ["runner-01"]  // optional, all relevant if omitted
}
```

---

## Execution Flow

When a procedural agent is invoked:

```
1. Caller invokes via orchestrator MCP
   start_agent_session(agent_name="notifier", parameters={...})
   │
   ▼
2. Coordinator validates parameters against script's parameters_schema
   │
   ▼
3. Coordinator creates run with merged demands (agent + script)
   │
   ▼
4. Runner claims run (if demands match)
   │
   ▼
5. Runner locates script in local scripts directory
   {project_dir}/.agent-orchestrator/scripts/send-notification/
   │
   ▼
6. Procedural executor executes script
   (execution method based on demand tags, e.g., "uv" → uv run --script)
   │
   ▼
7. Script output captured and returned as result_data
```

---

## Summary

| Component | Responsibility |
|-----------|---------------|
| **Script** | Defines execution logic, input/output schemas, execution requirements |
| **Procedural Agent** | References script, adds orchestration config (hooks, description, extra demands) |
| **Coordinator** | Stores scripts and agents, manages distribution, validates parameters |
| **Runner** | Syncs scripts locally, executes via procedural executor |
| **Dashboard** | Manages scripts and procedural agents |
| **Orchestrator MCP** | Provides `start_agent_session` for invoking procedural agents |

---

---

## Deployment: Shared Project Directory for File Access

A common concern is whether procedural scripts can access files created by autonomous agents. This is solved by sharing the **project directory** between runners.

### The Pattern

Both autonomous and procedural runners use the same project directory as their working directory. Files created by one are accessible to the other.

```
Autonomous Agent (Runner A)
    │
    │ Creates: {project_dir}/data/output.csv
    │
    │ Calls: start_agent_session(
    │   agent_name="csv-processor",
    │   parameters={"path": "data/output.csv"}
    │ )
    ▼
Procedural Agent (Runner B)
    │
    │ Reads: {project_dir}/data/output.csv
    │ (same directory, file exists)
    ▼
Result returned
```

### Local Development

When running runners locally (without Docker), both runners naturally share the filesystem:

```bash
# Terminal 1: Autonomous runner
./agent-runner --profile autonomous --project-dir /path/to/project

# Terminal 2: Procedural runner
./agent-runner --profile procedural --project-dir /path/to/project
```

Both runners operate in the same project directory. Files created by autonomous agents are immediately accessible to procedural scripts.

### Docker Deployment

When running runners in Docker containers, mount the same volume for the project directory:

```yaml
# docker-compose.yml
services:
  autonomous-runner:
    image: agent-runner
    volumes:
      - ./project:/app/project
    environment:
      - PROJECT_DIR=/app/project

  procedural-runner:
    image: agent-runner
    volumes:
      - ./project:/app/project  # Same mount
    environment:
      - PROJECT_DIR=/app/project
```

Both containers see the same `/app/project` directory. File operations work transparently.

### Key Constraint

**Files must be within the project directory.** Paths outside the project directory are not shared and will not work across runners.

| Path | Works? | Reason |
|------|--------|--------|
| `{project_dir}/data/file.csv` | Yes | Within shared directory |
| `data/file.csv` (relative) | Yes | Resolved relative to project dir |
| `/tmp/file.csv` | No | Outside shared directory |
| `/home/user/file.csv` | No | Outside shared directory |

### When This Is Sufficient

This shared directory approach covers most use cases:
- Processing files created by autonomous agents
- Sharing intermediate results between agents
- Working with project-local data

### When Phase 2 Would Be Needed

Phase 2 (local script execution) would only be needed for:
- Operations requiring `/tmp` or other non-project paths
- Scenarios where runners cannot share a volume
- Latency-critical operations avoiding network round-trips

For most workflows, the shared project directory is sufficient.

---

## Related Documents

- [Phase 2: Scripts as Capabilities](./phase-2-scripts-as-capabilities.md) - Future consideration for local execution in autonomous agents
- [Open Questions](./open-questions.md) - Unresolved design questions
