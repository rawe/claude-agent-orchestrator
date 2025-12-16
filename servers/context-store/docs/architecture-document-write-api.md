# Architecture Proposal: Document Write API

## Overview

This document proposes adding document creation and content writing capabilities to the Context Store API. The design introduces a **two-phase approach** that separates document creation from content writing, enabling agent workflows where document IDs are known before content is generated.

## Motivation

### Current Limitations

The existing API supports:
- `POST /documents` - Upload files with content (via `doc-push`)
- `GET /documents/{id}` - Read content
- `DELETE /documents/{id}` - Delete documents

**Missing capabilities:**
- Create document placeholders without content
- Write/update content to existing documents
- Agent-friendly workflows where ID is known upfront

### Use Cases

1. **Agent content generation**: Agent plans to create multiple documents, reserves IDs, then generates content
2. **Deferred content**: Create document metadata/structure first, fill content later
3. **Content updates**: Modify existing document content without re-uploading
4. **Iterative writing**: Create placeholder, write draft, refine with edits

## Design

### Two-Phase Approach

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  doc-create │   ───►  │  doc-write  │   ───►  │  doc-edit   │
│  (reserve)  │         │  (fill)     │         │  (refine)   │
└─────────────┘         └─────────────┘         └─────────────┘
     │                        │                       │
     ▼                        ▼                       ▼
  Returns ID            Full content            Surgical updates
  + metadata            replacement             (future)
