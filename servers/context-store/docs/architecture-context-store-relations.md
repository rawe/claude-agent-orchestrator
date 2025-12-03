# Context Store: Document Relations Framework

## Architectural Draft v1.0

**Status**: Implemented
**Date**: 2025-12-03
**Author**: Claude (AI Assistant)

---

## 1. Overview

This document describes the architecture for a **general document relations framework** in the context-store plugin.

### Terminology

A **Relation Definition** describes a bidirectional link between two documents. It combines two individual relations - one for each side.

Each individual **relation** is stored in the database with a **relation_type** (e.g., "parent", "child", "related").

**Example: `parent-child` definition**

When Document A becomes the parent of Document B:

```
Document A                          Document B
┌─────────────────────┐            ┌─────────────────────┐
│ relation_type:      │            │ relation_type:      │
│   "parent"          │───────────▶│   "child"           │
│ related_document:   │            │ related_document:   │
│   Document B        │◀───────────│   Document A        │
│ note: "..."         │            │ note: "..."         │
└─────────────────────┘            └─────────────────────┘
```

- The **definition** is `parent-child` (the conceptual link)
- Document A stores a relation with **type** `parent` (meaning: "I am a parent")
- Document B stores a relation with **type** `child` (meaning: "I am a child")
- Both relations together form the bidirectional link

**Example: `related` definition**

For peer documents, both sides have the same type:

```
Document A                          Document B
┌─────────────────────┐            ┌─────────────────────┐
│ relation_type:      │            │ relation_type:      │
│   "related"         │◀──────────▶│   "related"         │
└─────────────────────┘            └─────────────────────┘
```

### Available Definitions

| Definition | Types | Behavior |
|------------|-------|----------|
| `parent-child` | "parent" + "child" | Cascade delete (parent deletion removes children) |
| `related` | "related" + "related" | No cascade (deletion removes relation only) |

### Design Principles

