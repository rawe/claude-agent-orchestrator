# Centralized Script Management

Scripts are reusable, executable units stored in the Coordinator. They define execution logic, input parameters, and runtime requirements. Procedural agents reference scripts rather than embedding execution logic directly.

## Rationale

Before centralized management, procedural scripts were bundled with runners:

- No central visibility into available scripts
- Script updates required manual deployment to each runner
- No Dashboard management for scripts

With scripts as a first-class primitive:

- Scripts are managed through the Dashboard or API
- Changes automatically sync to runners
- Procedural agents reference scripts by name, inheriting their parameter schemas

## Script Model

A script consists of metadata and an executable file, stored together in the Coordinator.

**Metadata fields:**

| Field | Description |
|-------|-------------|
| `name` | Unique identifier |
| `description` | Human-readable purpose |
| `script_file` | Filename of the executable (e.g., `process.py`, `deploy.sh`) |
| `parameters_schema` | JSON Schema defining accepted CLI arguments |
| `demands.tags` | Execution requirements (e.g., `["uv"]`, `["python3"]`) |

Scripts using Python dependencies leverage UV's PEP 723 inline metadata format, allowing dependencies to be declared directly in the script file.

**Execution environment:** Scripts run with `uv run --script` without the `--isolated` flag. This enables dependency caching for faster subsequent executions. The trade-off is that cached dependencies may become stale; if reproducibility issues arise, `--isolated` can be considered as a future enhancement.

## Procedural Agent Integration

Procedural agents reference scripts via the `script` field on the Agent entity. When an agent references a script:

- The script's `parameters_schema` is used for input validation
- The script's `demands.tags` are merged with the agent's demands (union)
- The agent can add its own description, hooks, and additional demand tags

This separation allows the same script to be used by multiple agents with different orchestration configurations.

## Scripts as Capabilities

Autonomous agents can also use scripts through the capability system. This enables local script execution within the agent's filesystem context, useful for file processing workflows where the agent creates files that need transformation.

### Capability Model

Capabilities can reference a script via the `script` field:

```json
{
  "name": "json-validation",
  "description": "Validate JSON files locally",
  "script": "json_checker"
}
```

When an autonomous agent is assigned this capability, the referenced script becomes available for local execution.

### System Prompt Injection

The Coordinator generates CLI usage instructions from the script's `parameters_schema` and injects them into the agent's system prompt. The agent sees guidance like:

```
## Local Script: json_checker
**Description:** Checks a given file for proper JSON format

**Usage:**
uv run --script scripts/json_checker/json_check.py --file <file>

**Arguments:**
- `--file` (required) - Path to the file to validate as JSON
```

The agent executes the script via bash, with direct access to the shared filesystem.

### Schema Transformation

The `parameters_schema` is transformed into CLI argument documentation:

| Schema Type | CLI Placeholder |
|-------------|-----------------|
| `string` | `<value>` |
| `integer` / `number` | `<N>` |
| `boolean` | (flag, no placeholder) |
| `array` | `<value1,value2,...>` |
| `enum` | `<option1\|option2>` |

Required arguments are shown without brackets; optional arguments use `[--arg]` notation. Default values are shown as `[default: value]`.

## Script Distribution

Scripts are distributed to runners through the existing long-poll mechanism.

**Sync triggers:**

| Event | Action |
|-------|--------|
| Script created/updated | Coordinator queues sync command to all runners |
| Script deleted | Coordinator queues remove command to all runners |
| Runner registration | Runner receives current scripts on first poll |

**Sync flow:**

1. Runner receives `sync_scripts` command via long-poll
2. Runner downloads script as tarball from `/scripts/{name}/download`
3. Runner extracts to `{PROJECT_DIR}/scripts/{name}/`
4. Runner makes the script file executable

Scripts are stored locally on the runner in a directory parallel to the project workspace, enabling the Procedural Executor to locate them at runtime.

## API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/scripts` | GET | List all scripts |
| `/scripts` | POST | Create script |
| `/scripts/{name}` | GET | Get script with content |
| `/scripts/{name}` | PATCH | Update script |
| `/scripts/{name}` | DELETE | Delete script (fails if referenced by agents) |
| `/scripts/{name}/download` | GET | Download script tarball for runner sync |

## Ownership Model

Procedural agents support two ownership models for backward compatibility. See [ADR-017: Procedural Agent Ownership Model](../adr/ADR-017-procedural-agent-ownership.md) for the architectural decision.

**Coordinator-owned** agents reference centralized scripts and benefit from Dashboard management and automatic sync.

**Runner-owned** agents use locally bundled scripts and are registered by runners at startup. This model exists for legacy compatibility and specialized runner-specific tools.

## Deployment: Shared Project Directory

Procedural scripts often need to access files created by autonomous agents. This is achieved by sharing the project directory between runners.

**Local development:** Both autonomous and procedural runners use the same `--project-dir` argument, giving them access to the same filesystem.

**Docker deployment:** Mount the same volume for both runner containers:

```yaml
services:
  autonomous-runner:
    volumes:
      - ./project:/app/project
    environment:
      - PROJECT_DIR=/app/project

  procedural-runner:
    volumes:
      - ./project:/app/project
    environment:
      - PROJECT_DIR=/app/project
```

Files created by autonomous agents at `{PROJECT_DIR}/data/output.csv` are immediately accessible to procedural scripts reading from the same path.

**Constraint:** File paths must be within the project directory. Paths outside (e.g., `/tmp/`) are not shared between runners.

## Related

- [ADR-017: Procedural Agent Ownership Model](../adr/ADR-017-procedural-agent-ownership.md)
- [ADR-011: Runner Capabilities and Run Demands](../adr/ADR-011-runner-capabilities-and-run-demands.md)
- [Capabilities System](./capabilities-system.md)
- [Agent Types](../architecture/agent-types.md)
