# Script Authoring Guide

Scripts are reusable execution units in Agentech. They define what to execute, what input they need, and what environment they require. Procedural agents reference scripts for execution.

**Goal:** Create a script that can be invoked via the orchestrator with validated parameters.

**Scope:** This guide covers script creation only. Script discovery, sync, and agent configuration are handled elsewhere.

## Structure

```
config/scripts/<script-name>/
├── script.json
└── <script>.py
```

## script.json

```json
{
  "name": "<script-name>",
  "description": "<what the script does>",
  "script_file": "<filename>.py",
  "parameters_schema": {
    "type": "object",
    "required": ["<param>"],
    "properties": {
      "<param>": {
        "type": "string",
        "enum": ["option1", "option2"],
        "description": "Parameter description"
      }
    }
  },
  "demands": { "tags": ["uv"] }
}
```

`parameters_schema` uses [JSON Schema](https://json-schema.org/). Properties become CLI arguments: `--<param> <value>`.

Common JSON Schema keywords: `type`, `enum`, `required`, `default`, `description`.

## Script File

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# Script receives parameters as --key value CLI arguments
# Output to stdout, errors to stderr
# Non-zero exit = failure
```

Script runs in project directory.
