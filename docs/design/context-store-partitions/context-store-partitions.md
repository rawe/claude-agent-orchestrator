# Context Store Partitions

**Status:** Implemented
**Date:** 2026-01-31

## Overview

Introduce partition-based isolation to the Context Store, enabling controlled document visibility across different contexts (projects, sessions, workflows). Documents are partitioned by a single identifier, with complete isolation between partitions.

**Key Principles:**
1. Simple single-tier partitioning (one `partition` parameter)
2. Complete isolation between partitions (no cross-partition access)
3. Backward compatible via global partition
4. Explicit partition lifecycle (create, list, delete)
5. Internally always explicit - no special-casing for global

## Motivation

### Problem Statement

The Context Store currently has no access boundaries. Any client can see all documents:

| Problem | Impact |
|---------|--------|
| No project isolation | Documents from unrelated projects visible to all agents |
| No session isolation | Agent runs in different sessions see each other's artifacts |
| No multi-tenancy | Cannot support multiple isolated document spaces |

### Use Cases

1. **Project isolation**: Documents for "project-alpha" invisible to agents working on "project-beta"
2. **Session-scoped artifacts**: Root session creates partition shared with sub-agents
3. **Workflow isolation**: Separate document spaces for different workflows

## Design

### Partition Model

Single-tier partitioning with one identifier:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Context Store                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Partition: "_global"              Partition: "project-alpha"   │
│  ┌────────────────────────┐        ┌────────────────────────┐   │
│  │  doc_a1b2...           │        │  doc_x9y8...           │   │
│  │  doc_c3d4...           │        │  doc_z7w6...           │   │
│  │  (backward compat)     │        │  (isolated)            │   │
│  └────────────────────────┘        └────────────────────────┘   │
│                                                                  │
│  Partition: "ses_root_001"         Partition: "project-beta"    │
│  ┌────────────────────────┐        ┌────────────────────────┐   │
│  │  doc_e5f6...           │        │  doc_m3n4...           │   │
│  │  (session tree)        │        │  (isolated)            │   │
│  └────────────────────────┘        └────────────────────────┘   │
│                                                                  │
│  Complete isolation: No cross-partition access                   │
└─────────────────────────────────────────────────────────────────┘
```

### Global Partition

A special partition `_global` (constant: `GLOBAL_PARTITION`) provides backward compatibility:

- Pre-created and persisted (not on every startup - initialization/migration)
- Accessed via `/documents/...` endpoints (no partition prefix)
- Enables future overarching search endpoints
- Documents created without partition go here

### Document Visibility

| Access Path | Documents Returned |
|-------------|-------------------|
| `GET /documents` | Only `_global` partition |
| `GET /partitions/project-alpha/documents` | Only `project-alpha` partition |

**No cross-partition visibility.** Each partition is completely isolated.

### Document IDs

Document IDs are globally unique across all partitions:

```python
doc_id = f"doc_{secrets.token_hex(12)}"  # 96 bits of randomness
```

- No partition encoded in ID
- Enables future overarching endpoints
- Collision probability effectively zero

## API Design

### New Partition Endpoints

#### Create Partition

```http
POST /partitions
Content-Type: application/json

