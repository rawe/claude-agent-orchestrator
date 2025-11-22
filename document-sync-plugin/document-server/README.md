# Document Sync Server

FastAPI server for document management and synchronization. This server provides RESTful API endpoints for uploading, retrieving, querying, and deleting documents with metadata and tag support.

## Prerequisites

- **Python 3.11+** - Required for modern type hints and async support
- **UV package manager** - Fast Python package installer and resolver

## Installation

1. Navigate to the document-server directory:
   ```bash
   cd document-server
   ```

2. Install dependencies using UV:
   ```bash
   uv sync
   ```

   This will create a virtual environment and install all required packages (FastAPI, Uvicorn, python-multipart).

## Starting the Server

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

### POST /documents

Upload a new document with optional tags and metadata.

- **Request format**: `multipart/form-data`
- **Parameters**:
  - `file` (required): File to upload
  - `tags` (optional): Comma-separated list of tags (e.g., "documentation,example")
  - `metadata` (optional): JSON string with key-value pairs (e.g., `{"author":"John Doe"}`)
- **Response**: 201 Created with `DocumentResponse`

**Example**:
```bash
curl -X POST http://localhost:8766/documents \
  -F "file=@example.md" \
  -F "tags=documentation,example" \
  -F "metadata={\"author\":\"John Doe\",\"version\":\"1.0\"}"
```

**Response**:
```json
{
  "id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2",
  "filename": "example.md",
  "content_type": "text/markdown",
  "size_bytes": 1234,
  "created_at": "2025-11-22T12:34:56.789012",
  "updated_at": "2025-11-22T12:34:56.789012",
  "tags": ["documentation", "example"],
  "metadata": {"author": "John Doe", "version": "1.0"}
}
```

The server generates a unique document ID, calculates a SHA256 checksum for integrity verification, and detects the MIME type automatically.

### GET /documents

Query documents with optional filtering by filename and/or tags.

- **Query parameters**:
  - `filename` (optional): Partial filename match (e.g., "example" matches "example.md")
  - `tags` (optional): Comma-separated tags - uses AND logic (document must have ALL tags)
  - `limit` (default: 100): Maximum number of results
  - `offset` (default: 0): Pagination offset
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
```

**Tag AND Logic**: When querying with multiple tags (e.g., `tags=python,tutorial`), only documents that have BOTH tags will be returned.

### GET /documents/{document_id}

Download a document by ID. Returns the file content with appropriate headers.

- **Path parameter**: `document_id` - The document's unique identifier
- **Success Response**: 200 OK with file content (binary/text based on MIME type)
- **Headers**:
  - `Content-Type`: The document's MIME type
  - `Content-Disposition`: Includes the original filename

**Example**:
```bash
# Download and save to file
curl http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2 -o downloaded_file.md

# View content directly
curl http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2
```

**Success Response**: The actual file content is returned (e.g., markdown text, binary data, etc.)

**Error Response** (404 if not found):
```json
{
  "detail": "Document not found"
}
```

### DELETE /documents/{document_id}

Delete a document by ID. Removes both the file and database metadata.

- **Path parameter**: `document_id` - The document's unique identifier
- **Response**: 200 OK with `DeleteResponse`

**Example**:
```bash
curl -X DELETE http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2
```

**Success Response**:
```json
{
  "success": true,
  "message": "Document doc_a1b2c3d4e5f6a7b8c9d0e1f2 deleted successfully",
  "document_id": "doc_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

**Error Response** (404 if not found):
```json
{
  "detail": "Document not found"
}
```

Tags associated with the document are automatically removed (CASCADE deletion).

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

2. Make sure you're running from the `document-server/` directory

3. Run as a module (not as a script):
   ```bash
   # Correct
   uv run python -m src.main

   # Incorrect (will fail with import errors)
   uv run src/main.py
   ```

#### Module Not Found

If you see "No module named 'src'":

- Verify you're in the `document-server/` directory when running the server
- The `src/` directory should be a Python package with `__init__.py`

## Project Structure

```
document-server/
├── pyproject.toml
├── uv.lock
├── README.md
├── .venv/
├── document-data/         # Created at runtime
│   ├── files/
│   └── documents.db
├── src/
│   ├── main.py
│   ├── models.py
│   ├── storage.py
│   └── database.py
└── test_*.py
```

## Testing

End-to-end tests verify all API endpoints (upload, query, download, delete) including tag AND logic and path traversal protection.

**Quick start**: `./tests/e2e.sh` (requires running server)

For detailed instructions, see [tests/README.md](tests/README.md).
