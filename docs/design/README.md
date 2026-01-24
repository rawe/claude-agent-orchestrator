# Design Documents

Feature specifications and detailed designs for planned capabilities. Documents here represent work in planning or early development stages.

Once implemented, features are documented in [features/](../features/README.md) and the design doc moves to [archive/](./archive/).

## Planned

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

### Centralized Script Management

Deploy UV/Python scripts centrally via Dashboard with automatic distribution to procedural executors.

| Document | Description |
|----------|-------------|
| [Overview](./centralized-script-management/README.md) | Requirements, use cases, and document index |

### Other

| Document | Description |
|----------|-------------|
| [Agent Output Schema](./agent-output-schema.md) | Blueprint-defined output schemas for autonomous agents |
| [Structured Output Schema Enforcement](./structured-output-schema-enforcement.md) | Caller-driven JSON Schema enforcement on agent outputs |
| [Unified Task Model Overview](./unified-task-model-overview.md) | Architectural overview of the unified task model |

## Archive (Implemented)

Completed design documents kept for historical reference.

| Document | Implemented | Description |
|----------|-------------|-------------|
| [Rename Session Events to Run Events](./archive/rename-session-events-to-run-events.md) | 2026-01-06 | Event type naming refactoring |