{
  "name": "project-alpha",
  "description": "Optional description"
}
```

**Response:** `201 Created`
```json
{
  "name": "project-alpha",
  "description": "Optional description",
  "created_at": "2026-01-31T10:00:00Z"
}
```

**Errors:**
- `400`: Invalid partition name
- `409`: Partition already exists

#### List Partitions

```http
GET /partitions
```

**Response:** `200 OK`
```json
{
  "partitions": [
    {"name": "_global", "description": "Global partition", "created_at": "..."},
    {"name": "project-alpha", "description": "...", "created_at": "..."}
  ]
}
```

#### Delete Partition

```http
DELETE /partitions/{partition}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Partition deleted",
  "deleted_document_count": 42
}
```

**Behavior:**
- Deletes partition and ALL documents within it
- Removes partition subdirectory from storage
- Removes all chunks from semantic search index

**Errors:**
- `404`: Partition not found
- `403`: Cannot delete `_global` partition

### Document Endpoints

#### Partitioned Endpoints (New)

```http
POST   /partitions/{partition}/documents
GET    /partitions/{partition}/documents
GET    /partitions/{partition}/documents/{document_id}
GET    /partitions/{partition}/documents/{document_id}/metadata
PUT    /partitions/{partition}/documents/{document_id}/content
PATCH  /partitions/{partition}/documents/{document_id}/content
DELETE /partitions/{partition}/documents/{document_id}
GET    /partitions/{partition}/documents/{document_id}/relations
GET    /partitions/{partition}/search
```

**Error:** `404` if partition does not exist (typo protection)

#### Global Endpoints (Backward Compatible)

```http
POST   /documents
GET    /documents
GET    /documents/{document_id}
...
```

**Internal mapping:** These are thin wrappers that delegate to partitioned endpoints with `GLOBAL_PARTITION`:

```python
GLOBAL_PARTITION = "_global"

@app.get("/documents")
async def list_documents_global(...):
    return await list_documents_partitioned(GLOBAL_PARTITION, ...)
```

### Relation Endpoints

Relations remain partition-scoped:

```http
POST   /partitions/{partition}/relations
GET    /partitions/{partition}/relations/definitions
PATCH  /partitions/{partition}/relations/{relation_id}
DELETE /partitions/{partition}/relations/{relation_id}
```

**Constraint:** Relations cannot cross partition boundaries. Both documents must be in the same partition.

### Search Endpoint

```http
GET /partitions/{partition}/search?q=...&limit=10
```

Semantic search filtered by partition. Only returns documents within the specified partition.

## Internal Architecture

### Always Explicit Partition

Internally, all operations use explicit partition names. No special-casing:

```python
GLOBAL_PARTITION = "_global"

# All database queries include partition
def query_documents(partition: str, filename: str = None, tags: list = None):
    query = "SELECT * FROM documents WHERE partition = ?"
    # ...

# All storage operations use partition path
def get_document_path(partition: str, doc_id: str) -> Path:
    return self.base_dir / partition / doc_id
```

The global endpoints are a thin compatibility layer only.

### Storage Structure

Partition subdirectories for document files:

```
document-data/
├── files/
│   ├── _global/
│   │   ├── doc_a1b2c3d4...
│   │   └── doc_e5f6a7b8...
│   ├── project-alpha/
│   │   ├── doc_x9y8z7w6...
│   │   └── doc_m3n4o5p6...
│   └── ses_root_001/
│       └── doc_q1r2s3t4...
└── documents.db
```

**Benefits:**
- Partition deletion is simple (delete directory)
- Files organized by partition
- Easy inspection/debugging

### Database Schema

Add `partition` column to documents table:

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    partition TEXT NOT NULL,           -- NEW: partition identifier
    filename TEXT,
    content_type TEXT,
    size_bytes INTEGER,
    checksum TEXT,
    storage_path TEXT,
    created_at TEXT,
    updated_at TEXT,
    metadata TEXT
);

CREATE INDEX idx_partition ON documents(partition);
CREATE INDEX idx_partition_filename ON documents(partition, filename);
```

Add partitions table:

```sql
CREATE TABLE partitions (
    name TEXT PRIMARY KEY,
    description TEXT,
    created_at TEXT NOT NULL
);
```

### Semantic Search

Single Elasticsearch index with partition field for filtering:

**Index Mapping:**
```json
{
  "mappings": {
    "properties": {
      "context_store_document_id": {"type": "keyword"},
      "partition": {"type": "keyword"},
      "char_start": {"type": "integer"},
      "char_end": {"type": "integer"},
      "embedding": {
        "type": "dense_vector",
        "dims": 768,
        "index": true,
        "similarity": "cosine"
      }
    }
  }
}
```

