# Context Store CLI Commands

Command-line tools for interacting with the Context Store Server. These UV-based scripts enable Claude Code sessions to store, retrieve, query, inspect, read, and delete documents with metadata and tags.

## Prerequisites

- **Python 3.11+** - Required for script dependencies
- **UV package manager** - For running scripts with automatic dependency management
- **Context Store Server** - Must be running (see `../../../../servers/context-store/README.md`)

## Available Commands

All commands output JSON for easy parsing and integration with Claude Code (except `doc-read`, which outputs raw text).

### doc-push - Upload Documents

Upload a document to the server with optional tags and description.

```bash
uv run --script /path/to/doc-push <file> [OPTIONS]
```

**Arguments:**
- `file` - Path to the file to upload (required)

**Options:**
- `--name TEXT` - Custom name for the document (defaults to filename)
- `--tags TEXT` - Comma-separated tags (e.g., "python,api,docs")
- `--description TEXT` - Document description

**Example:**
```bash
uv run --script doc-push architecture.md --tags "design,architecture" --description "System architecture document"
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
  "metadata": {"description": "System architecture document"},
  "url": "http://localhost:8766/documents/doc_abc123..."
}
```

### doc-query - Search Documents

Query documents by name pattern and/or tags.

```bash
uv run --script /path/to/doc-query [OPTIONS]
```

**Options:**
- `--name TEXT` - Filter by filename pattern (partial match)
- `--tags TEXT` - Comma-separated tags with AND logic (document must have ALL tags)
- `--limit INTEGER` - Maximum number of results

**Examples:**
```bash
# List all documents
uv run --script doc-query

# Find documents with specific tags (AND logic)
uv run --script doc-query --tags "python,tutorial"

# Filter by name pattern
uv run --script doc-query --name "architecture"

# Combine filters
uv run --script doc-query --name "guide" --tags "python" --limit 5
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
    "metadata": {},
    "url": "http://localhost:8766/documents/doc_abc123..."
  }
]
```

### doc-info - Get Document Metadata

Retrieve metadata for a specific document without downloading the file.

```bash
uv run --script /path/to/doc-info <document_id>
```

**Arguments:**
- `document_id` - The document's unique identifier (required)

**Example:**
```bash
uv run --script doc-info doc_abc123...
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
  "metadata": {"description": "System architecture document"},
  "url": "http://localhost:8766/documents/doc_abc123..."
}
```

**Use Case:** Check document metadata (file size, MIME type, tags) before downloading. The `url` field provides a direct link to retrieve the document, mostly interesting for the user or system having no access to the skill itself.

### doc-read - Read Text Documents

Read text document content directly to stdout without downloading to file.

```bash
uv run --script /path/to/doc-read <document_id>
```

**Arguments:**
- `document_id` - The document's unique identifier (required)

**Supported File Types:**
- Text files (`text/*`)
- JSON files (`application/json`)
- XML files (`application/xml`)

**Examples:**
```bash
# Output content to terminal
uv run --script doc-read doc_abc123...

# Pipe to grep
uv run --script doc-read doc_abc123... | grep "search term"

# Pipe to jq (for JSON documents)
uv run --script doc-read doc_abc123... | jq '.field'

# Save to file
uv run --script doc-read doc_abc123... > output.txt
```

**Output:** Raw text content (no JSON wrapper)

**Error (for non-text files):**
```json
{"error": "Cannot read non-text file (MIME type: image/png). Use doc-pull to download binary files."}
```

**Use Case:** Quick inspection of text files, piping content to other tools, processing documents in scripts without creating temporary files.

### doc-pull - Download Documents

Download a document by its ID.

```bash
uv run --script /path/to/doc-pull <document_id> [OPTIONS]
```

**Arguments:**
- `document_id` - The document's unique identifier (required)

**Options:**
- `--output PATH` or `-o PATH` - Output file path (defaults to original filename)

**Examples:**
```bash
# Download with original filename
uv run --script doc-pull doc_abc123...

# Download to specific path
uv run --script doc-pull doc_abc123... --output ~/downloads/my-document.md
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
uv run --script /path/to/doc-delete <document_id>
```

**Arguments:**
- `document_id` - The document's unique identifier (required)

**Example:**
```bash
uv run --script doc-delete doc_abc123...
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

Commands connect to the context store server using environment variables:

### DOC_SYNC_HOST
- **Description:** Server hostname or IP address
- **Default:** `localhost`
- **Example:**
  ```bash
  DOC_SYNC_HOST=192.168.1.100 uv run --script doc-push file.txt
  ```

### DOC_SYNC_PORT
- **Description:** Server port number
- **Default:** `8766`
- **Example:**
  ```bash
  DOC_SYNC_PORT=9000 uv run --script doc-query
  ```

### DOC_SYNC_SCHEME
- **Description:** HTTP scheme (http or https)
- **Default:** `http`
- **Example:**
  ```bash
  DOC_SYNC_SCHEME=https uv run --script doc-pull doc_abc123...
  ```

**Combined Example:**
```bash
DOC_SYNC_HOST=example.com DOC_SYNC_PORT=443 DOC_SYNC_SCHEME=https \
  uv run --script doc-push document.pdf --tags "report"
```

## Common Workflows

### Store and Retrieve a Document
```bash
# 1. Upload a document
uv run --script doc-push specs.md --tags "api,specification"

# Output includes the document ID: "doc_abc123..."

# 2. Later, query for it
uv run --script doc-query --tags "api,specification"

# 3. Check metadata before downloading
uv run --script doc-info doc_abc123...

# 4. Read content (for text files)
uv run --script doc-read doc_abc123... | less

# 5. Download it
uv run --script doc-pull doc_abc123... --output specs-copy.md
```

### Share Documents Across Sessions
```bash
# Session 1: Store architecture document
uv run --script doc-push architecture.md --tags "design,mvp" \
  --description "MVP architecture decisions"

# Session 2: Query and retrieve
uv run --script doc-query --tags "design,mvp"
uv run --script doc-info doc_abc123...  # Check metadata
uv run --script doc-read doc_abc123... | head -20  # Preview first 20 lines
uv run --script doc-pull doc_abc123... --output architecture.md
```

### Manage Document Repository
```bash
# List all documents
uv run --script doc-query

# Find specific category
uv run --script doc-query --tags "deprecated"

# Remove old documents
uv run --script doc-delete doc_old123...
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

**Non-text file (doc-read only):**
```json
{"error": "Cannot read non-text file (MIME type: image/png). Use doc-pull to download binary files."}
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
The context store server isn't running. Start it first:
```bash
cd ../../../../servers/context-store
uv run python -m src.main
```

### "No such file or directory" when running commands
Use full paths or navigate to the commands directory:
```bash
# Use full path
uv run --script /full/path/to/doc-push file.txt

# Or navigate to commands directory
cd /path/to/commands
uv run --script doc-push file.txt
```

### Commands run slowly the first time
UV is installing dependencies. Subsequent runs will be fast as dependencies are cached.
