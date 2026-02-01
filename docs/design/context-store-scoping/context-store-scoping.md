# Context Store Scoping and Namespace Isolation

**Status:** Partially Implemented
**Date:** 2026-01-11

> **Note:** A simpler single-tier partition model has been implemented instead of the two-tier namespace/scope_filters approach described here. See [Context Store Partitions](../../features/context-store-partitions.md) for the implemented feature. This document is retained for reference on potential future enhancements (e.g., scope_filters within partitions).

## Overview

Introduce namespace and scope-based isolation to the Context Store, enabling controlled document visibility across agent runs. Documents are partitioned by logical boundaries (namespaces for projects/workflows) and optionally by finer-grained criteria (scope filters for run trees, origins). The Context Store API is explicit; the MCP layer enforces that LLMs cannot manipulate scope.

**Key Principles:**
1. Context Store remains domain-agnostic - no knowledge of sessions, agents, or orchestration concepts
2. Namespace is the primary isolation boundary (required)
3. Scope filters are optional generic key-value pairs (framework decides semantics)
4. Context Store Server API is explicit - namespace in URL path, no header magic
5. LLMs cannot influence scope - MCP server receives context from executor, translates to explicit API calls

## Motivation

### Problem Statement

The Context Store currently has no access boundaries. Any client can see all documents, creating several issues:

| Problem | Impact |
|---------|--------|
| No project isolation | Documents from unrelated projects visible to all agents |
| No workflow isolation | Agent runs in different contexts see each other's artifacts |
| No multi-tenancy | Cannot support multiple users/teams with isolated document spaces |
| Security concerns | Sensitive documents accessible to any agent in the system |

### Use Cases

1. **Project-based isolation**: Documents for "project-alpha" invisible to agents working on "project-beta"
2. **Workflow-scoped artifacts**: Intermediate documents from one workflow not visible to unrelated workflows
3. **Shared reference documents**: Architecture docs visible to all runs within a project namespace
4. **Run-specific scratch space**: Temporary documents visible only to a specific run tree

## Design

### Scoping Model

Two orthogonal scoping dimensions:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Scoping Model                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Namespace: "project-alpha" (required)                                      │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                                                                    │    │
│   │   Scoped Documents                      Namespace-Wide Documents   │    │
│   │   (scope_filters present)               (scope_filters empty)      │    │
│   │                                                                    │    │
│   │   ┌──────────────────────┐              ┌──────────────────────┐  │    │
│   │   │ tree_id: tree_001    │              │ (no filters)         │  │    │
│   │   │ ┌────────┐ ┌────────┐│              │                      │  │    │
│   │   │ │ doc_a  │ │ doc_b  ││              │ ┌────────┐ ┌────────┐│  │    │
│   │   │ └────────┘ └────────┘│              │ │ doc_x  │ │ doc_y  ││  │    │
│   │   └──────────────────────┘              │ └────────┘ └────────┘│  │    │
│   │                                         │                      │  │    │
│   │   ┌──────────────────────┐              │ Visible to ALL runs  │  │    │
│   │   │ tree_id: tree_002    │              │ in this namespace    │  │    │
│   │   │ ┌────────┐           │              └──────────────────────┘  │    │
│   │   │ │ doc_c  │           │                                        │    │
│   │   │ └────────┘           │                                        │    │
│   │   └──────────────────────┘                                        │    │
│   │                                                                    │    │
│   └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│   Namespace: "project-beta" (completely isolated)                           │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │   ...                                                              │    │
│   └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Concept | Required | Purpose |
|---------|----------|---------|
| **Namespace** | Yes | Primary isolation boundary. Documents in different namespaces are completely invisible to each other. |
| **Scope Filters** | No | Generic key-value pairs for finer-grained scoping within a namespace. Framework assigns meaning (e.g., `tree_id`, `origin`). |

### Document Visibility Rules

**Query behavior:**

| API Request | Documents returned |
|-------------|-------------------|
| `GET /namespaces/project-alpha/documents` | All docs in namespace (scoped + namespace-wide) |
| `GET /namespaces/project-alpha/documents?scope_filters={"tree_id":"tree_001"}` | Docs with `tree_id=tree_001` + namespace-wide docs |

**Key rule:** Namespace-wide documents (empty `scope_filters`) are always visible to any request within that namespace.

### Security Boundary

