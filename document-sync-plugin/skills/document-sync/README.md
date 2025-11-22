# Document Sync CLI Commands

Command-line tools for interacting with the Document Sync Server. These UV-based scripts enable Claude Code sessions to store, retrieve, query, and delete documents with metadata and tags.

## Prerequisites

- **Python 3.11+** - Required for script dependencies
- **UV package manager** - For running scripts with automatic dependency management
- **Document Server** - Must be running (see `../../document-server/README.md`)

## Available Commands

All commands output JSON for easy parsing and integration with Claude Code.

### doc-push - Upload Documents

Upload a document to the server with optional tags and description.

```bash
uv run /path/to/doc-push <file> [OPTIONS]
```

**Arguments:**
- `file` - Path to the file to upload (required)

**Options:**
- `--name TEXT` - Custom name for the document (defaults to filename)
- `--tags TEXT` - Comma-separated tags (e.g., "python,api,docs")
- `--description TEXT` - Document description

**Example:**
```bash
uv run doc-push architecture.md --tags "design,architecture" --description "System architecture document"
```

**Output:**
```json
{
  "id": "doc_abc123...",
  "filename": "architecture.md",
  "content_type": "text/markdown",
  "size_bytes": 2048,
  "created_at": "2025-11-23T00:00:00",
  "updated_at": "2025-11-23T00:00:00",
  "tags": ["design", "architecture"],
  "metadata": {"description": "System architecture document"}
}
```

### doc-query - Search Documents

Query documents by name pattern and/or tags.

```bash
uv run /path/to/doc-query [OPTIONS]
```

**Options:**
- `--name TEXT` - Filter by filename pattern (partial match)
- `--tags TEXT` - Comma-separated tags with AND logic (document must have ALL tags)
- `--limit INTEGER` - Maximum number of results

**Examples:**
```bash
# List all documents
uv run doc-query

# Find documents with specific tags (AND logic)
uv run doc-query --tags "python,tutorial"

# Filter by name pattern
uv run doc-query --name "architecture"

# Combine filters
uv run doc-query --name "guide" --tags "python" --limit 5
```

**Tag AND Logic:** When querying with multiple tags (e.g., `--tags "python,api"`), only documents that have **both** tags will be returned.

**Output:**
```json
[
  {
    "id": "doc_abc123...",
    "filename": "python-guide.md",
    "content_type": "text/markdown",
    "size_bytes": 1024,
    "created_at": "2025-11-23T00:00:00",
    "updated_at": "2025-11-23T00:00:00",
    "tags": ["python", "tutorial"],
    "metadata": {}
  }
]
```

### doc-pull - Download Documents

Download a document by its ID.

```bash
uv run /path/to/doc-pull <document_id> [OPTIONS]
```

**Arguments:**
- `document_id` - The document's unique identifier (required)

**Options:**
- `--output PATH` or `-o PATH` - Output file path (defaults to original filename)

**Examples:**
```bash
# Download with original filename
uv run doc-pull doc_abc123...

# Download to specific path
uv run doc-pull doc_abc123... --output ~/downloads/my-document.md
```

**Output:**
```json
{
  "success": true,
  "document_id": "doc_abc123...",
  "filename": "/path/to/output.md",
  "size_bytes": 2048
}
```

### doc-delete - Remove Documents

Delete a document from the server.

```bash
uv run /path/to/doc-delete <document_id>
```

**Arguments:**
- `document_id` - The document's unique identifier (required)

**Example:**
```bash
uv run doc-delete doc_abc123...
```

**Output:**
```json
{
  "success": true,
  "message": "Document doc_abc123... deleted successfully",
  "document_id": "doc_abc123..."
}
```

## Configuration

Commands connect to the document server using environment variables:

### DOC_SYNC_HOST
- **Description:** Server hostname or IP address
- **Default:** `localhost`
- **Example:**
  ```bash
  DOC_SYNC_HOST=192.168.1.100 uv run doc-push file.txt
  ```

### DOC_SYNC_PORT
- **Description:** Server port number
- **Default:** `8766`
- **Example:**
  ```bash
  DOC_SYNC_PORT=9000 uv run doc-query
  ```

### DOC_SYNC_SCHEME
- **Description:** HTTP scheme (http or https)
- **Default:** `http`
- **Example:**
  ```bash
  DOC_SYNC_SCHEME=https uv run doc-pull doc_abc123...
  ```

**Combined Example:**
```bash
DOC_SYNC_HOST=example.com DOC_SYNC_PORT=443 DOC_SYNC_SCHEME=https \
  uv run doc-push document.pdf --tags "report"
```

## Common Workflows

### Store and Retrieve a Document
```bash
# 1. Upload a document
uv run doc-push specs.md --tags "api,specification"

# Output includes the document ID: "doc_abc123..."

# 2. Later, query for it
uv run doc-query --tags "api,specification"

# 3. Download it
uv run doc-pull doc_abc123... --output specs-copy.md
```

### Share Documents Across Sessions
```bash
# Session 1: Store architecture document
uv run doc-push architecture.md --tags "design,mvp" \
  --description "MVP architecture decisions"

# Session 2: Query and retrieve
uv run doc-query --tags "design,mvp"
uv run doc-pull doc_abc123... --output architecture.md
```

### Manage Document Repository
```bash
# List all documents
uv run doc-query

# Find specific category
uv run doc-query --tags "deprecated"

# Remove old documents
uv run doc-delete doc_old123...
```

## Error Handling

All commands output errors to stderr in JSON format and exit with code 1 on failure.

**Common Errors:**

**File not found:**
```json
{"error": "File not found: /path/to/file.txt"}
```

**Document not found:**
```json
{"error": "Document not found: doc_invalid123"}
```

**Network error:**
```json
{"error": "Network error: Connection refused"}
```

**Server not running:**
```json
{"error": "Network error: [Errno 61] Connection refused"}
```

## Technical Details

### Script Architecture
- **UV Scripts:** Use PEP 723 inline dependency metadata
- **Shebang:** `#!/usr/bin/env -S uv run --script`
- **Dependencies:** Automatically installed by UV (httpx, typer)
- **Shared Library:** `lib/config.py` and `lib/client.py` provide reusable components

### Why UV?
- **Zero installation:** Scripts run with dependencies automatically installed
- **Reproducible:** PEP 723 metadata ensures consistent dependency versions
- **Fast:** UV's Rust-based resolver is extremely fast
- **Portable:** Scripts work across different environments

## Troubleshooting

### "Connection refused" error
The document server isn't running. Start it first:
```bash
cd ../../document-server
uv run python -m src.main
```

### "No such file or directory" when running commands
Use full paths or navigate to the commands directory:
```bash
# Use full path
uv run /full/path/to/doc-push file.txt

# Or navigate to commands directory
cd /path/to/commands
uv run doc-push file.txt
```

### Commands run slowly the first time
UV is installing dependencies. Subsequent runs will be fast as dependencies are cached.

## Development

See `../../docs/implementation/03-IMPLEMENTATION-CHECKLIST.md` for implementation details and design decisions.