- **KISS (Keep It Simple, Stupid)**: Minimal complexity, SQLite-only solution
- **YAGNI (You Aren't Gonna Need It)**: Only implement what's needed now
- **Bidirectional Consistency**: Both sides of a relation are always in sync
- **Relation-specific behavior**: Each definition defines its own deletion semantics

---

## 2. Requirements Summary

### Parent-Child Relations

| Aspect | Requirement |
|--------|-------------|
| Cardinality | One parent → many children; one child → one parent (soft constraint) |
| Hints | Each side stores a context note about the relationship |
| Cascade Delete | Parent deletion recursively deletes all descendants |
| Enforcement | One-parent constraint is NOT enforced technically |

### General Framework

- Extensible for future relation types
- Dedicated API endpoints for relation management
- Relations are not embedded in document metadata

---

## 3. Database Schema

### New Table: `document_relations`

```sql
CREATE TABLE document_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- The document that "owns" this relation entry
    document_id TEXT NOT NULL,

    -- The document this relation points to
    related_document_id TEXT NOT NULL,

    -- Relation type: 'parent' or 'child' (directional view)
    -- Future: 'sibling', 'reference', 'derived_from', etc.
    relation_type TEXT NOT NULL,

    -- Contextual notes about why/how documents are related
    -- e.g., "Implementation details for auth module"
    note TEXT,

    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- Foreign keys with cascade delete on relation rows
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (related_document_id) REFERENCES documents(id) ON DELETE CASCADE,

    -- Prevent duplicate relations
    UNIQUE(document_id, related_document_id, relation_type)
);

-- Indexes for efficient queries
CREATE INDEX idx_relations_document_id ON document_relations(document_id);
CREATE INDEX idx_relations_related_document_id ON document_relations(related_document_id);
CREATE INDEX idx_relations_type ON document_relations(relation_type);
```

### Bidirectional Storage Strategy

When creating a parent-child relation between documents A (parent) and B (child):

```
Row 1: document_id=A, related_document_id=B, relation_type='child', note='<parent's context about child>'
Row 2: document_id=B, related_document_id=A, relation_type='parent', note='<child's context about parent>'
```

**Why bidirectional storage?**
- Simple queries: "Get all children of X" → `WHERE document_id=X AND relation_type='child'`
- Each side can have its own note/context
- No complex joins or reverse lookups needed
- Consistent with KISS principle

### Cascade Delete: Application Logic

Cascade deletion is handled in **application code**, not database triggers. This is necessary because deletion involves multiple systems:
- Database records
- Filesystem (binary files)
- Semantic search index (Elasticsearch)

```python
def delete_document(doc_id: str) -> list[str]:
    """
    Delete a document with explicit relation type handling.
    Uses recursive calls so each document handles its own cleanup
    (file, Elasticsearch, database).
    """
    deleted_ids = []
    relations = db.get_relations(doc_id)

    for relation in relations:
        definition = RelationDefinitions.get_by_type(relation.relation_type)

        # EXPLICIT: Handle parent-child cascade
        if definition == RelationDefinitions.PARENT_CHILD:
            # Does this document have children? (relation_type is "parent")
            if relation.relation_type == definition.from_type:
                # Recursively delete child (it handles its own cleanup)
                deleted_ids.extend(delete_document(relation.related_document_id))

        # EXPLICIT: Related type - no cascade
        elif definition == RelationDefinitions.RELATED:
            pass  # Just remove relation, no cascade

        # Future relation definitions get their own explicit block

    # Delete this document's resources
    storage.delete_document(doc_id)
    indexer.delete_document_index(doc_id)
    db.delete_document(doc_id)  # Relations auto-deleted via FK CASCADE
    deleted_ids.append(doc_id)

    return deleted_ids
```

**Note**: The recursive approach ensures each document handles its own cleanup (file deletion, Elasticsearch index removal, database removal). This is simpler to understand than collecting all IDs upfront, though slightly less performant for very deep hierarchies.

**Helper: Delete Relation (Bidirectional)**

When deleting a relation (not the document), both sides must be removed to maintain consistency:

```python
def delete_relation(relation_id: int) -> None:
    """
    Delete a relation and its inverse counterpart.
    Maintains bidirectional consistency.
    """
    # 1. Get the relation being deleted
    relation = db.get_relation(relation_id)

    # 2. Find the inverse relation_type
    inverse_type = RelationDefinitions.get_inverse_type(relation.relation_type)

    # 3. Find and delete the counterpart relation
    counterpart = db.find_relation(
        document_id=relation.related_document_id,
        related_document_id=relation.document_id,
        relation_type=inverse_type
    )

    # 4. Delete both in a transaction
    with db.transaction():
        db.delete_relation_by_id(relation.id)
        if counterpart:
            db.delete_relation_by_id(counterpart.id)
```

**Why application logic instead of triggers:**
- Triggers cannot delete files from filesystem
- Triggers cannot clean up Elasticsearch indexes
- Application code keeps all deletion logic in one place
- Easier to test and debug
- Transaction control remains explicit

---

## 4. Relation Definitions (Application Code)

### RelationDefinition Class

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RelationDefinition:
    """
    Defines a relation with its two sides for bidirectional linking.
    Immutable to ensure consistency.
    """
    name: str           # API identifier: "parent-child", "related"
    description: str    # Human-readable description
    from_type: str      # DB value for first document: "parent", "related"
    to_type: str        # DB value for second document: "child", "related"


class RelationDefinitions:
    """
    Central registry of all relation definitions.
    Use these constants instead of magic strings.
    """

    PARENT_CHILD = RelationDefinition(
        name="parent-child",
        description="Hierarchical relation where parent owns children",
        from_type="parent",
        to_type="child"
    )

    RELATED = RelationDefinition(
        name="related",
        description="Peer relation between related documents",
        from_type="related",
        to_type="related"
    )

    # Registry for lookups
    _BY_NAME: dict[str, RelationDefinition] = {}
    _BY_TYPE: dict[str, RelationDefinition] = {}

    @classmethod
    def _init_registry(cls):
        """Initialize lookup mappings"""
        all_definitions = [cls.PARENT_CHILD, cls.RELATED]
        cls._BY_NAME = {d.name: d for d in all_definitions}
        cls._BY_TYPE = {}
        for d in all_definitions:
            cls._BY_TYPE[d.from_type] = d
            cls._BY_TYPE[d.to_type] = d

    @classmethod
    def get_by_name(cls, name: str) -> RelationDefinition:
        """Lookup by API name (e.g., 'parent-child')"""
        if not cls._BY_NAME:
            cls._init_registry()
        return cls._BY_NAME[name]

    @classmethod
    def get_by_type(cls, relation_type: str) -> RelationDefinition:
        """Lookup by database relation_type value (e.g., 'parent')"""
        if not cls._BY_TYPE:
            cls._init_registry()
        return cls._BY_TYPE[relation_type]

    @classmethod
    def get_inverse_type(cls, relation_type: str) -> str:
        """Get the inverse relation_type for bidirectional operations"""
        definition = cls.get_by_type(relation_type)
        if relation_type == definition.from_type:
            return definition.to_type
        return definition.from_type


# Initialize registry on module load
RelationDefinitions._init_registry()
```

### Usage Examples

```python
# Creating relations - use definition constants
definition = RelationDefinitions.PARENT_CHILD
db.create_relation(parent_id, child_id, definition.from_type, parent_note)  # stores "parent"
db.create_relation(child_id, parent_id, definition.to_type, child_note)     # stores "child"

# Looking up definition from DB value
definition = RelationDefinitions.get_by_type(db_row.relation_type)  # "parent" → PARENT_CHILD

# Bidirectional deletion - get inverse type
inverse_type = RelationDefinitions.get_inverse_type(db_row.relation_type)  # "parent" → "child"
```

---

## 5. Data Models (Pydantic)

### Request/Response Models

```python
from pydantic import BaseModel
from datetime import datetime

class RelationDefinitionResponse(BaseModel):
    """Available relation definition"""
    name: str            # "parent-child", "related"
    description: str     # Human-readable description
    from_type: str       # DB value for from document
    to_type: str         # DB value for to document

class RelationCreateRequest(BaseModel):
    """Request to create a relation"""
    definition: str                  # "parent-child", "related"
    from_document_id: str            # First document
    to_document_id: str              # Second document
    from_note: str | None = None     # Note from first document's perspective
    to_note: str | None = None       # Note from second document's perspective

class RelationResponse(BaseModel):
    """Single relation from a document's perspective"""
    id: int
    document_id: str
    related_document_id: str
    relation_type: str       # DB value: "parent", "child", "related"
    note: str | None
    created_at: datetime
    updated_at: datetime

class RelationUpdateRequest(BaseModel):
    """Update note for an existing relation"""
    note: str | None

class DocumentRelationsResponse(BaseModel):
    """All relations for a document, grouped by definition"""
    document_id: str
    relations: dict[str, list[RelationResponse]]  # Grouped by relation_type
```

---

## 5. API Endpoints

### Base Path: `/relations`

#### List Available Relation Definitions

```
GET /relations/definitions

Response: 200 OK
[
    {
        "name": "parent-child",
        "description": "Hierarchical relation where parent owns children",
        "from_type": "parent",
        "to_type": "child"
    },
    {
        "name": "related",
        "description": "Peer relation between related documents",
        "from_type": "related",
        "to_type": "related"
    }
]
```

#### Create Relation

```
POST /relations

Request Body:
{
    "definition": "parent-child",
    "from_document_id": "doc_abc123",
    "to_document_id": "doc_def456",
    "from_note": "Main implementation document",
    "to_note": "See parent for overview"
}

Response: 201 Created
{
    "success": true,
    "message": "Relation created",
    "from_relation": {
        "id": 1,
        "document_id": "doc_abc123",
        "related_document_id": "doc_def456",
        "relation_type": "parent",
        "note": "Main implementation document"
    },
    "to_relation": {
        "id": 2,
        "document_id": "doc_def456",
        "related_document_id": "doc_abc123",
        "relation_type": "child",
        "note": "See parent for overview"
    }
}

Errors:
- 400: Invalid definition name
- 404: Document not found
- 409: Relation already exists
```

#### Get Document Relations

```
GET /documents/{document_id}/relations

Response: 200 OK
{
    "document_id": "doc_abc123",
    "relations": {
        "parent": [
            {
                "id": 1,
                "document_id": "doc_abc123",
                "related_document_id": "doc_xyz789",
                "relation_type": "parent",
                "note": "See parent for overview",
                "created_at": "2025-12-03T10:00:00Z",
                "updated_at": "2025-12-03T10:00:00Z"
            }
        ],
        "child": [
            {
                "id": 2,
                "document_id": "doc_abc123",
                "related_document_id": "doc_def456",
                "relation_type": "child",
                "note": "Detailed implementation",
                "created_at": "2025-12-03T10:00:00Z",
                "updated_at": "2025-12-03T10:00:00Z"
            }
        ]
    }
}

Errors:
- 404: Document not found
```

#### Update Relation Note

```
PATCH /relations/{relation_id}

Request Body:
{
    "note": "Updated context information"
}

Response: 200 OK
{
    "success": true,
    "relation": { ... }
}

Errors:
- 404: Relation not found
```

#### Delete Relation

```
DELETE /relations/{relation_id}

Response: 200 OK
{
    "success": true,
    "message": "Relation removed",
    "deleted_relation_ids": [5, 12]  # Both sides of bidirectional relation
}

Note: This removes the relation only, NOT the documents.
      Both relation rows (the relation and its inverse) are deleted automatically.
      Use GET /documents/{id}/relations first to find the relation_id.

Errors:
- 404: Relation not found
```

---

## 6. Implementation Plan

### Phase 1: Database Schema

1. Add migration system (simple version tracking)
2. Create `document_relations` table
3. Add indexes
4. Update `DocumentDatabase` class with relation methods

### Phase 2: Application Code

1. Create `RelationDefinition` class and `RelationDefinitions` registry
2. Create Pydantic request/response models
3. Implement cascade delete logic with explicit relation type checks

### Phase 3: API Endpoints

1. `GET /relations/definitions` - List available relation definitions
2. `POST /relations` - Create relation (generic, uses definition name)
3. `GET /documents/{id}/relations` - Get document relations
4. `PATCH /relations/{id}` - Update note
5. `DELETE /relations/{id}` - Remove relation (handles bidirectional cleanup)

### Phase 4: Testing

1. Unit tests for database operations
2. Integration tests for API endpoints
3. Cascade delete tests (including recursive)
4. Concurrent modification tests

---

## 7. Considerations & Trade-offs

### Why Bidirectional Storage?

**Pros:**
- Simple, fast queries
- Each side has its own note
- No complex SQL for reverse lookups
- Easy to understand and maintain

**Cons:**
- Data redundancy (2 rows per relation)
- Must maintain consistency (handled by transactions)

**Decision**: Bidirectional storage aligns with KISS principle and makes queries trivial.

### Why Soft Constraint for Single Parent?

**Rationale:**
- Technically enforcing "one parent only" would require:
  - Unique index on (document_id, relation_type) WHERE relation_type='parent'
  - Or application-level checks with race conditions
- Soft constraint allows flexibility for edge cases
- Future relation types may have different cardinality rules
- Documentation + API design encourages correct usage

**Alternative considered:**
```sql
CREATE UNIQUE INDEX idx_single_parent
ON document_relations(document_id)
WHERE relation_type = 'parent';
```
This was rejected because it makes the framework less general and the user explicitly requested no technical enforcement.

### Recursive Deletion Performance

**Concern**: Deep hierarchies could cause slow cascades

**Mitigation:**
- Recursive application code is simple and maintainable
- Stack depth is only a concern for very deep hierarchies (unlikely in practice)
- Consider iterative approach for extremely deep trees (future optimization)

### Future Relation Definitions

The framework supports adding new relation definitions by:
1. Adding a new `RelationDefinition` constant to `RelationDefinitions`
2. Adding explicit handling in `delete_document()` if cascade behavior is needed

Examples of future definitions:
- `sibling`: Peer documents (mutual relation, no cascade)
- `reference`: Document A references B (one-way with backlink)
- `derived_from`: Document created from another
- `supersedes`: Newer version replaces older

---

## 8. Example Usage Scenarios

### Creating a Documentation Hierarchy

```
POST /relations
{
    "definition": "parent-child",
    "from_document_id": "doc_architecture",
    "to_document_id": "doc_database_design",
    "from_note": "Database layer documentation",
    "to_note": "Part of system architecture"
}

POST /relations
{
    "definition": "parent-child",
    "from_document_id": "doc_architecture",
    "to_document_id": "doc_api_design",
    "from_note": "API layer documentation",
    "to_note": "Part of system architecture"
}
```

Result:
```
doc_architecture
├── doc_database_design (note: "Database layer documentation")
└── doc_api_design (note: "API layer documentation")
```

### Deleting a Parent Document

When `DELETE /documents/doc_architecture`:
1. Application code checks relations, finds children: `doc_database_design`, `doc_api_design`
2. Recursively calls `delete_document()` for each child (handles its own cleanup)
3. Each document deletes: file from storage, Elasticsearch index, database record
4. Relation rows are auto-deleted via FK CASCADE

### Querying Relations

```
GET /documents/doc_database_design/relations

Response:
{
    "document_id": "doc_database_design",
    "relations": {
        "parent": [
            {
                "id": 5,
                "document_id": "doc_database_design",
                "related_document_id": "doc_architecture",
                "relation_type": "parent",
                "note": "Part of system architecture",
                "created_at": "2025-12-03T10:00:00Z",
                "updated_at": "2025-12-03T10:00:00Z"
            }
        ]
    }
}
```

---

## 9. Migration Strategy

- no migration needed for initial implementation, drop db and recreate!


## Appendix A: Full SQL Schema

```sql
-- Relations table
CREATE TABLE document_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    related_document_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (related_document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(document_id, related_document_id, relation_type)
);

CREATE INDEX idx_relations_document_id ON document_relations(document_id);
CREATE INDEX idx_relations_related_document_id ON document_relations(related_document_id);
CREATE INDEX idx_relations_type ON document_relations(relation_type);
```

**Note**: Cascade deletion of child documents is handled in application logic, not database triggers. See "Cascade Delete: Application Logic" section.
