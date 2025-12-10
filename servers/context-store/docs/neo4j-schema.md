# Neo4j Database Schema

The context-store uses Neo4j graph database to store document metadata and relations. This document describes the schema design.

## Node Types

### Document

Represents a stored document with its metadata.

**Label:** `Document`

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier (e.g., `doc_a1b2c3d4e5f6`) |
| `filename` | String | Original filename |
| `content_type` | String | MIME type (e.g., `text/markdown`) |
| `size_bytes` | Integer | File size in bytes |
| `checksum` | String | SHA256 checksum |
| `storage_path` | String | Filesystem path to document file |
| `created_at` | String | ISO 8601 timestamp |
| `updated_at` | String | ISO 8601 timestamp |
| `tags` | List[String] | Array of tag strings |
| `metadata` | String | JSON string of custom key-value metadata |

## Relationship Types

### RELATES_TO

Bidirectional relationship between documents. Each logical relation creates two directed edges (one in each direction) to enable efficient traversal from either document.

**Type:** `RELATES_TO`

| Property | Type | Description |
|----------|------|-------------|
| `relation_type` | String | Type of relation: `parent`, `child`, `related`, `predecessor`, `successor` |
| `note` | String | Optional annotation/note |
| `created_at` | String | ISO 8601 timestamp |
| `updated_at` | String | ISO 8601 timestamp |

## Relation Types

| Relation Definition | from_type | to_type | Cascade Delete |
|---------------------|-----------|---------|----------------|
| `parent-child` | `child` | `parent` | Yes |
| `related` | `related` | `related` | No |
| `predecessor-successor` | `successor` | `predecessor` | No |

**Note:** The `from_type` stored on the edge from document A to document B indicates what B is to A. For example, if A is a parent of B, then:
- Edge A→B has `relation_type: 'child'` (B is A's child)
- Edge B→A has `relation_type: 'parent'` (A is B's parent)

## Constraints and Indexes

```cypher
-- Unique constraint on document ID
CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE

-- Index on filename for queries
CREATE INDEX document_filename IF NOT EXISTS
FOR (d:Document) ON (d.filename)

-- Index on tags for filtering
CREATE INDEX document_tags IF NOT EXISTS
FOR (d:Document) ON (d.tags)
```

## Example Queries

### Create a Document

```cypher
CREATE (d:Document {
    id: 'doc_abc123',
    filename: 'example.md',
    content_type: 'text/markdown',
    size_bytes: 1234,
    checksum: 'sha256...',
    storage_path: '/app/data/files/doc_abc123',
    created_at: '2025-01-15T10:00:00',
    updated_at: '2025-01-15T10:00:00',
    tags: ['documentation', 'example'],
    metadata: '{"description": "Example document"}'
})
```

### Query Documents by Tag

```cypher
MATCH (d:Document)
WHERE ALL(tag IN ['documentation', 'example'] WHERE tag IN d.tags)
RETURN d
```

### Create Parent-Child Relation

```cypher
-- Parent doc_a, Child doc_b
MATCH (a:Document {id: 'doc_a'})
MATCH (b:Document {id: 'doc_b'})
CREATE (a)-[:RELATES_TO {
    relation_type: 'child',
    note: 'Child document',
    created_at: '2025-01-15T10:00:00',
    updated_at: '2025-01-15T10:00:00'
}]->(b)
CREATE (b)-[:RELATES_TO {
    relation_type: 'parent',
    note: 'Parent document',
    created_at: '2025-01-15T10:00:00',
    updated_at: '2025-01-15T10:00:00'
}]->(a)
```

### Get Document with Relations

```cypher
MATCH (d:Document {id: 'doc_abc123'})-[r:RELATES_TO]->(related:Document)
RETURN d, r, related
```

### Get Child Documents (for Cascade Delete)

```cypher
MATCH (parent:Document {id: 'doc_parent'})-[r:RELATES_TO {relation_type: 'child'}]->(child:Document)
RETURN child.id AS child_id
```

### Delete Document with Relations

```cypher
MATCH (d:Document {id: 'doc_abc123'})
DETACH DELETE d
```

## Visual Schema

```
┌─────────────────────────────────────────────────────────────┐
│                         Document                             │
│  (:Document)                                                │
├─────────────────────────────────────────────────────────────┤
│  id: String (UNIQUE)                                        │
│  filename: String (INDEXED)                                 │
│  content_type: String                                       │
│  size_bytes: Integer                                        │
│  checksum: String                                           │
│  storage_path: String                                       │
│  created_at: String                                         │
│  updated_at: String                                         │
│  tags: List[String] (INDEXED)                               │
│  metadata: String (JSON)                                    │
└─────────────────────────────────────────────────────────────┘
          │
          │  [:RELATES_TO]
          │  relation_type: String
          │  note: String
          │  created_at: String
          │  updated_at: String
          ▼
┌─────────────────────────────────────────────────────────────┐
│                         Document                             │
│  (another document node)                                    │
└─────────────────────────────────────────────────────────────┘
```

## Migration Notes

This schema replaces the previous SQLite-based storage. Key differences:

1. **Tags**: Stored as native Neo4j list property instead of separate join table
2. **Relations**: Stored as graph edges (`RELATES_TO`) instead of a separate table
3. **Cascade Delete**: Handled by `DETACH DELETE` which removes all relationships
4. **Indexes**: Created on document properties for query performance
