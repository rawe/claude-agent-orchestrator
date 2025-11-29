# Context Store Server

FastAPI server for storing context documents. This server provides RESTful API endpoints for uploading, retrieving, querying, and deleting documents with metadata and tag support.

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
  "metadata": {"author": "John Doe", "version": "1.0"},
  "url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

The server generates a unique document ID, calculates a SHA256 checksum for integrity verification, detects the MIME type automatically, and provides a fully qualified URL for document retrieval.

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

Comprehensive integration test suite covering all API endpoints, edge cases, and error scenarios.

For test documentation and how to run tests, see [tests/README.md](tests/README.md).
