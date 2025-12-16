# Context Store Server

FastAPI server for storing context documents. This server provides RESTful API endpoints for uploading, retrieving, querying, and deleting documents with metadata and tag support.

The server also supports **semantic search** (optional) using embeddings to find documents by meaning rather than exact keyword matches.

## Prerequisites

- **Python 3.11+** - Required for modern type hints and async support
- **UV package manager** - Fast Python package installer and resolver

## Installation

1. Navigate to the context-store directory:
   ```bash
   cd servers/context-store
   ```

2. Install dependencies using UV:
   ```bash
   uv sync
   ```

   This will create a virtual environment and install all required packages (FastAPI, Uvicorn, python-multipart).

## Starting the Server

### Option 1: Using Docker (Recommended)

From the project root:
```bash
cd ..
docker-compose up -d
```

The server will be available at `http://localhost:8766`

Check health:
```bash
curl http://localhost:8766/health
```

### Option 2: Running Locally

Run the server using UV:

```bash
uv run python -m src.main
```

The server will start on `http://0.0.0.0:8766` by default with auto-reload enabled for development.

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8766 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Application startup complete.
```

## Available Endpoints

### GET /health

Health check endpoint for monitoring and Docker health checks.

**Example**:
```bash
curl http://localhost:8766/health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "context-store-server"
}
```

### POST /documents

Create a new document. Supports two modes based on `Content-Type` header:

#### Mode 1: Upload File (multipart/form-data)

Upload a file with content and optional metadata.

- **Request format**: `multipart/form-data`
- **Parameters**:
  - `file` (required): File to upload
  - `tags` (optional): Comma-separated list of tags (e.g., "documentation,example")
  - `metadata` (optional): JSON string with key-value pairs. Use `description` to provide a human-readable summary of the document's purpose or content.
- **Response**: 201 Created with `DocumentResponse`

**Example**:
```bash
curl -X POST http://localhost:8766/documents \
  -F "file=@example.md" \
  -F "tags=documentation,example" \
  -F "metadata={\"description\":\"API usage guide for the authentication module\"}"
```

#### Mode 2: Create Placeholder (application/json)

Create an empty document with metadata. Use `PUT /documents/{id}/content` to add content later.
This is useful for agent workflows where you need to know the document ID before generating content.

- **Request format**: `application/json`
- **Body**:
  - `filename` (required): Document filename (used for content-type inference)
  - `tags` (optional): Array of tags
  - `metadata` (optional): Key-value pairs
- **Response**: 201 Created with `DocumentResponse` (size_bytes=0, checksum=null)

**Example**:
```bash
curl -X POST http://localhost:8766/documents \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "architecture.md",
    "tags": ["design", "mvp"],
    "metadata": {"description": "System architecture overview"}
  }'
```

**Response** (placeholder):
```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "architecture.md",
  "content_type": "text/markdown",
  "size_bytes": 0,
  "checksum": null,
  "created_at": "2025-11-22T12:34:56.789012",
  "updated_at": "2025-11-22T12:34:56.789012",
  "tags": ["design", "mvp"],
  "metadata": {"description": "System architecture overview"},
  "url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

**Response** (file upload):
```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "example.md",
  "content_type": "text/markdown",
  "size_bytes": 1234,
  "checksum": "a1b2c3d4e5f6...",
  "created_at": "2025-11-22T12:34:56.789012",
  "updated_at": "2025-11-22T12:34:56.789012",
  "tags": ["documentation", "example"],
  "metadata": {"description": "API usage guide for the authentication module"},
  "url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

The server generates a unique document ID, detects the MIME type from the filename, and provides a fully qualified URL for document retrieval.

### PUT /documents/{document_id}/content

Write or replace content of an existing document. Use after creating a placeholder with `POST /documents` (JSON mode).

- **Path parameter**: `document_id` - The document's unique identifier
- **Request body**: Raw content (any content type)
- **Response**: 200 OK with `DocumentResponse`

**Example**:
```bash
# Write content to a placeholder document
curl -X PUT http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2/content \
  -H "Content-Type: text/plain" \
  -d '# Architecture Overview

