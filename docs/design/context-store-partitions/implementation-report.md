# Context Store Partitions - Implementation Report

**Date:** 2026-01-31
**Design Document:** `context-store-partitions.md`

## Summary

Implemented partition-based isolation for the Context Store, enabling controlled document visibility across different contexts (projects, sessions, workflows). Documents are partitioned by a single identifier with complete isolation between partitions.

## Main Files Changed

| File | Changes |
|------|---------|
| `servers/context-store/src/database.py` | Added `GLOBAL_PARTITION` constant, `partitions` table, `partition` column to documents, partition CRUD methods, updated all document queries to include partition filter |
| `servers/context-store/src/storage.py` | Added partition directory management (`ensure_partition_directory`, `delete_partition_directory`), updated all 6 storage methods to accept partition parameter for `base_dir/partition/doc_id` structure |
| `servers/context-store/src/models.py` | Added `PartitionCreate`, `PartitionResponse`, `PartitionListResponse`, `PartitionDeleteResponse` models, added `partition` field to `DocumentMetadata` and `DocumentResponse`, added `validate_partition_name()` helper |
| `servers/context-store/src/main.py` | Added partition lifecycle endpoints, all partitioned document endpoints, partitioned relation endpoints, partitioned search endpoint, refactored global endpoints as thin wrappers |
| `servers/context-store/src/semantic/indexer.py` | Added `partition` field to Elasticsearch index mapping, updated `index_document()` to accept partition parameter |
| `servers/context-store/src/semantic/search.py` | Added partition filter to KNN query in `search_documents()` |
| `mcps/context-store/lib/http_client.py` | Added resource constants (`RESOURCE_DOCUMENTS`, etc.), unified `_build_url()` method, partition parameter to all document/relation/search methods, partition lifecycle methods |
| `plugins/context-store/.../lib/client.py` | Same refactoring as MCP client, plus client-level default partition from `DOC_SYNC_PARTITION` environment variable |
| `plugins/context-store/.../lib/config.py` | Added `DOC_SYNC_PARTITION` environment variable support |

## New API Endpoints

### Partition Lifecycle

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/partitions` | Create a new partition |
| GET | `/partitions` | List all partitions |
| DELETE | `/partitions/{partition}` | Delete partition and all documents |

### Partitioned Document Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/partitions/{partition}/documents` | Create document in partition |
| GET | `/partitions/{partition}/documents` | List documents in partition |
| GET | `/partitions/{partition}/documents/{id}` | Get document content |
| GET | `/partitions/{partition}/documents/{id}/metadata` | Get document metadata |
| PUT | `/partitions/{partition}/documents/{id}/content` | Write document content |
| PATCH | `/partitions/{partition}/documents/{id}/content` | Edit document content |
| DELETE | `/partitions/{partition}/documents/{id}` | Delete document |
| GET | `/partitions/{partition}/documents/{id}/relations` | Get document relations |

### Partitioned Relation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/partitions/{partition}/relations` | Create relation (both docs must be in partition) |
| GET | `/partitions/{partition}/relations/definitions` | List relation definitions |
| PATCH | `/partitions/{partition}/relations/{id}` | Update relation note |
| DELETE | `/partitions/{partition}/relations/{id}` | Delete relation |

### Partitioned Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/partitions/{partition}/search` | Semantic search within partition |

## Backward Compatibility

All existing `/documents/...` and `/relations/...` endpoints continue to work unchanged. They internally use the `_global` partition, which is created automatically on database initialization.

Existing clients require no changes - they will continue using the global partition.

## Storage Structure

Documents are now stored in partition subdirectories:

```
document-data/
├── files/
│   ├── _global/
│   │   ├── doc_a1b2c3d4...
│   │   └── doc_e5f6a7b8...
│   ├── project-alpha/
│   │   └── doc_x9y8z7w6...
│   └── my-session/
│       └── doc_q1r2s3t4...
└── documents.db
```

## Database Schema Changes

### New Table: `partitions`

```sql
CREATE TABLE partitions (
    name TEXT PRIMARY KEY,
    description TEXT,
    created_at TEXT NOT NULL
);
```

### Updated Table: `documents`

Added column:
- `partition TEXT NOT NULL` - foreign key to `partitions.name`

New indexes:
- `idx_partition ON documents(partition)`
- `idx_partition_filename ON documents(partition, filename)`

## Elasticsearch Index Changes

Added field to index mapping:
- `partition: {"type": "keyword"}` - enables filtering by partition in KNN search

## Client Architecture

Both HTTP clients (MCP and plugin) use a unified approach for partition support:

### Resource Constants

```python
RESOURCE_DOCUMENTS = "documents"
RESOURCE_RELATIONS = "relations"
RESOURCE_SEARCH = "search"
RESOURCE_PARTITIONS = "partitions"
```

### URL Building

Single `_build_url()` method handles all endpoint construction:

```python
def _build_url(self, resource, partition=None, resource_id=None, suffix=None):
    if partition:
        path = f"/{RESOURCE_PARTITIONS}/{partition}/{resource}"
    else:
        path = f"/{resource}"
    if resource_id:
        path = f"{path}/{resource_id}"
    if suffix:
        path = f"{path}/{suffix}"
    return f"{self.base_url}{path}"
```

### Partition Parameter

All document, relation, and search methods accept an optional `partition` parameter:
- `partition=None` (default): Uses global partition endpoint
- `partition="my-project"`: Uses partitioned endpoint `/partitions/my-project/...`

### Plugin Client Environment Variable

The plugin client supports a client-level default partition via `DOC_SYNC_PARTITION`:

```bash
export DOC_SYNC_PARTITION=my-project  # All operations use my-project partition
export DOC_SYNC_PARTITION=             # Empty/unset = global partition
```

Partition resolution order:
1. Method `partition` parameter (if provided)
2. Client default from `DOC_SYNC_PARTITION` environment variable
3. Global partition (no partition in URL path)

## Key Design Decisions

1. **Single-tier partitioning**: Simple `partition` parameter instead of complex namespace/scope hierarchy
2. **Complete isolation**: No cross-partition access or queries
3. **Global partition for compatibility**: `_global` partition handles existing endpoints
4. **Explicit partitions**: Partitions must be created before use (typo protection)
5. **Cascade delete**: Deleting a partition removes all its documents and files
6. **Cross-partition relations forbidden**: Both documents must be in the same partition

## Testing Recommendations

1. Create partition: `POST /partitions {"name": "test-project"}`
2. Create document in partition: `POST /partitions/test-project/documents`
3. Verify isolation: `GET /partitions/test-project/documents` vs `GET /documents`
4. Delete partition: `DELETE /partitions/test-project`
5. Test backward compatibility: Verify `/documents` endpoints still work
6. Test semantic search partition filtering

## References

- Design document: `docs/design/context-store-partitions/context-store-partitions.md`
