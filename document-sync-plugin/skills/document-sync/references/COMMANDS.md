# Command Reference

## doc-push

```bash
uv run commands/doc-push <file> [--name TEXT] [--tags TEXT] [--description TEXT]
```

**Arguments**: `<file>` - File path to upload

**Options**:
- `--name TEXT` - Custom name (default: filename)
- `--tags TEXT` - Comma-separated tags
- `--description TEXT` - Description

**Examples**:
```bash
uv run commands/doc-push specs.md --tags "api,v2"
uv run commands/doc-push arch.md --tags "design,mvp" --description "MVP architecture"
```

**Output**:
```json
{
  "id": "doc_abc123def456...",
  "filename": "specs.md",
  "content_type": "text/markdown",
  "size_bytes": 2048,
  "created_at": "2025-11-23T00:00:00",
  "updated_at": "2025-11-23T00:00:00",
  "tags": ["api", "v2"],
  "metadata": {"description": "Specification document for API v2"}
}
```

**Note**: Save the `id` field for pull/delete operations.

---

## doc-query

```bash
uv run commands/doc-query [--name TEXT] [--tags TEXT] [--limit INTEGER]
```

**Options**:
- `--name TEXT` - Filter by filename pattern
- `--tags TEXT` - Filter by tags (AND logic - ALL tags must match)
- `--limit INTEGER` - Max results

**Examples**:
```bash
uv run commands/doc-query                    # List all
uv run commands/doc-query --tags "api,v2"    # Both tags required (AND)
uv run commands/doc-query --name "spec"      # Name contains "spec"
```

**Output**:
```json
[
  {
    "id": "doc_abc123...",
    "filename": "api-spec.md",
    "content_type": "text/markdown",
    "size_bytes": 1024,
    "created_at": "2025-11-23T00:00:00",
    "updated_at": "2025-11-23T00:00:00",
    "tags": ["api", "v2"],
    "metadata": {}
  }
]
```

**Important**: Multiple tags = ALL must match (AND logic, not OR)

---

## doc-pull

```bash
uv run commands/doc-pull <document-id> [--output PATH | -o PATH]
```

**Arguments**: `<document-id>` - Document ID from query results

**Options**: `--output PATH` or `-o PATH` - Output path (default: original filename)

**Examples**:
```bash
uv run commands/doc-pull doc_abc123...
uv run commands/doc-pull doc_abc123... -o custom-name.md
```

**Output**:
```json
{
  "success": true,
  "document_id": "doc_abc123...",
  "filename": "/absolute/path/to/output.md",
  "size_bytes": 2048
}
```

---

## doc-delete

```bash
uv run commands/doc-delete <document-id>
```

**Arguments**: `<document-id>` - Document ID from query results

**Example**:
```bash
uv run commands/doc-delete doc_abc123...
```

**Output**:
```json
{
  "success": true,
  "message": "Document doc_abc123... deleted successfully",
  "document_id": "doc_abc123..."
}
```

**Warning**: Permanent deletion - cannot be undone.

---

## Exit Codes

- `0` - Success
- `1` - Error (JSON error in stderr)