This document describes the system architecture...'
```

**Response**:
```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "architecture.md",
  "content_type": "text/markdown",
  "size_bytes": 67,
  "checksum": "a1b2c3d4e5f6...",
  "created_at": "2025-11-22T12:34:56.789012",
  "updated_at": "2025-11-22T12:35:00.123456",
  "tags": ["design", "mvp"],
  "metadata": {"description": "System architecture overview"},
  "url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

**Behavior**:
- Replaces the entire document content (full replacement, not append)
- Calculates SHA256 checksum of new content
- Updates `size_bytes` and `updated_at`
- Re-indexes for semantic search if enabled
- Preserves `filename`, `content_type`, `tags`, `metadata`, `created_at`

**Error Responses**:
- `404`: Document not found
- `500`: Storage write failure

**Two-Phase Workflow**:
```bash
# 1. Create placeholder (get ID immediately)
curl -X POST http://localhost:8766/documents \
  -H "Content-Type: application/json" \
  -d '{"filename": "report.md", "tags": ["report"]}'
# Returns: {"id": "doc_abc123", ...}

# 2. Generate content (agent work happens here)

# 3. Write content to the document
curl -X PUT http://localhost:8766/documents/doc_abc123/content \
  -d '# Report Content...'
```

### PATCH /documents/{document_id}/content

Edit content of an existing document surgically without full replacement. Supports two modes:

