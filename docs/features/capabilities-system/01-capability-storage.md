# Work Package 1: Capability Storage & Models

**Parent Feature:** [Capabilities System](../capabilities-system.md)
**Status:** Complete

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

## Implementation

### Files Created/Modified

1. **`servers/agent-coordinator/models.py`** - Added capability models:
   - `CapabilityBase` - Base fields (name, description)
   - `CapabilityCreate` - Request body for creating capabilities
   - `CapabilityUpdate` - Request body for partial updates
   - `Capability` - Full capability with text, mcp_servers, timestamps
   - `CapabilitySummary` - List endpoint response (without full text)

2. **`servers/agent-coordinator/validation.py`** - Added validation functions:
   - `validate_capability_name()` - Same rules as agent names (1-60 chars, alphanumeric + hyphens/underscores)
   - `validate_unique_capability_name()` - Check for existing capability

3. **`servers/agent-coordinator/capability_storage.py`** - New file with CRUD operations:
   - `get_capabilities_dir()` - Returns `{AGENTS_DIR}/../capabilities/`
   - `list_capabilities()` - Returns list of `CapabilitySummary`
   - `get_capability(name)` - Returns full `Capability` or None
   - `create_capability(data)` - Creates capability directory and files
   - `update_capability(name, updates)` - Partial update support
   - `delete_capability(name)` - Removes capability directory

## Starting Points

- Look at `servers/agent-coordinator/agent_storage.py` for patterns
- Look at `servers/agent-coordinator/models.py` for Agent model structure

## Acceptance

- [x] Can create, read, update, delete capabilities via storage module
- [x] Capabilities persisted to file system
- [x] Validation rejects invalid capability names