The LLM generates tool calls but cannot control scope. The MCP server receives scope configuration from the executor and translates to explicit API calls:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Executor / Harness                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Executor provides config to MCP Server:                                    │
│     CONTEXT_STORE_NAMESPACE=project-alpha                                    │
│     CONTEXT_STORE_SCOPE_FILTERS={"tree_id":"tree_001"}                      │
│                                                                              │
│   ┌─────────────┐         ┌─────────────────────────────────────────────┐   │
│   │     LLM     │         │              MCP Server                     │   │
│   │             │         │                                             │   │
│   │ Tool call:  │         │  Receives:                                  │   │
│   │ doc_query(  │────────►│    - Tool params (from LLM): tags, name     │   │
│   │   tags=..., │         │    - Config (from executor): namespace,     │   │
│   │   name=...  │         │      scope_filters                          │   │
│   │ )           │         │                                             │   │
│   │             │         │  Builds explicit API call:                  │   │
│   │ (cannot set │         │    GET /namespaces/project-alpha/documents  │   │
│   │  namespace  │         │        ?tags=...                            │   │
│   │  or filters)│         │        &scope_filters={"tree_id":"tree_001"}│   │
│   └─────────────┘         └──────────────────────┬──────────────────────┘   │
│                                                  │                          │
│                                                  ▼                          │
│                                    ┌─────────────────────────┐              │
│                                    │  Context Store Server   │              │
│                                    │                         │              │
│                                    │  Explicit API:          │              │
│                                    │  Namespace in URL path  │              │
│                                    │  Scope filters as param │              │
│                                    └─────────────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### API Structure

**Namespace in URL path, scope filters as query/body parameter:**

```
POST   /namespaces/{namespace}/documents
GET    /namespaces/{namespace}/documents
GET    /namespaces/{namespace}/documents?scope_filters={...}&tags=...
GET    /namespaces/{namespace}/documents/{id}
PUT    /namespaces/{namespace}/documents/{id}/content
PATCH  /namespaces/{namespace}/documents/{id}/content
DELETE /namespaces/{namespace}/documents/{id}
GET    /namespaces/{namespace}/search?q=...&scope_filters={...}
POST   /namespaces/{namespace}/relations
```

| Parameter | Location | Purpose |
|-----------|----------|---------|
| `namespace` | URL path | Primary isolation boundary (required) |
| `scope_filters` | Query param (GET) or body (POST) | JSON object for finer-grained filtering (optional) |

### Document Storage Model

```
┌──────────────────────────────────────────────────────────────────────┐
│  Document record:                                                    │
├──────────────────────────────────────────────────────────────────────┤
│  id: doc_abc123                                                      │
│  filename: architecture.md                                           │
│  namespace: "project-alpha"          ◄── Primary isolation           │
│  scope_filters: {                    ◄── Generic key-value filters   │
│    "tree_id": "tree_001",                                            │
│    "origin": "run_xyz"                                               │
│  }                                                                   │
│  tags: ["architecture", "mvp"]       ◄── User/agent-controlled       │
│  metadata: { ... }                   ◄── User/agent-controlled       │
│  content_type: "text/markdown"                                       │
│  ...                                                                 │
└──────────────────────────────────────────────────────────────────────┘

  namespace + scope_filters = Framework-controlled (MCP hides from LLM)
  tags + metadata = LLM/user-controlled (exposed in tool parameters)
```

## Framework Integration

This section maps the generic Context Store scoping features to Agent Orchestrator framework use cases.

### Use Case 1: Namespace-Wide Documents (Session-Overarching)

**Scenario:** Documents shared across all sessions in a project, regardless of which run tree created them. Example: architecture docs, specifications, shared reference material.

**Framework mapping:**

| Generic Feature | Framework Usage |
|-----------------|-----------------|
| `namespace` | Project or workflow identifier (e.g., `"project-alpha"`) |
| `scope_filters` | Empty `{}` - no filters, visible to all |

**Coordinator assigns context:**

```json
POST /runs
{
  "agent_name": "architect",
  "prompt": "Create architecture doc",
  "context": {
    "namespace": "project-alpha",
    "scope_filters": {}
  }
}
```

**Document creation (via MCP → Context Store API):**

```
POST /namespaces/project-alpha/documents
Body: { "filename": "architecture.md", "scope_filters": {} }

Result: Document visible to ALL runs in "project-alpha" namespace
```

**Document query:**

```
GET /namespaces/project-alpha/documents?tags=architecture

Result: Returns this document regardless of requester's scope_filters
```

### Use Case 2: Root Session Scoped Documents (Session Tree)

**Scenario:** Documents visible only to agents within the same session tree. A root session spawns child sessions; all share the same scope. Example: intermediate artifacts, session-specific scratch space.

**Framework mapping:**

