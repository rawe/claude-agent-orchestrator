# Work Package 2: Capability API

**Parent Feature:** [Capabilities System](../capabilities-system.md)
**Depends On:** [01-capability-storage](./01-capability-storage.md)
**Status:** Complete

## Goal

Expose capability CRUD operations via REST API endpoints.

## Scope

- `GET /capabilities` - List all capabilities
- `GET /capabilities/{name}` - Get single capability
- `POST /capabilities` - Create capability
- `PATCH /capabilities/{name}` - Update capability
- `DELETE /capabilities/{name}` - Delete capability

## Key Decisions

- List response includes metadata: `has_text`, `has_mcp`, `mcp_server_names`
- Delete checks if capability is referenced by agents (fails with 409 if referenced)

## Implementation

### Files Modified

1. **`servers/agent-coordinator/main.py`** - Added capability routes:
   - `GET /capabilities` - Returns `list[CapabilitySummary]`
   - `GET /capabilities/{name}` - Returns `Capability` or 404
   - `POST /capabilities` - Creates capability, returns 201 with `Capability`
   - `PATCH /capabilities/{name}` - Partial update, returns `Capability` or 404
   - `DELETE /capabilities/{name}` - Deletes capability, returns 204 or 404/409

2. **Helper function** `_get_agents_using_capability(name)`:
   - Iterates agents and returns names of those referencing the capability
   - Used by DELETE to prevent deleting capabilities in use

### Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Invalid capability name (validation failed) |
| 404 | Capability not found |
| 409 | Capability already exists (POST) or referenced by agents (DELETE) |

## Starting Points

- Look at agent endpoints in `servers/agent-coordinator/main.py`
- Follow same patterns for routing and error handling

## Acceptance

- [x] All CRUD endpoints functional
- [x] Proper error responses (404, 400, 409)
- [x] OpenAPI docs updated (automatic via FastAPI)
