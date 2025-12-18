# Command Reference

## doc-push

```bash
uv run --script commands/doc-push <file> [--name TEXT] [--tags TEXT] [--description TEXT]
```

**Arguments**: `<file>` - File path to upload

**Options**:
- `--name TEXT` - Custom name (default: filename)
- `--tags TEXT` - Comma-separated tags
- `--description TEXT` - Description

**Examples**:
```bash
uv run --script commands/doc-push specs.md --tags "api,v2"
uv run --script commands/doc-push arch.md --tags "design,mvp" --description "MVP architecture"
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
  "metadata": {"description": "Specification document for API v2"},
  "url": "http://localhost:8766/documents/doc_abc123def456..."
}
```

**Note**: Save the `id` field for pull/delete operations.

---

## doc-query

```bash
uv run --script commands/doc-query [--name TEXT] [--tags TEXT] [--limit INTEGER]
```

**Options**:
- `--name TEXT` - Filter by filename pattern
- `--tags TEXT` - Filter by tags (AND logic - ALL tags must match)
- `--limit INTEGER` - Max results

**Examples**:
```bash
uv run --script commands/doc-query                    # List all
uv run --script commands/doc-query --tags "api,v2"    # Both tags required (AND)
uv run --script commands/doc-query --name "spec"      # Name contains "spec"
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
    "metadata": {},
    "url": "http://localhost:8766/documents/doc_abc123..."
  }
]
```

**Important**: Multiple tags = ALL must match (AND logic, not OR)

---

## doc-info

```bash
uv run --script commands/doc-info <document-id>
```

**Arguments**: `<document-id>` - Document ID to retrieve metadata for

**Examples**:
```bash
uv run --script commands/doc-info doc_abc123...
```

**Output**:
```json
{
  "id": "doc_abc123...",
  "filename": "api-spec.md",
  "content_type": "text/markdown",
  "size_bytes": 1024,
  "created_at": "2025-11-23T00:00:00",
  "updated_at": "2025-11-23T00:00:00",
  "tags": ["api", "v2"],
  "metadata": {"description": "API specification"},
  "url": "http://localhost:8766/documents/doc_abc123...",
  "relations": {
    "parent": [
      {
        "id": "rel_abc123",
        "related_document_id": "doc_child1",
        "note": "Database layer docs",
        "created_at": "2025-12-03T10:00:00"
      }
    ],
    "child": [],
    "related": []
  }
}
```

**Use Case**: View document metadata without downloading the file. The `url` field provides a direct link to retrieve the document. The `relations` field shows all document relationships grouped by type.

**If no relations exist**: `"relations": {}`

**Error Output** (stderr):
```json
{"error": "Document not found: doc_abc123..."}
```

---

## doc-read

```bash
uv run --script commands/doc-read <document-id>
```

**Arguments**: `<document-id>` - Document ID to read content from

**Examples**:
```bash
# Direct output
uv run --script commands/doc-read doc_abc123...

# Pipe to grep
uv run --script commands/doc-read doc_abc123... | grep "pattern"

# Pipe to wc
uv run --script commands/doc-read doc_abc123... | wc -l

# Save to file
uv run --script commands/doc-read doc_abc123... > output.txt
```

**Output**: Raw text content to stdout (no JSON wrapper)

**Supported MIME Types**:
- `text/*` (text/plain, text/markdown, text/html, etc.)
- `application/json`
- `application/xml`

**Error Output** (stderr):
```json
{"error": "Cannot read non-text file (MIME type: image/png). Use doc-pull to download binary files."}
{"error": "File is not valid UTF-8 text. Use doc-pull to download."}
{"error": "Document not found: doc_abc123..."}
```

**Use Case**: Read text document content directly without downloading to file system. Ideal for:
- Piping content to other tools (grep, awk, jq, etc.)
- Quick inspection of text files
- Processing document content in scripts