| Generic Feature | Framework Usage |
|-----------------|-----------------|
| `namespace` | Project identifier (e.g., `"project-alpha"`) |
| `scope_filters.root_session_id` | Root session ID of the session tree |

**Session tree example:**

```
Root Session: ses_root_001
├── Child Session: ses_child_002
└── Child Session: ses_child_003
    └── Grandchild: ses_child_004

All sessions use: scope_filters = {"root_session_id": "ses_root_001"}
```

**Coordinator assigns context:**

When creating any run in this tree, coordinator sets:

```json
POST /runs
{
  "agent_name": "implementer",
  "prompt": "Implement feature X",
  "context": {
    "namespace": "project-alpha",
    "scope_filters": {
      "root_session_id": "ses_root_001"
    }
  }
}
```

The coordinator determines `root_session_id`:
- For root sessions: use own session ID
- For child sessions: inherit from parent's context

**Document creation (via MCP → Context Store API):**

```
POST /namespaces/project-alpha/documents
Body: {
  "filename": "implementation-notes.md",
  "scope_filters": {"root_session_id": "ses_root_001"}
}

Result: Document visible only to runs with matching root_session_id + namespace-wide docs
```

**Document query from any session in tree:**

```
GET /namespaces/project-alpha/documents?scope_filters={"root_session_id":"ses_root_001"}

Result:
- Documents with root_session_id=ses_root_001
- PLUS namespace-wide documents (empty scope_filters)
```

**Document query from different session tree:**

```
GET /namespaces/project-alpha/documents?scope_filters={"root_session_id":"ses_root_999"}

Result:
- Documents with root_session_id=ses_root_999 (different tree)
- PLUS namespace-wide documents
- NOT documents from ses_root_001 tree
```

### Document Write Behavior

When creating or writing documents, the scope is applied from the request:

**1. Create placeholder with scope:**

```
POST /namespaces/{namespace}/documents
Body: {
  "filename": "notes.md",
  "scope_filters": {"root_session_id": "ses_root_001"}
}

Stored: namespace="project-alpha", scope_filters={"root_session_id":"ses_root_001"}
```

**2. Write content (scope already set):**

```
PUT /namespaces/{namespace}/documents/{id}/content
Body: "# Notes content..."

Scope unchanged - inherits from document creation
```

**3. Push file with scope:**

```
POST /namespaces/{namespace}/documents
Form: file=@notes.md, scope_filters={"root_session_id":"ses_root_001"}

Stored with provided scope_filters
```

**MCP Server behavior:**

The MCP server always injects configured scope into document creation:

```python
# MCP tool (simplified)
def doc_create(filename: str, tags: list = None):
    # LLM provides: filename, tags
    # MCP injects: namespace, scope_filters from executor config
    return client.post(
        f"/namespaces/{config.namespace}/documents",
        json={
            "filename": filename,
            "tags": tags,
            "scope_filters": config.scope_filters  # Injected, not from LLM
        }
    )
```

### Summary: Read vs Write Scope Handling

| Operation | Namespace | Scope Filters |
|-----------|-----------|---------------|
| **Query/Read** | From URL path | Optional param - if provided, returns matching + namespace-wide |
| **Create** | From URL path | From request body - stored with document |
| **Write content** | Already set | Already set (from creation) |

## Subcomponent Changes

### Context Store Server

| Area | Change |
|------|--------|
| **API restructure** | New URL structure: `/namespaces/{namespace}/documents/...`. All endpoints scoped under namespace path. |
| **Schema** | Add `namespace` (TEXT, NOT NULL, indexed) and `scope_filters` (JSON) columns to documents table |
| **Query filtering** | Filter by namespace from URL path. If `scope_filters` query param present, include documents matching filters OR having empty `scope_filters` (namespace-wide). |
| **Document creation** | Documents receive `namespace` from URL path and `scope_filters` from request body |
| **Backward compatibility** | Old endpoints (`/documents/...`) deprecated, redirect to `/namespaces/default/documents/...` |
| **API documentation** | Document new URL structure and scope_filters parameter in OpenAPI spec |

### MCP Server

| Area | Change |
|------|--------|
| **Startup config** | Accept namespace and scope_filters from executor (env vars or config) |
| **API call construction** | Build explicit API URLs using configured namespace (e.g., `/namespaces/{ns}/documents`). Add `scope_filters` param from config. |
| **Tool definitions** | Do NOT expose namespace/filter params to LLM. These are framework-controlled. |

### CLI Commands