```

**Benefits:**
- Clear ID lifecycle - ID known immediately before content exists
- Simple write operations - always operate on existing documents
- Agent-friendly - agents can plan document structure upfront
- Atomic metadata - tags, filename, relations set at creation time
- Queryable placeholders - documents visible before content written

### Comparison with Existing Tools

| Aspect | `doc-push` | `doc-create` + `doc-write` |
|--------|-----------|---------------------------|
| Input | File from filesystem | Content from memory/string |
| Steps | Single step | Two steps |
| Use case | Upload existing files | Agent-generated content |
| ID timing | Known after upload | Known before content |
| Content | Required immediately | Deferred |

Both patterns coexist - `doc-push` for human file uploads, `doc-create`/`doc-write` for agent workflows.

## API Specification

### `doc-create` - Create Placeholder Document

Creates a new document entry with metadata but no content.

#### Endpoint

```
POST /documents
Content-Type: application/json
```

#### Request Body

```json
{
  "filename": "architecture.md",
  "tags": ["design", "mvp"],
  "metadata": {
    "description": "System architecture overview"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filename` | string | Yes | Document filename (used for content-type inference) |
| `tags` | string[] | No | List of tags for querying |
| `metadata` | object | No | Key-value metadata pairs |

#### Response

**Status:** `201 Created`

```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "architecture.md",
  "content_type": "text/markdown",
  "size_bytes": 0,
  "checksum": null,
  "created_at": "2025-12-16T10:00:00.000000",
  "updated_at": "2025-12-16T10:00:00.000000",
  "tags": ["design", "mvp"],
  "metadata": {
    "description": "System architecture overview"
  },
  "url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

#### Behavior

1. Generate unique document ID (`doc_` + 24 hex characters)
2. Create empty file (0 bytes) in storage
3. Infer `content_type` from filename extension
4. Set `checksum` to `NULL` (no content to hash)
5. Set `size_bytes` to `0`
6. Set `created_at` and `updated_at` to current timestamp
7. Store tags and metadata in database
8. Return document response with generated ID

#### Content-Type Inference

| Extension | Content-Type |
|-----------|--------------|
| `.md` | `text/markdown` |
| `.txt` | `text/plain` |
| `.json` | `application/json` |
| `.yaml`, `.yml` | `application/x-yaml` |
| `.html` | `text/html` |
| `.xml` | `application/xml` |
| `.py` | `text/x-python` |
| `.js` | `text/javascript` |
| (unknown) | `application/octet-stream` |

---

### `doc-write` - Write Content to Document

Writes or replaces content of an existing document.

#### Endpoint

```
PUT /documents/{document_id}/content
Content-Type: text/plain
```

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `document_id` | string | Document ID (e.g., `doc_a1b2c3d4...`) |

#### Request Body

Raw content as request body:

```
# Architecture Overview

This document describes the system architecture...
```

#### Response

**Status:** `200 OK`

```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "architecture.md",
  "content_type": "text/markdown",
  "size_bytes": 1234,
  "checksum": "a1b2c3d4e5f6789...",
  "created_at": "2025-12-16T10:00:00.000000",
  "updated_at": "2025-12-16T10:05:00.000000",
  "tags": ["design", "mvp"],
  "metadata": {
    "description": "System architecture overview"
  },
  "url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

#### Behavior

1. Verify document exists (return `404` if not found)
2. Replace file content entirely (full replacement, not append)
3. Calculate SHA256 checksum of new content
4. Update `size_bytes` to new content length
5. Update `updated_at` to current timestamp
6. Preserve: `filename`, `content_type`, `tags`, `metadata`, `created_at`
7. Re-index for semantic search (if enabled)
8. Return updated document response

#### Error Responses

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Document ID does not exist |
| `500 Internal Server Error` | Storage write failure |

---

## Design Decisions

### Content-Type Handling

| Decision | Rationale |
|----------|-----------|
| Infer from filename extension | Automatic, intuitive, no extra parameters |
| Content-type is immutable | Filename is the "contract" - change filename to change type |
| Ignore Content-Type header on write | Trust document metadata, not request headers |
| No content validation | Lenient approach - trust the caller |

### Placeholder Behavior

| Decision | Rationale |
|----------|-----------|
| Empty file (0 bytes) | Simple, real file exists in storage |
| `checksum = NULL` | Distinguishes "never written" from "empty content with hash" |
| `size_bytes = 0` | Accurate representation |
| Visible in queries | Users can find placeholders to write to |
| No expiration/cleanup | Placeholders are valid empty documents |

### Write Semantics

| Decision | Rationale |
|----------|-----------|
| Full replacement | Matches Claude's Write tool behavior |
| Last write wins | Simple, no locking complexity |
| Re-index on write | Keep semantic search up to date |
| Preserve metadata on write | Write only affects content, not document properties |

### Checksum Behavior

| State | Checksum Value |
|-------|----------------|
| After `doc-create` (placeholder) | `NULL` |
| After `doc-write` (with content) | SHA256 hash of content |
| After `doc-write` (empty content) | SHA256 of empty string |

Note: Writing empty content intentionally results in the SHA256 hash of an empty string, which differs from `NULL` (never written).

---

## Database Schema Changes

### Modified: `documents` Table

The `checksum` column must allow `NULL` values:

```sql
-- Existing column (verify nullable)
checksum TEXT  -- NULL for placeholders, SHA256 for written content
```

No new columns required. The `size_bytes = 0` and `checksum IS NULL` combination indicates a placeholder.

---

## Semantic Search Re-indexing

When semantic search is enabled (Elasticsearch + Ollama embeddings), document content changes must trigger re-indexing.

### Current Indexing Flow (doc-push)

```
Upload → Store file → Index in Elasticsearch
                            ↓
                      1. Chunk content (1000 chars, 200 overlap)
                      2. Generate embeddings via Ollama
                      3. Store vectors with document_id + offsets
```

### Required Changes for doc-write

#### On `doc-create` (placeholder)

- **Do NOT index** - No content to embed
- Placeholder has `size_bytes = 0`, skip indexing

#### On `doc-write` (content written)

```
Write content → Update file → Re-index in Elasticsearch
                                    ↓
                              1. Delete existing chunks for document_id
                              2. Chunk new content
                              3. Generate new embeddings
                              4. Store new vectors
```

### Implementation in Storage Layer

The `storage.py` module must call the semantic indexer on write:

```python
# In storage.py - write_document_content() method

async def write_document_content(self, document_id: str, content: bytes) -> DocumentMetadata:
    """Write content to an existing document."""
    # 1. Get existing document metadata
    metadata = self.get_document(document_id)
    if not metadata:
        raise DocumentNotFoundError(document_id)

    # 2. Write file content
    with open(metadata.storage_path, 'wb') as f:
        f.write(content)

    # 3. Update database (size, checksum, updated_at)
    new_checksum = hashlib.sha256(content).hexdigest()
    self.db.update_document(
        document_id,
        size_bytes=len(content),
        checksum=new_checksum,
        updated_at=datetime.utcnow()
    )

    # 4. Re-index for semantic search (if enabled)
    if self.semantic_indexer:
        # Delete old chunks first
        await self.semantic_indexer.delete_document(document_id)
        # Index new content (only if non-empty)
        if len(content) > 0:
            await self.semantic_indexer.index_document(
                document_id=document_id,
                content=content.decode('utf-8'),
                filename=metadata.filename
            )

    return self.get_document(document_id)
```

### Indexer Interface

Reference the existing semantic indexer (`src/semantic/indexer.py`):

| Method | Purpose |
|--------|---------|
| `index_document(document_id, content, filename)` | Chunk, embed, and store vectors |
| `delete_document(document_id)` | Remove all chunks for a document |

### Edge Cases

| Scenario | Indexing Behavior |
|----------|-------------------|
| `doc-create` (placeholder) | Skip indexing |
| `doc-write` to placeholder | Index new content |
| `doc-write` to existing content | Delete old chunks, index new |
| `doc-write` empty content | Delete old chunks, skip indexing |
| `doc-delete` | Delete chunks (already implemented) |

### Text-Only Indexing

Semantic search only applies to text content types. Check before indexing:

```python
TEXT_CONTENT_TYPES = {
    'text/plain', 'text/markdown', 'text/html',
    'application/json', 'application/xml',
    'application/x-yaml', 'text/x-python',
    # ... other text types
}

if metadata.content_type in TEXT_CONTENT_TYPES:
    await self.semantic_indexer.index_document(...)
```

---

## CLI Commands

CLI commands are located in the plugin's skills directory:

```
plugins/context-store/skills/context-store/commands/
├── doc-create    # (new) Create placeholder document
├── doc-write     # (new) Write content to document
├── doc-delete
├── doc-info
├── doc-link
├── doc-pull
├── doc-push
├── doc-query
├── doc-read
├── doc-search
└── lib/
```

### `doc-create`

**Path:** `plugins/context-store/skills/context-store/commands/doc-create`

```bash
uv run plugins/context-store/skills/context-store/commands/doc-create \
  --name "architecture.md" \
  --tags "design,mvp" \
  --description "System architecture overview"
```

**Output:**
```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "architecture.md",
  "size_bytes": 0,
  "url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

### `doc-write`

**Path:** `plugins/context-store/skills/context-store/commands/doc-write`

```bash
# From stdin
echo "# Content here" | uv run plugins/context-store/skills/context-store/commands/doc-write doc_a1b2c3d4...

# From file
uv run plugins/context-store/skills/context-store/commands/doc-write doc_a1b2c3d4... < content.md

# Inline content (if supported)
uv run plugins/context-store/skills/context-store/commands/doc-write doc_a1b2c3d4... --content "# Content here"
```

**Output:**
```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "architecture.md",
  "size_bytes": 1234,
  "checksum": "a1b2c3d4..."
}
```

---

## MCP Server Changes

The MCP server is located at `mcps/context-store/context-store-mcp.py` and acts as a thin 1:1 wrapper around CLI commands. Each tool follows this pattern:

```python
@mcp.tool()
async def doc_xxx(params...) -> str:
    """Docstring with description and examples"""
    args = [...]  # Build CLI arguments
    stdout, stderr, code = await run_command("doc-xxx", args)
    return format_response(stdout, stderr, code)
```

### Update Server Instructions

Update the FastMCP initialization to document new capabilities:

```python
mcp = FastMCP(
    "context-store-mcp-server",
    instructions="""Context Store MCP Server - Document management system.

Use this server to:
- Create placeholder documents (doc_create) and write content later (doc_write)
- Store documents with metadata and tags (doc_push for files)
- Query documents by name or tags
- Semantic search for documents by meaning
- Read document content (full or partial)
- Download documents to local filesystem
- Manage document relations (parent-child, peer links)

Workflow for agent-generated content:
1. doc_create(filename="doc.md", tags="...") → returns document ID
2. doc_write(document_id="doc_xxx", content="...") → fills the content
""",
)
```

### Add `doc_create` Tool

```python
@mcp.tool()
async def doc_create(
    filename: str = Field(
        description="Document filename (e.g., 'notes.md'). Used to infer content type.",
    ),
    tags: Optional[str] = Field(
        default=None,
        description="Comma-separated tags for categorization",
    ),
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the document",
    ),
) -> str:
    """Create a placeholder document in the Context Store.

    Creates an empty document with metadata. Use doc_write to add content later.
    This two-phase approach lets you reserve document IDs before generating content.

    Returns:
        JSON with document metadata: id, filename, content_type, size_bytes (0), url

    Example:
        doc_create(filename="architecture.md", tags="design,mvp", description="System overview")
    """
    args = ["--name", filename]
    if tags:
        args.extend(["--tags", tags])
    if description:
        args.extend(["--description", description])

    stdout, stderr, code = await run_command("doc-create", args)
    return format_response(stdout, stderr, code)
```

### Add `doc_write` Tool

```python
@mcp.tool()
async def doc_write(
    document_id: str = Field(
        description="The document ID to write to",
    ),
    content: str = Field(
        description="The full content to write (replaces existing content)",
    ),
) -> str:
    """Write content to an existing document (full replacement).

    Replaces the entire content of a document. Use after doc_create to fill
    placeholder documents, or to update existing document content.

    Returns:
        JSON with updated document metadata: id, filename, size_bytes, checksum

    Example:
        doc_write(document_id="doc_abc123", content="# My Document\\n\\nContent here...")
    """
    args = [document_id, "--content", content]

    stdout, stderr, code = await run_command("doc-write", args)
    return format_response(stdout, stderr, code)
```

### Content Passing Strategy

The `doc_write` tool needs to pass potentially large content to the CLI command.

| Method | Pros | Cons |
|--------|------|------|
| `--content` arg | Simple, works with current pattern | Shell escaping issues, arg length limits |
| stdin pipe | No length limits, clean | Requires modified `run_command` |
| Temp file | Reliable for large content | Extra I/O, cleanup needed |

**Recommended approach:** Use `--content` for simplicity. For large content (>100KB), use stdin:

```python
async def run_command_with_stdin(command: str, args: list[str], stdin_data: Optional[str] = None) -> tuple[str, str, int]:
    """Execute a doc-* command with optional stdin input."""
    cmd_path = COMMAND_PATH / command
    full_args = ["uv", "run", str(cmd_path)] + args

    process = await asyncio.create_subprocess_exec(
        *full_args,
        stdin=subprocess.PIPE if stdin_data else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await process.communicate(input=stdin_data.encode() if stdin_data else None)
    return stdout.decode(), stderr.decode(), process.returncode or 0
```

**Updated `doc_write` with large content handling:**

```python
@mcp.tool()
async def doc_write(
    document_id: str = Field(
        description="The document ID to write to",
    ),
    content: str = Field(
        description="The full content to write (replaces existing content)",
    ),
) -> str:
    """Write content to an existing document (full replacement).

    Replaces the entire content of a document. Use after doc_create to fill
    placeholder documents, or to update existing document content.

    Returns:
        JSON with updated document metadata: id, filename, size_bytes, checksum

    Example:
        doc_write(document_id="doc_abc123", content="# My Document\\n\\nContent here...")
    """
    LARGE_CONTENT_THRESHOLD = 100_000  # 100KB

    if len(content) > LARGE_CONTENT_THRESHOLD:
        # Use stdin for large content
        stdout, stderr, code = await run_command_with_stdin(
            "doc-write", [document_id], stdin_data=content
        )
    else:
        # Use --content argument for small content
        args = [document_id, "--content", content]
        stdout, stderr, code = await run_command("doc-write", args)

    return format_response(stdout, stderr, code)
```

The CLI command must support both modes:
- `doc-write <document_id> --content "..."` for argument-based content
- `echo "..." | doc-write <document_id>` for stdin-based content

---

## Workflow Examples

### Agent Creating Documentation

```
Agent: "I'll create architecture documentation with 3 sections"

1. doc-create --name "overview.md" --tags "architecture"
   → Returns doc_001

2. doc-create --name "database.md" --tags "architecture,database"
   → Returns doc_002

3. doc-create --name "api.md" --tags "architecture,api"
   → Returns doc_003

4. doc-write doc_001 "# System Overview..."
5. doc-write doc_002 "# Database Design..."
6. doc-write doc_003 "# API Specification..."
```

### Iterative Content Development

```
1. doc-create --name "draft.md" --tags "wip"
   → Returns doc_abc

2. doc-write doc_abc "# First draft..."

3. [Agent reviews, decides to rewrite]

4. doc-write doc_abc "# Revised content..."  (replaces entirely)
```

---

## `doc-edit` - Surgical Content Updates

Partial document editing with two modes: **string replacement** (like Claude's Edit tool) and **offset-based** (symmetric with partial reads).

### Endpoint

```
PATCH /documents/{document_id}/content
Content-Type: application/json
```

### Mode 1: String Replacement

Find and replace text within the document.

#### Request Body

```json
{
  "old_string": "## Old Section\nOld content",
  "new_string": "## Updated Section\nNew content",
  "replace_all": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `old_string` | string | Yes (for this mode) | Text to find and replace |
| `new_string` | string | Yes | Replacement text |
| `replace_all` | boolean | No | `false` (default): replace first unique match. `true`: replace all occurrences |

#### Error Handling (Claude Edit Semantics)

| Condition | Response |
|-----------|----------|
| `old_string` not found | `400 Bad Request` - "old_string not found in document" |
| Multiple matches + `replace_all=false` | `400 Bad Request` - "old_string matches N times; use replace_all=true or provide more context" |
| Document not found | `404 Not Found` |

#### Response

**Status:** `200 OK`

```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "architecture.md",
  "content_type": "text/markdown",
  "size_bytes": 1250,
  "checksum": "b2c3d4e5f6789...",
  "created_at": "2025-12-16T10:00:00.000000",
  "updated_at": "2025-12-16T10:10:00.000000",
  "replacements_made": 1
}
```

---

### Mode 2: Offset-Based Edit

Insert, replace, or delete content at a specific character position. Symmetric with `GET /documents/{id}?offset=X&limit=Y`.

#### Request Body

```json
{
  "offset": 2000,
  "length": 500,
  "new_string": "replacement text"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `offset` | integer | Yes (for this mode) | Starting character position (0-indexed) |
| `length` | integer | No | Number of characters to replace. `0` or omitted = insert at offset |
| `new_string` | string | Yes | Text to insert/replace with. Empty string = delete |

#### Operations

| `length` | `new_string` | Operation |
|----------|--------------|-----------|
| 0 or omitted | non-empty | **Insert** at offset |
| > 0 | non-empty | **Replace** characters [offset, offset+length) |
| > 0 | empty `""` | **Delete** characters [offset, offset+length) |

#### Error Handling

| Condition | Response |
|-----------|----------|
| `offset` < 0 | `400 Bad Request` - "offset must be non-negative" |
| `offset` > document length | `400 Bad Request` - "offset N exceeds document length M" |
| `offset + length` > document length | `400 Bad Request` - "range exceeds document length" |
| Document not found | `404 Not Found` |

#### Response

**Status:** `200 OK`

```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "architecture.md",
  "content_type": "text/markdown",
  "size_bytes": 1300,
  "checksum": "c3d4e5f6789...",
  "created_at": "2025-12-16T10:00:00.000000",
  "updated_at": "2025-12-16T10:15:00.000000",
  "edit_range": {
    "offset": 2000,
    "old_length": 500,
    "new_length": 550
  }
}
```

---

### Mode Detection

The server determines mode by which fields are present:

| Fields Present | Mode |
|----------------|------|
| `old_string` | String replacement |
| `offset` | Offset-based |
| Both | `400 Bad Request` - "cannot mix old_string and offset modes" |
| Neither | `400 Bad Request` - "must provide old_string or offset" |

---

### Semantic Search Re-indexing

On edit:
1. Delete existing chunks for document
2. Re-chunk and re-index entire document

(Future optimization: partial re-indexing for offset-based edits)

---

## CLI Command: `doc-edit`

**Path:** `plugins/context-store/skills/context-store/commands/doc-edit`

### String Replacement Mode

```bash
# Simple replacement (must be unique match)
doc-edit <document_id> --old-string "old text" --new-string "new text"

# Replace all occurrences
doc-edit <document_id> --old-string "old text" --new-string "new text" --replace-all

# Multi-line strings via stdin (JSON format)
echo '{"old_string": "line1\nline2", "new_string": "new line1\nnew line2"}' | doc-edit <document_id> --json

# Or with heredoc
doc-edit <document_id> --json <<'EOF'
{
  "old_string": "## Old Section\nOld content here",
  "new_string": "## New Section\nUpdated content"
}
EOF
```

### Offset-Based Mode

```bash
# Insert at position
doc-edit <document_id> --offset 2000 --new-string "text to insert"

# Replace range
doc-edit <document_id> --offset 2000 --length 500 --new-string "replacement"

# Delete range
doc-edit <document_id> --offset 2000 --length 500 --new-string ""
```

### CLI Arguments

| Argument | Description |
|----------|-------------|
| `document_id` | Document ID (positional, required) |
| `--old-string` | Text to find (string replacement mode) |
| `--new-string` | Replacement/insert text |
| `--replace-all` | Replace all occurrences (default: false) |
| `--offset` | Character position (offset mode) |
| `--length` | Characters to replace (offset mode, default: 0) |
| `--json` | Read edit spec from stdin as JSON |

### Output

```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "architecture.md",
  "size_bytes": 1250,
  "checksum": "b2c3d4e5f6789...",
  "replacements_made": 1
}
```

---

## MCP Tool: `doc_edit`

```python
@mcp.tool()
async def doc_edit(
    document_id: str = Field(
        description="The document ID to edit",
    ),
    old_string: Optional[str] = Field(
        default=None,
        description="Text to find and replace (string replacement mode)",
    ),
    new_string: str = Field(
        description="Replacement text, or text to insert (offset mode)",
    ),
    replace_all: bool = Field(
        default=False,
        description="Replace all occurrences (only for string replacement mode)",
    ),
    offset: Optional[int] = Field(
        default=None,
        description="Character position for offset-based edit",
    ),
    length: Optional[int] = Field(
        default=None,
        description="Characters to replace at offset (0 = insert)",
    ),
) -> str:
    """Edit document content surgically without full replacement.

    Two modes:
    1. String replacement: Provide old_string + new_string (like Claude's Edit tool)
    2. Offset-based: Provide offset + new_string (+ optional length)

    String replacement follows Claude Edit semantics:
    - old_string must be found in document (error if not)
    - old_string must be unique unless replace_all=true (error if ambiguous)

    Returns:
        JSON with updated document metadata and edit details

    Examples:
        # String replacement
        doc_edit(document_id="doc_abc", old_string="old text", new_string="new text")

        # Replace all occurrences
        doc_edit(document_id="doc_abc", old_string="TODO", new_string="DONE", replace_all=True)

        # Insert at position
        doc_edit(document_id="doc_abc", offset=100, new_string="inserted text")

        # Replace range
        doc_edit(document_id="doc_abc", offset=100, length=50, new_string="replacement")
    """
```

### Large Content Handling

Like `doc_write`, use stdin for content > 100KB:

```python
LARGE_CONTENT_THRESHOLD = 100_000  # 100KB

if len(new_string) > LARGE_CONTENT_THRESHOLD or (old_string and len(old_string) > LARGE_CONTENT_THRESHOLD):
    # Build JSON payload and pass via stdin
    payload = {"new_string": new_string}
    if old_string:
        payload["old_string"] = old_string
        payload["replace_all"] = replace_all
    else:
        payload["offset"] = offset
        if length:
            payload["length"] = length

    stdout, stderr, code = await run_command_with_stdin(
        "doc-edit", [document_id, "--json"], stdin_data=json.dumps(payload)
    )
else:
    # Use arguments for small content
    args = [document_id]
    if old_string:
        args.extend(["--old-string", old_string, "--new-string", new_string])
        if replace_all:
            args.append("--replace-all")
    else:
        args.extend(["--offset", str(offset), "--new-string", new_string])
        if length:
            args.extend(["--length", str(length)])

    stdout, stderr, code = await run_command("doc-edit", args)
```

---

## Workflow Examples

### Iterative Document Refinement

```
1. doc-create --name "report.md" --tags "draft"
   → doc_001

2. doc-write doc_001 "# Report\n\n## Section 1\nInitial content..."

3. [Agent reviews, wants to fix a section]

4. doc-edit doc_001 --old-string "## Section 1\nInitial content" --new-string "## Section 1\nRevised content"

5. [Agent wants to insert a new section]

6. doc-edit doc_001 --offset 500 --new-string "\n\n## New Section\nAdditional content\n"
```

### Find and Replace Across Document

```
# Replace all TODO markers
doc-edit doc_001 --old-string "TODO:" --new-string "DONE:" --replace-all
```

---

## Implementation Checklist

### doc-create / doc-write (Completed)

- [x] Add `PUT /documents/{document_id}/content` endpoint
- [x] Modify `POST /documents` to support JSON body without file (placeholder mode)
- [x] Update database to ensure `checksum` column allows NULL
- [x] Implement content-type inference from filename
- [x] Add semantic search re-indexing on content write
- [x] Create `doc-create` CLI command
- [x] Create `doc-write` CLI command
- [x] Add `doc_create` MCP tool
- [x] Add `doc_write` MCP tool

### doc-edit (Completed)

- [x] Add `PATCH /documents/{document_id}/content` endpoint
- [x] Implement string replacement with uniqueness check
- [x] Implement offset-based insert/replace/delete
- [x] Add semantic search re-indexing on edit
- [x] Create `doc-edit` CLI command
- [x] Add `doc_edit` MCP tool
- [x] Update README documentation
- [x] Add integration tests

---

## References

- [Context Store Server README](../README.md)
- [Claude Code Edit Tool](https://docs.anthropic.com/claude-code) - Inspiration for edit semantics
- [ADR-001: Relation API Naming](./ADR-001-relation-api-naming.md)
