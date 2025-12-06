# ADR-001: Relation API Property Naming

## Status
Approved

## Context
Testing revealed that AI agents misinterpret the relation API properties. When presented with:
```json
{
  "name": "parent-child",
  "from_type": "child",
  "to_type": "parent"
}
```

Agents interpreted `from_type: "child"` as "from_document IS the child" rather than the intended "from_document STORES a child relation type."

This ambiguity caused incorrect usage of the relation creation endpoint.

## Decision

### Relation Definition Response
Rename properties to explicitly state what each document IS in the relationship:

**Before:**
```json
{
  "name": "parent-child",
  "from_type": "child",
  "to_type": "parent"
}
```

**After:**
```json
{
  "name": "parent-child",
  "from_document_is": "parent",
  "to_document_is": "child"
}
```

### Relation Creation Request
Rename note properties to indicate edge direction in the bidirectional graph:

**Before:**
```json
{
  "definition": "parent-child",
  "from_document_id": "<id>",
  "to_document_id": "<id>",
  "from_note": "<text>",
  "to_note": "<text>"
}
```

**After:**
```json
{
  "definition": "parent-child",
  "from_document_id": "<id>",
  "to_document_id": "<id>",
  "from_to_note": "<text>",
  "to_from_note": "<text>"
}
```

### Mental Model
```
[from_doc] ---from_to_note---> [to_doc]
           <--to_from_note----
```

For parent-child where parent=from, child=to:
- `from_to_note`: "Visual evidence screenshot" (parent's note about child)
- `to_from_note`: "Parent bug report" (child's note about parent)

## Implementation Files

| Component | File |
|-----------|------|
| Relation definitions | `src/models.py` - `RelationDefinition`, `RelationDefinitions` |
| API request model | `src/models.py` - `RelationCreateRequest` |
| API response model | `src/models.py` - `RelationDefinitionResponse` |
| Endpoint handler | `src/main.py` - `create_relation()`, relation definitions endpoint |
| Database layer | `src/database.py` - `create_relation()`, `get_child_document_ids()` |

## Consequences
- API consumers can unambiguously understand which document plays which role
- Note properties clearly indicate which edge they label in the bidirectional graph
- Existing clients (bug-spotter extension) will need to update property names