| Area | Change |
|------|--------|
| **Flags** | Add `--namespace` (required) and `--scope-filter key=value` (repeatable) flags |
| **Environment** | Support `DOC_NAMESPACE` and `DOC_SCOPE_FILTERS` env vars for scripting |
| **Backward compatibility** | If no namespace provided, use default namespace (e.g., `"default"`) with deprecation warning |

**Example CLI usage:**

```bash
# Push document to namespace
doc-push --namespace project-alpha --scope-filter tree_id=tree_001 file.md

# Query documents in namespace
doc-query --namespace project-alpha --tags architecture

# Using environment variables
DOC_NAMESPACE=project-alpha doc-query --tags architecture
```

### Agent Coordinator

| Area | Change |
|------|--------|
| **Run creation** | Accept `context.namespace` and `context.scope_filters` in POST /runs request body |
| **Run storage** | Store context alongside run metadata |
| **Runner dispatch** | Pass context to runner when assigning runs |

**Example run creation:**

```json
POST /runs
{
  "type": "start_session",
  "agent_name": "architect",
  "prompt": "Design the API layer",
  "context": {
    "namespace": "project-alpha",
    "scope_filters": {
      "tree_id": "tree_001",
      "origin": "run_abc"
    }
  }
}
```

### Agent Runner / Executor

| Area | Change |
|------|--------|
| **Context propagation** | Receive context from coordinator, pass to MCP server spawn |
| **MCP configuration** | Provide namespace/scope_filters via env vars or config file when spawning MCP server |

## Configuration

### Environment Variables

| Variable | Component | Description |
|----------|-----------|-------------|
| `DOC_NAMESPACE` | CLI | Default namespace for CLI commands |
| `DOC_SCOPE_FILTERS` | CLI | JSON object of default scope filters |
| `CONTEXT_STORE_NAMESPACE` | MCP Server | Namespace to use in API calls (set by executor) |
| `CONTEXT_STORE_SCOPE_FILTERS` | MCP Server | JSON object of scope filters to include in API calls (set by executor) |

## Migration Strategy

### Phase 1: Additive Changes (Backward Compatible)

1. Add `namespace` and `scope_filters` columns to documents table
2. Add new `/namespaces/{namespace}/...` endpoints alongside existing endpoints
3. Existing `/documents/...` endpoints continue to work, using `"default"` namespace
4. CLI supports `--namespace` flag but defaults to `"default"` if not provided
5. Existing documents assigned to `"default"` namespace

### Phase 2: Deprecation

1. Mark old `/documents/...` endpoints as deprecated in OpenAPI spec
2. Add deprecation warnings to CLI when namespace not specified
3. Log warnings on server when old endpoints used

### Phase 3: Removal (Breaking)

1. Remove old `/documents/...` endpoints (or redirect to `/namespaces/default/...`)
2. CLI requires `--namespace` or `DOC_NAMESPACE` env var
3. Update all framework components to use namespaced endpoints

## Limitations

| Limitation | Rationale |
|------------|-----------|
| No cross-namespace access | By design. Namespaces are complete isolation boundaries. |
| No fine-grained permissions | Complexity vs. value trade-off. All docs in accessible scope are readable/writable. |
| No scope filter matching modes | Exact match only. Keeps implementation simple. |
| Framework must assign scope | Context Store is domain-agnostic; doesn't know session hierarchies. |

## Future Considerations

The following enhancements may be explored in future iterations:

### Enhancement: Document-Level Access Control

Per-document read/write permissions. Trade-off: significant complexity increase, may not be needed.

### Enhancement: Scope Inheritance

Child documents automatically inherit parent's scope. Trade-off: adds implicit behavior, complicates document creation.

### Enhancement: Scope Filter Matching Modes

Support `subset` or `any` matching for scope filters. Trade-off: added complexity for hierarchical access patterns.

### Enhancement: Cross-Namespace Document Linking

Allow documents to reference documents in other namespaces (read-only). Trade-off: adds complexity, potential security considerations.

## References

### Component Documentation

- [Context Store Architecture](../../components/context-store/README.md) - Component overview
- [Context Store Server](../../components/context-store/SERVER.md) - Server architecture
- [MCP Server Architecture](../../components/context-store/MCP.md) - MCP integration

### Implementation Documentation

- [Context Store Server README](../../../servers/context-store/README.md) - Server implementation, API endpoints, environment variables
- [Semantic Search Architecture](../../../servers/context-store/docs/architecture-semantic-search.md) - Vector search implementation
- [Document Relations](../../../servers/context-store/docs/architecture-context-store-relations.md) - Parent-child and peer relations