**Search with Filter:**
```python
search_body = {
    "knn": {
        "field": "embedding",
        "query_vector": query_embedding,
        "k": limit * 3,
        "num_candidates": 100,
        "filter": {
            "term": {"partition": partition}
        }
    }
}
```

### Relation Constraints

Relations cannot cross partition boundaries:

```python
def create_relation(partition: str, from_doc_id: str, to_doc_id: str, ...):
    # Verify both documents exist in the same partition
    from_doc = get_document(partition, from_doc_id)
    to_doc = get_document(partition, to_doc_id)

    if not from_doc or not to_doc:
        raise HTTPException(404, "Document not found in partition")

    # Create relation...
```

## Out of Scope

The following are explicitly out of scope for this design:

| Topic | Reason |
|-------|--------|
| Authentication | Separate concern (JWT, Auth0) |
| MCP server configuration | How scope is passed via headers/env vars is separate |
| Cross-partition access | Against isolation principle |
| Partition permissions | No fine-grained access control within partitions |
| Partition metadata beyond name/description | Keep it simple |

## Implementation Guide

### Affected Components

| Component | Files | Changes |
|-----------|-------|---------|
| **API Layer** | `servers/context-store/src/main.py` | New partition endpoints, partitioned document endpoints, global endpoint wrappers, URL generation |
| **Models** | `servers/context-store/src/models.py` | `PartitionCreate`, `PartitionResponse`, add partition to document models |
| **Database** | `servers/context-store/src/database.py` | Partition CRUD, add partition to all document queries, new indexes |
| **Storage** | `servers/context-store/src/storage.py` | Partition subdirectories, all methods need partition parameter (6 methods) |
| **Semantic Indexer** | `servers/context-store/src/semantic/indexer.py` | Add partition field to chunks, update index mapping |
| **Semantic Search** | `servers/context-store/src/semantic/search.py` | Add partition filter to KNN queries |
| **MCP HTTP Client** | `mcps/context-store/lib/http_client.py` | Add partition parameter to all document methods |
| **Plugin Client** | `plugins/context-store/skills/context-store/commands/lib/client.py` | Add partition parameter to all document methods |
| **API Documentation** | `servers/context-store/README.md` | Document new endpoints and partition parameter |
| **Test Scenarios** | `servers/context-store/tests/test-scenarios.md` | Add partition test cases |

### Implementation Order

1. **Database**: Add partitions table, add partition column to documents
2. **Storage**: Implement partition subdirectories
3. **Models**: Add partition-related Pydantic models
4. **API - Partitions**: Implement `POST/GET/DELETE /partitions`
5. **API - Documents**: Add partitioned endpoints, refactor global as wrappers
6. **Relations**: Add partition validation
7. **Semantic Search**: Add partition field and filtering
8. **Testing**: Full integration tests

## Migration

### Clean Slate Approach

This implementation uses a clean slate approach:

- **Database**: Rebuilt from scratch (no schema migration)
- **Elasticsearch**: Complete re-index (no migration concerns)
- **File Storage**: New structure from start

### Global Partition Initialization

The `_global` partition is created once during initialization:

```python
def ensure_global_partition():
    """Ensure the global partition exists. Called during initialization."""
    if not partition_exists(GLOBAL_PARTITION):
        create_partition(GLOBAL_PARTITION, description="Global partition (default)")
```

This should be called on first database creation, not on every server startup.

## References

### Related Documentation

- [Context Store Architecture](../../components/context-store/README.md)
- [Context Store Server](../../components/context-store/SERVER.md)
- [MCP Server Architecture](../../components/context-store/MCP.md)

### Supersedes

This design supersedes the two-tier namespace/scope_filters approach in:
- `docs/design/context-store-scoping/context-store-scoping.md`

The simpler single-tier partition model was chosen for MVP.