1. **String Replacement Mode**: Find and replace text (like Claude's Edit tool)
2. **Offset-Based Mode**: Insert, replace, or delete at a specific character position

- **Path parameter**: `document_id` - The document's unique identifier
- **Request body**: JSON with edit parameters
- **Response**: 200 OK with `DocumentResponse` plus edit details

#### Mode 1: String Replacement

Find and replace text within the document. Follows Claude Edit semantics:
- `old_string` must be found in document (error if not)
- `old_string` must be unique unless `replace_all=true` (error if ambiguous)

**Request Body**:
```json
{
  "old_string": "text to find",
  "new_string": "replacement text",
  "replace_all": false
}
```

**Examples**:
```bash
# Simple replacement (must be unique match)
curl -X PATCH http://localhost:8766/documents/doc_abc123/content \
  -H "Content-Type: application/json" \
  -d '{"old_string": "TODO", "new_string": "DONE"}'

# Replace all occurrences
curl -X PATCH http://localhost:8766/documents/doc_abc123/content \
  -H "Content-Type: application/json" \
  -d '{"old_string": "TODO", "new_string": "DONE", "replace_all": true}'
```

**Response** (string replacement):
```json
{
  "id": "doc_abc123",
  "filename": "notes.md",
  "content_type": "text/markdown",
  "size_bytes": 1250,
  "checksum": "b2c3d4e5f6...",
  "created_at": "2025-12-16T10:00:00",
  "updated_at": "2025-12-16T10:10:00",
  "tags": ["notes"],
  "metadata": {},
  "url": "http://localhost:8766/documents/doc_abc123",
  "replacements_made": 3
}
```

#### Mode 2: Offset-Based

Insert, replace, or delete content at a specific character position.

**Request Body**:
```json
{
  "offset": 100,
  "length": 50,
  "new_string": "replacement text"
}
```

| `length` | `new_string` | Operation |
|----------|--------------|-----------|
| 0 or omitted | non-empty | **Insert** at offset |
| > 0 | non-empty | **Replace** characters [offset, offset+length) |
| > 0 | empty `""` | **Delete** characters [offset, offset+length) |

**Examples**:
```bash
# Insert at position 100
curl -X PATCH http://localhost:8766/documents/doc_abc123/content \
  -H "Content-Type: application/json" \
  -d '{"offset": 100, "new_string": "inserted text"}'

# Replace characters 100-150
curl -X PATCH http://localhost:8766/documents/doc_abc123/content \
  -H "Content-Type: application/json" \
  -d '{"offset": 100, "length": 50, "new_string": "replacement"}'

# Delete characters 100-150
curl -X PATCH http://localhost:8766/documents/doc_abc123/content \
  -H "Content-Type: application/json" \
  -d '{"offset": 100, "length": 50, "new_string": ""}'
```

**Response** (offset-based):
```json
{
  "id": "doc_abc123",
  "filename": "notes.md",
  "content_type": "text/markdown",
  "size_bytes": 1300,
  "checksum": "c3d4e5f6...",
  "created_at": "2025-12-16T10:00:00",
  "updated_at": "2025-12-16T10:15:00",
  "tags": ["notes"],
  "metadata": {},
  "url": "http://localhost:8766/documents/doc_abc123",
  "edit_range": {
    "offset": 100,
    "old_length": 50,
    "new_length": 11
  }
}
```

**Error Responses**:
- `400`: `old_string` not found in document
- `400`: `old_string` matches multiple times (use `replace_all=true`)
- `400`: Cannot mix `old_string` and `offset` modes
- `400`: Must provide `old_string` or `offset`
- `400`: Offset out of bounds
- `400`: Edit only supported for text content types
- `404`: Document not found

**Note**: The edit endpoint only supports text content types (`text/*`). Attempting to edit binary files will return a 400 error.

### GET /documents

Query documents with optional filtering by filename and/or tags.

- **Query parameters**:
  - `filename` (optional): Partial filename match (e.g., "example" matches "example.md")
  - `tags` (optional): Comma-separated tags - uses AND logic (document must have ALL tags)
  - `limit` (default: 100): Maximum number of results
  - `offset` (default: 0): Pagination offset
  - `include_relations` (default: false): Include document relations in response
- **Response**: 200 OK with array of `DocumentResponse`

**Examples**:
```bash
# List all documents
curl http://localhost:8766/documents

# Filter by filename
curl "http://localhost:8766/documents?filename=example"

# Filter by single tag
curl "http://localhost:8766/documents?tags=documentation"

# Filter by multiple tags (AND logic - must have ALL tags)
curl "http://localhost:8766/documents?tags=documentation,example"

# Combine filename and tags
curl "http://localhost:8766/documents?filename=guide&tags=python"

# Include relations in response
curl "http://localhost:8766/documents?include_relations=true"
```

**Tag AND Logic**: When querying with multiple tags (e.g., `tags=python,tutorial`), only documents that have BOTH tags will be returned.

**Relations**: When `include_relations=true`, each document includes a `relations` field grouped by relation type:
```json
{
  "id": "doc_a1b2c3d4",
  "filename": "example.md",
  "relations": {
    "parent": [
      {"id": "1", "related_document_id": "doc_child1", "relation_type": "parent", "note": "Child document"}
    ]
  }
}
```

### GET /documents/{document_id}/metadata

Retrieve metadata for a specific document without downloading the file content.

- **Path parameter**: `document_id` - The document's unique identifier
- **Response**: 200 OK with `DocumentResponse` (JSON metadata only)

**Example**:
```bash
curl http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2/metadata
```

**Success Response**:
```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "example.md",
  "content_type": "text/markdown",
  "size_bytes": 1234,
  "created_at": "2025-11-22T12:34:56.789012",
  "updated_at": "2025-11-22T12:34:56.789012",
  "tags": ["documentation", "example"],
  "metadata": {"author": "John Doe", "version": "1.0"},
  "url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

**Error Response** (404 if not found):
```json
{
  "detail": "Document not found"
}
```

**Use Case**: Check document metadata (file size, MIME type, tags, timestamps) before downloading. The `url` field provides a direct link to retrieve the document content. Useful for filtering or validating documents without transferring the full file content.

### GET /search

Semantic search across indexed documents. Only available when semantic search is enabled.

- **Query parameters**:
  - `q` (required): Natural language search query
  - `limit` (default: 10): Maximum number of documents to return (1-100)
  - `include_relations` (default: false): Include document relations in response
- **Response**: 200 OK with `SearchResponse`

**Example**:
```bash
curl "http://localhost:8766/search?q=how%20to%20configure%20authentication&limit=5"

# Include relations in search results
curl "http://localhost:8766/search?q=authentication&include_relations=true"
```

**Success Response**:
```json
{
  "query": "how to configure authentication",
  "results": [
    {
      "document_id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
      "filename": "auth-guide.md",
      "document_url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2",
      "sections": [
        { "score": 0.92, "offset": 2000, "limit": 1000 },
        { "score": 0.85, "offset": 5000, "limit": 1000 }
      ]
    }
  ]
}
```

**Response with Relations** (when `include_relations=true`):
```json
{
  "query": "authentication",
  "results": [
    {
      "document_id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
      "filename": "auth-guide.md",
      "document_url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2",
      "sections": [
        { "score": 0.92, "offset": 2000, "limit": 1000 }
      ],
      "relations": {
        "child": [
          {"id": "5", "related_document_id": "doc_parent", "relation_type": "child", "note": "Part of security docs"}
        ]
      }
    }
  ]
}
```

**Response Fields**:
- `document_id`: Unique identifier of the matching document
- `filename`: Original filename
- `document_url`: Direct URL to retrieve the document
- `sections`: List of matching sections with:
  - `score`: Similarity score (0-1, higher is more relevant)
  - `offset`: Character position where the matching section starts
  - `limit`: Number of characters in the section
- `relations` (optional): Document relations grouped by type (only when `include_relations=true`)

**Error Response** (404 if semantic search is disabled):
```json
{
  "detail": "Semantic search is not enabled"
}
```

**Workflow**: Use the `offset` and `limit` from search results to retrieve only the relevant section:
```bash
# Get the matching section directly
curl "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2?offset=2000&limit=1000"
```

### GET /documents/{document_id}

Download a document by ID. Returns the file content with appropriate headers.

- **Path parameter**: `document_id` - The document's unique identifier
- **Query parameters** (optional, for text content types only):
  - `offset`: Starting character position (0-indexed)
  - `limit`: Number of characters to return
- **Success Response**:
  - 200 OK with full file content (when no offset/limit)
  - 206 Partial Content with partial content (when offset/limit provided)
- **Headers**:
  - `Content-Type`: The document's MIME type
  - `Content-Disposition`: Includes the original filename
  - `X-Total-Chars`: Total characters in document (partial content only)
  - `X-Char-Range`: Character range returned, e.g., "2000-3000" (partial content only)

**Examples**:
```bash
# Download full document
curl http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2 -o downloaded_file.md

# View content directly
curl http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2

# Get partial content (first 500 characters)
curl "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2?offset=0&limit=500"

# Get a specific section (characters 2000-3000)
curl "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2?offset=2000&limit=1000"
```

**Success Response**: The actual file content is returned (e.g., markdown text, binary data, etc.)

**Partial Content Response** (206):
```
HTTP/1.1 206 Partial Content
X-Total-Chars: 5000
X-Char-Range: 2000-3000
Content-Type: text/markdown

[partial document content here]
```

**Error Response** (404 if not found):
```json
{
  "detail": "Document not found"
}
```

**Error Response** (400 if partial read on binary content):
```json
{
  "detail": "Partial content retrieval is only supported for text content types"
}
```

### DELETE /documents/{document_id}

Delete a document by ID. Removes the file, database metadata, and semantic search index (if enabled).

**Cascade Delete Behavior**: If the document has **parent-child relations**, all child documents are **recursively deleted** first. Related documents (non-hierarchical) are NOT deleted, only their relations are removed.

- **Path parameter**: `document_id` - The document's unique identifier
- **Response**: 200 OK with `DeleteResponseWithCascade`

**Example**:
```bash
curl -X DELETE http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2
```

**Success Response** (single document):
```json
{
  "success": true,
  "message": "Deleted 1 document(s)",
  "deleted_document_ids": ["doc_a1b2c3d4e5f6a7b8c9d0e1f2"]
}
```

**Success Response** (with cascade - parent with 2 children):
```json
{
  "success": true,
  "message": "Deleted 3 document(s)",
  "deleted_document_ids": [
    "doc_child1",
    "doc_child2",
    "doc_parent"
  ]
}
```

**Error Response** (404 if not found):
```json
{
  "detail": "Document not found"
}
```

Tags and relations associated with the document are automatically removed (CASCADE deletion).

## Document Relations

The context store supports **bidirectional relations** between documents. Relations allow you to model hierarchies (parent-child) and peer connections (related) between documents.

### Terminology

- **Relation Definition**: A named relation type (e.g., `parent-child`, `related`) that describes how two documents are connected
- **Relation Type**: The database value stored for each side of a relation (e.g., `parent`, `child`, `related`)
- **Bidirectional**: Each relation creates two database entries, one from each document's perspective

### Available Definitions

| Definition | From Type | To Type | Cascade Delete |
|------------|-----------|---------|----------------|
| `parent-child` | `parent` | `child` | Yes (children deleted with parent) |
| `related` | `related` | `related` | No (only relation removed) |
| `predecessor-successor` | `predecessor` | `successor` | No (only relation removed) |

**Note**: Relation IDs are **strings** in the API (e.g., `"1"`, `"42"`), allowing for future flexibility.

### GET /relations/definitions

List all available relation definitions.

- **Response**: 200 OK with array of `RelationDefinitionResponse`

**Example**:
```bash
curl http://localhost:8766/relations/definitions
```

**Response**:
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
    "description": "Peer relation between related documents.",
    "from_document_is": "related",
    "to_document_is": "related"
  },
  {
    "name": "predecessor-successor",
    "description": "Sequential ordering relation.",
    "from_document_is": "predecessor",
    "to_document_is": "successor"
  }
]
```

### POST /relations

Create a bidirectional relation between two documents.

- **Request body**: `RelationCreateRequest` (JSON)
  - `definition` (required): Relation definition name (`parent-child`, `related`, or `predecessor-successor`)
  - `from_document_id` (required): First document ID
  - `to_document_id` (required): Second document ID
  - `from_to_note` (optional): Note on edge from source to target (from_doc's note about to_doc)
  - `to_from_note` (optional): Note on edge from target to source (to_doc's note about from_doc)
- **Response**: 201 Created with `RelationCreateResponse`

**Example** (creating parent-child relation):
```bash
curl -X POST http://localhost:8766/relations \
  -H "Content-Type: application/json" \
  -d '{
    "definition": "parent-child",
    "from_document_id": "doc_architecture",
    "to_document_id": "doc_database_design",
    "from_to_note": "Database layer documentation",
    "to_from_note": "Part of system architecture"
  }'
```

**Success Response**:
```json
{
  "success": true,
  "message": "Relation created",
  "from_relation": {
    "id": "1",
    "document_id": "doc_architecture",
    "related_document_id": "doc_database_design",
    "relation_type": "parent",
    "note": "Database layer documentation",
    "created_at": "2025-12-03T10:00:00",
    "updated_at": "2025-12-03T10:00:00"
  },
  "to_relation": {
    "id": "2",
    "document_id": "doc_database_design",
    "related_document_id": "doc_architecture",
    "relation_type": "child",
    "note": "Part of system architecture",
    "created_at": "2025-12-03T10:00:00",
    "updated_at": "2025-12-03T10:00:00"
  }
}
```

**Error Responses**:
- `400`: Invalid relation definition
- `404`: Document not found
- `409`: Relation already exists

### GET /documents/{document_id}/relations

Get all relations for a document, grouped by relation type.

- **Path parameter**: `document_id` - The document's unique identifier
- **Response**: 200 OK with `DocumentRelationsResponse`

**Example**:
```bash
curl http://localhost:8766/documents/doc_architecture/relations
```

**Response**:
```json
{
  "document_id": "doc_architecture",
  "relations": {
    "parent": [
      {
        "id": "1",
        "document_id": "doc_architecture",
        "related_document_id": "doc_database_design",
        "relation_type": "parent",
        "note": "Database layer documentation",
        "created_at": "2025-12-03T10:00:00",
        "updated_at": "2025-12-03T10:00:00"
      },
      {
        "id": "3",
        "document_id": "doc_architecture",
        "related_document_id": "doc_api_design",
        "relation_type": "parent",
        "note": "API layer documentation",
        "created_at": "2025-12-03T10:00:00",
        "updated_at": "2025-12-03T10:00:00"
      }
    ]
  }
}
```

**Error Response** (404 if document not found):
```json
{
  "detail": "Document not found"
}
```

### PATCH /relations/{relation_id}

Update the note for an existing relation. Only updates the specified side of the relation.

- **Path parameter**: `relation_id` - The relation's unique identifier
- **Request body**: `RelationUpdateRequest` (JSON)
  - `note` (optional): New note value (null to clear)
- **Response**: 200 OK with `RelationResponse`

**Example**:
```bash
curl -X PATCH http://localhost:8766/relations/1 \
  -H "Content-Type: application/json" \
  -d '{"note": "Updated context information"}'
```

**Success Response**:
```json
{
  "id": "1",
  "document_id": "doc_architecture",
  "related_document_id": "doc_database_design",
  "relation_type": "parent",
  "note": "Updated context information",
  "created_at": "2025-12-03T10:00:00",
  "updated_at": "2025-12-03T10:30:00"
}
```

**Error Response** (404 if relation not found):
```json
{
  "detail": "Relation not found"
}
```

### DELETE /relations/{relation_id}

Delete a relation and its bidirectional counterpart. This removes the relation only, NOT the documents.

- **Path parameter**: `relation_id` - The relation's unique identifier
- **Response**: 200 OK with `RelationDeleteResponse`

**Example**:
```bash
curl -X DELETE http://localhost:8766/relations/1
```

**Success Response**:
```json
{
  "success": true,
  "message": "Relation removed",
  "deleted_relation_ids": ["1", "2"]
}
```

The response includes both relation IDs that were deleted (the specified relation and its inverse counterpart).

**Error Response** (404 if relation not found):
```json
{
  "detail": "Relation not found"
}
```

### Relation Usage Examples

**Creating a Documentation Hierarchy**:
```bash
# Create architecture document
curl -X POST http://localhost:8766/documents -F "file=@architecture.md"
# Returns: doc_architecture

# Create child documents
curl -X POST http://localhost:8766/documents -F "file=@database-design.md"
# Returns: doc_database_design

curl -X POST http://localhost:8766/documents -F "file=@api-design.md"
# Returns: doc_api_design

# Create parent-child relations
curl -X POST http://localhost:8766/relations \
  -H "Content-Type: application/json" \
  -d '{"definition":"parent-child","from_document_id":"doc_architecture","to_document_id":"doc_database_design"}'

curl -X POST http://localhost:8766/relations \
  -H "Content-Type: application/json" \
  -d '{"definition":"parent-child","from_document_id":"doc_architecture","to_document_id":"doc_api_design"}'
```

Result:
```
doc_architecture (parent)
├── doc_database_design (child)
└── doc_api_design (child)
```

**Deleting the Parent (Cascade)**:
```bash
curl -X DELETE http://localhost:8766/documents/doc_architecture
```

This will delete `doc_architecture` and both children (`doc_database_design`, `doc_api_design`).

## Document URL Behavior

All document metadata responses include a `url` field that provides a direct link to retrieve the document content. This URL points to the `GET /documents/{document_id}` endpoint.

### Using URLs in a Browser

When you open a document URL in a web browser (e.g., `http://localhost:8766/documents/doc_123`), the behavior depends on the document's MIME type:

| Content Type | Browser Behavior | Example |
|-------------|------------------|---------|
| `text/plain`, `text/markdown` | **Displays inline** as plain text | README files, logs |
| `text/html` | **Renders** the HTML page | Web pages |
| `image/png`, `image/jpeg`, `image/gif` | **Displays** the image | Photos, diagrams |
| `application/pdf` | **Opens** in built-in PDF viewer | PDF documents |
| `application/json` | **Displays** formatted JSON | API responses, configs |
| `video/mp4`, `audio/mp3` | **Plays** in media player | Videos, audio files |
| `application/octet-stream` | **Downloads** the file | Binary files, executables |
| Other binary types | **Downloads** with suggested filename | Archives, Office docs |

The server sets appropriate headers:
- `Content-Type`: The document's detected MIME type
- `Content-Disposition`: Includes the original filename for downloads

### Programmatic Access

For programmatic access (API clients, scripts), use the URL to download the document:

```bash
# Download using curl
curl http://localhost:8766/documents/doc_123 -o downloaded_file.md

# Download using wget
wget http://localhost:8766/documents/doc_123 -O downloaded_file.md

# In Python
import requests
response = requests.get("http://localhost:8766/documents/doc_123")
with open("downloaded_file.md", "wb") as f:
    f.write(response.content)
```

## Environment Variables

Configure the server using environment variables:

### DOCUMENT_SERVER_HOST

- **Description**: Server bind address
- **Default**: `0.0.0.0` (listens on all interfaces)
- **Example**:
  ```bash
  DOCUMENT_SERVER_HOST=127.0.0.1 uv run python -m src.main
  ```

### DOCUMENT_SERVER_PORT

- **Description**: Server port number
- **Default**: `8766`
- **Example**:
  ```bash
  DOCUMENT_SERVER_PORT=9000 uv run python -m src.main
  ```

### DOCUMENT_SERVER_PUBLIC_URL

- **Description**: Public-facing base URL for generating document retrieval links. This is **critical for Docker deployments** where the internal port may differ from the external port, or when the server is behind a reverse proxy.
- **Default**: `http://localhost:{DOCUMENT_SERVER_PORT}`
- **Format**: `{protocol}://{host}[:{port}]` (no trailing slash)
- **Use Cases**:
  - **Docker with port mapping**: If container uses internal port 8766 but is exposed as 9000: `http://localhost:9000`
  - **Remote access**: If server runs on a remote host: `http://192.168.1.100:8766`
  - **Reverse proxy/HTTPS**: If behind nginx with SSL: `https://api.example.com`
  - **Custom domain**: If using a domain name: `https://docs.mycompany.com`
- **Examples**:
  ```bash
  # Docker with different external port
  DOCUMENT_SERVER_PUBLIC_URL=http://localhost:9000 uv run python -m src.main

  # Remote server
  DOCUMENT_SERVER_PUBLIC_URL=http://192.168.1.100:8766 uv run python -m src.main

  # Production with HTTPS
  DOCUMENT_SERVER_PUBLIC_URL=https://api.example.com uv run python -m src.main
  ```
- **Note**: The `url` field in all document metadata responses will use this base URL. For example, with `DOCUMENT_SERVER_PUBLIC_URL=https://api.example.com`, a document's URL will be `https://api.example.com/documents/{document_id}`

### DOCUMENT_SERVER_STORAGE

- **Description**: Storage directory path for document files
- **Default**: `./document-data/files`
- **Example**:
  ```bash
  DOCUMENT_SERVER_STORAGE=/var/documents uv run python -m src.main
  ```

### DOCUMENT_SERVER_DB

- **Description**: SQLite database file path
- **Default**: `./document-data/documents.db`
- **Example**:
  ```bash
  DOCUMENT_SERVER_DB=/var/db/documents.db uv run python -m src.main
  ```

## Semantic Search (Optional)

The context store supports semantic search using vector embeddings. This feature allows you to search documents by meaning rather than exact keyword matches.

### Requirements

1. **Ollama** - Local LLM server for generating embeddings
2. **Elasticsearch** - Vector database for storing and searching embeddings

### Setting Up Ollama

Ollama must be installed and running on your machine with the embedding model pulled.

1. **Install Ollama** (if not already installed):
   ```bash
   # macOS
   brew install ollama

   # Linux
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Start Ollama**:
   ```bash
   ollama serve
   ```

3. **Pull the embedding model**:
   ```bash
   ollama pull nomic-embed-text
   ```

4. **Verify it's working**:
   ```bash
   curl http://localhost:11434/api/tags
   ```
   You should see `nomic-embed-text` in the list of models.

### Elasticsearch Setup

Elasticsearch is handled automatically via Docker Compose. When you start the full stack with `docker-compose up`, Elasticsearch will be started as a service.

For local development without the full stack, you can start only Elasticsearch:
```bash
cd servers/context-store
docker compose up -d
```

### Enabling Semantic Search

Set the environment variable to enable semantic search:

```bash
# Local development
SEMANTIC_SEARCH_ENABLED=true uv run python -m src.main

# Docker (set in .env file or pass to docker-compose)
SEMANTIC_SEARCH_ENABLED=true docker-compose up -d
```

### Semantic Search Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SEMANTIC_SEARCH_ENABLED` | Enable/disable semantic search | `false` |
| `OLLAMA_BASE_URL` | Ollama API base URL | `http://localhost:11434` (local) or `http://host.docker.internal:11434` (Docker) |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model name | `nomic-embed-text` |
| `ELASTICSEARCH_URL` | Elasticsearch URL | `http://localhost:9200` (local) or `http://elasticsearch:9200` (Docker) |
| `ELASTICSEARCH_INDEX` | Index name for vectors | `context-store-vectors` |
| `CHUNK_SIZE` | Characters per chunk | `1000` |
| `CHUNK_OVERLAP` | Overlap between chunks | `200` |

### How It Works

1. **Document Upload**: When a text document is uploaded and semantic search is enabled, it is:
   - Split into overlapping chunks (default: 1000 chars with 200 char overlap)
   - Each chunk is embedded using Ollama's embedding model
   - Embeddings are stored in Elasticsearch with character offsets

2. **Search**: When you search:
   - Your query is embedded using the same model
   - Elasticsearch finds the most similar chunks
   - Results are aggregated by document and include section offsets

3. **Retrieval**: Use the `offset` and `limit` from search results to fetch only the relevant section of a document.

### Docker Network Considerations

When running in Docker:
- **Ollama**: Runs on your host machine (not in Docker). The context-store container accesses it via `host.docker.internal:11434`
- **Elasticsearch**: Runs as a Docker service. The context-store container accesses it via `elasticsearch:9200` (Docker DNS)

If you're running Ollama on a different host or port, set `OLLAMA_BASE_URL` accordingly:
```bash
OLLAMA_BASE_URL=http://192.168.1.100:11434 docker-compose up -d
```

## Docker Operations

### Docker Commands

```bash
# Build and start
docker-compose build
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs document-server

# Restart
docker-compose restart document-server

# Monitor resources
docker stats context-store-server

# Check health
docker inspect --format='{{json .State.Health}}' context-store-server

# Stop
docker-compose down        # Keep data
docker-compose down -v     # Remove data
```

## Development

### Interactive API Documentation

FastAPI provides auto-generated interactive documentation:

- **Swagger UI**: http://localhost:8766/docs
- **ReDoc**: http://localhost:8766/redoc

Use Swagger UI to test endpoints interactively with a web interface.

### Troubleshooting

#### Port Already in Use

If you see "Address already in use" error:

1. Check if another process is using port 8766:
   ```bash
   lsof -i :8766
   ```

2. Either stop the other process or use a different port:
   ```bash
   DOCUMENT_SERVER_PORT=9000 uv run python -m src.main
   ```

#### Import Errors

If you see "ModuleNotFoundError" or import errors:

1. Ensure you've installed dependencies:
   ```bash
   uv sync
   ```

2. Make sure you're running from the `servers/context-store/` directory

3. Run as a module (not as a script):
   ```bash
   # Correct
   uv run python -m src.main

   # Incorrect (will fail with import errors)
   uv run src/main.py
   ```

#### Module Not Found

If you see "No module named 'src'":

- Verify you're in the `servers/context-store/` directory when running the server
- The `src/` directory should be a Python package with `__init__.py`

## Project Structure

```
servers/context-store/
├── pyproject.toml
├── uv.lock
├── README.md
├── docker-compose.yml     # Local Elasticsearch for development
├── .venv/
├── document-data/         # Created at runtime (gitignored)
│   ├── files/
│   └── documents.db
├── src/
│   ├── main.py
│   ├── models.py
│   ├── storage.py
│   ├── database.py
│   └── semantic/          # Semantic search module (optional)
│       ├── __init__.py
│       ├── config.py      # Configuration settings
│       ├── indexer.py     # Chunking and embedding
│       └── search.py      # Query and retrieval
└── tests/
```

## Testing

Comprehensive integration test suite covering all API endpoints, edge cases, and error scenarios.

For test documentation and how to run tests, see [tests/README.md](tests/README.md).