**Limitations**:
- Text files only (binary files will error)
- UTF-8 encoding only
- For binary files or non-UTF-8 content, use `doc-pull` instead

---

## doc-pull

```bash
uv run --script commands/doc-pull <document-id> [--output PATH | -o PATH]
```

**Arguments**: `<document-id>` - Document ID from query results

**Options**: `--output PATH` or `-o PATH` - Output path (default: original filename)

**Examples**:
```bash
uv run --script commands/doc-pull doc_abc123...
uv run --script commands/doc-pull doc_abc123... -o custom-name.md
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
uv run --script commands/doc-delete <document-id>
```

**Arguments**: `<document-id>` - Document ID from query results

**Example**:
```bash
uv run --script commands/doc-delete doc_abc123...
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

## doc-link

```bash
uv run --script commands/doc-link <action-flag> [arguments] [options]
```

**Actions** (mutually exclusive):
- `--types` - List available relation types
- `--create <from-doc-id> <to-doc-id>` - Create relation between documents
- `--update <relation-id>` - Update a relation's note
- `--remove <relation-id>` - Remove a relation (both directions)

### List Relation Types

```bash
uv run --script commands/doc-link --types
```

**Output**:
```json
[
  {
    "name": "parent-child",
    "description": "Hierarchical relation where parent owns children. Cascade delete enabled.",
    "from_document_is": "parent",
    "to_document_is": "child"
  },
  {
    "name": "related",
    "description": "Peer relation between related documents. No cascade delete.",
    "from_document_is": "related",
    "to_document_is": "related"
  }
]
```

### Create Relation

```bash
uv run --script commands/doc-link --create <from-doc-id> <to-doc-id> [options]
```

**Options**:
- `--type TEXT` or `-t TEXT` - Relation type: `parent-child` or `related` (required)
- `--from-to-note TEXT` - Note on edge from source to target (source's note about target)
- `--to-from-note TEXT` - Note on edge from target to source (target's note about source)

**Examples**:
```bash
# Create parent-child relation
uv run --script commands/doc-link --create doc_parent doc_child --type parent-child --from-to-note "Child module"

# Create peer relation
uv run --script commands/doc-link --create doc_a doc_b --type related --from-to-note "See also" --to-from-note "Related doc"
```

**Output**:
```json
{
  "success": true,
  "message": "Relation created",
  "from_relation": {
    "id": "rel_abc123",
    "document_id": "doc_parent",
    "related_document_id": "doc_child",
    "relation_type": "parent",
    "note": "Child module"
  },
  "to_relation": {
    "id": "rel_def456",
    "document_id": "doc_child",
    "related_document_id": "doc_parent",
    "relation_type": "child",
    "note": null
  }
}
```

### Update Relation Note

```bash
uv run --script commands/doc-link --update <relation-id> --note "New note text"
```

**Options**: `--note TEXT` or `-n TEXT` - New note text (required)

**Example**:
```bash
uv run --script commands/doc-link --update rel_abc123 --note "Updated: Core database module"
```

**Output**:
```json
{
  "id": "rel_abc123",
  "document_id": "doc_parent",
  "related_document_id": "doc_child",
  "relation_type": "parent",
  "note": "Updated: Core database module",
  "updated_at": "2025-12-03T10:30:00"
}
```

### Remove Relation

```bash
uv run --script commands/doc-link --remove <relation-id>
```

**Example**:
```bash
uv run --script commands/doc-link --remove rel_abc123
```

**Output**:
```json
{
  "success": true,
  "message": "Relation removed",
  "deleted_relation_ids": ["rel_abc123", "rel_def456"]
}
```

**Note**: Removes both sides of the bidirectional relation.

**Error Output** (stderr):
```json
{"error": "Relation not found: 123"}
{"error": "Document not found"}
{"error": "Relation already exists"}
```

---

## Exit Codes

- `0` - Success
- `1` - Error (JSON error in stderr)