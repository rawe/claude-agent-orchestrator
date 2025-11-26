# BUG-001: Missing /documents/tags Endpoint

## Problem

Frontend calls `GET /documents/tags` but endpoint doesn't exist. Falls back to client-side computation with console warning.

## Error

```
Tags endpoint not implemented, computing client-side
```

## Files

**Frontend (caller):**
- `agent-orchestrator-frontend/src/services/documentService.ts:81-100` - `getTags()` method

**Backend (needs fix):**
- `plugins/document-sync/document-server/src/main.py` - Add endpoint here

## Expected Endpoint

```
GET /documents/tags
Response: { "tags": [{"name": "string", "count": number}, ...] }
```

## Fix

Add to `main.py`:

```python
@app.get("/documents/tags")
def get_tags():
    # Query all documents, aggregate tags with counts
    # Return {"tags": [{"name": "tag1", "count": 5}, ...]}
```

Sort by count descending. Reference existing `list_documents()` for database access pattern.
