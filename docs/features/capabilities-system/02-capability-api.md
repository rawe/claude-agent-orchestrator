# Work Package 2: Capability API

**Parent Feature:** [Capabilities System](../capabilities-system.md)
**Depends On:** [01-capability-storage](./01-capability-storage.md)

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
- Delete should check if capability is referenced by agents (warn or fail)

## Starting Points

- Look at agent endpoints in `servers/agent-coordinator/main.py`
- Follow same patterns for routing and error handling

## Acceptance

- All CRUD endpoints functional
- Proper error responses (404, 400, etc.)
- OpenAPI docs updated
