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

## doc-info

```bash
uv run commands/doc-info <document-id>
```

**Arguments**: `<document-id>` - Document ID to retrieve metadata for

**Examples**:
```bash
uv run commands/doc-info doc_abc123...
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
  "metadata": {"description": "API specification"}
}
```

**Use Case**: View document metadata without downloading the file. Useful for checking file size, MIME type, tags, and timestamps before downloading.

**Error Output** (stderr):
```json
{"error": "Document not found: doc_abc123..."}
```

---

## doc-read

```bash
uv run commands/doc-read <document-id>
```

**Arguments**: `<document-id>` - Document ID to read content from

**Examples**:
```bash
# Direct output
uv run commands/doc-read doc_abc123...

# Pipe to grep
uv run commands/doc-read doc_abc123... | grep "pattern"

# Pipe to wc
uv run commands/doc-read doc_abc123... | wc -l

# Save to file
uv run commands/doc-read doc_abc123... > output.txt
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