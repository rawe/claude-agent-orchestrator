# Work Package 1: Capability Storage & Models

**Parent Feature:** [Capabilities System](../capabilities-system.md)

## Goal

Create the data layer for capabilities: file storage, Pydantic models, and validation.

## Scope

- `capability_storage.py` - File-based storage (mirroring `agent_storage.py` patterns)
- Capability models in `models.py`
- Validation rules in `validation.py`

## Key Decisions

- Storage location: sibling to agents dir (`{AGENTS_DIR}/../capabilities/`)
- File structure per capability:
  - `capability.json` (name, description)
  - `capability.text.md` (optional)
  - `capability.mcp.json` (optional)

## Starting Points

- Look at `servers/agent-coordinator/agent_storage.py` for patterns
- Look at `servers/agent-coordinator/models.py` for Agent model structure

## Acceptance

- Can create, read, update, delete capabilities via storage module
- Capabilities persisted to file system
- Validation rejects invalid capability names
