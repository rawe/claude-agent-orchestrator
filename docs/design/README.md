# Design Documents

Feature specifications and detailed designs for planned capabilities. Documents here represent work in planning or early development stages.

Once implemented, features are documented in [features/](../features/README.md) and the design doc moves to [archive/](./archive/).

## Planned

### MCP Server Registry

Centralized management of MCP server definitions with framework-controlled HTTP header injection for scoping and authentication.

| Document | Description |
|----------|-------------|
| [MCP Server Registry](./mcp-server-registry/mcp-server-registry.md) | Registry design with header inheritance chain |

### Context Store Scoping

Namespace and scope-based isolation for document visibility.

| Document | Description |
|----------|-------------|
| [Context Store Scoping](./context-store-scoping/context-store-scoping.md) | Namespace and scope_filters design (Approach 1: Explicit API) |

### External Service Auth

Token-based server-to-server authentication with scoping. Generic pattern applicable to Context Store, Knowledge Graph, and future services.

| Document | Description |
|----------|-------------|
| [External Service Auth](./external-service-auth/README.md) | Overview and reading guide for token-based authentication and scoping |

## Archive (Implemented)

Completed design documents kept for historical reference.

| Document | Implemented | Description |
|----------|-------------|-------------|
| [Rename Session Events to Run Events](./archive/rename-session-events-to-run-events.md) | 2026-01-06 | Event type naming refactoring |
