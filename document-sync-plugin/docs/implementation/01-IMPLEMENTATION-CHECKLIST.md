# Implementation Checklist: Server Foundation (Block 01)

## Project Structure Reference

```
document-sync-plugin/
├── skills/document-sync/           # Skill for Claude Code (Blocks 03, 05)
│   ├── skill.json
│   ├── SKILL.md
│   └── commands/
│       ├── doc-push, doc-pull, doc-query, doc-delete
│       └── lib/                    # Shared client library
└── document-server/                # THIS BLOCK - Server implementation
    ├── pyproject.toml
    ├── uv.lock
    ├── Dockerfile
    ├── README.md
    └── src/
        ├── main.py                 # FastAPI application
        ├── models.py               # Pydantic models
        ├── storage.py              # File storage (Block 02)
        └── database.py             # SQLite database (Block 02)
```

**This block focuses on: `document-server/` directory**

## Overall Goal

Build a FastAPI server skeleton that listens on port 8766 with HTTP endpoints for document management operations. This foundation includes Pydantic models for request/response validation, basic routing structure, and stub implementations for core endpoints. The server will use environment-based configuration and handle multipart form data for document uploads.

## Checkpoint Instructions

Mark each task as complete by checking the box: `- [x]` when done. Work through the phases sequentially to ensure proper setup and validation at each step.

---

## Phase 1: Project Setup

- [ ] Create `document-server/` directory at project root
- [ ] Navigate to `document-server/` and run `uv init` to initialize UV project
- [ ] Configure `document-server/pyproject.toml` with:
  - [ ] Project name: "document-server"
  - [ ] Python version requirement: ">=3.11"
  - [ ] Dependencies: fastapi, uvicorn[standard], python-multipart
  - [ ] Script entry point (optional): "start = document_server.main:main"
- [ ] Run `uv sync` to create lockfile and install dependencies
- [ ] Create `document-server/src/` directory
- [ ] Create `document-server/src/__init__.py` (empty file to mark as package)
- [ ] Verify directory structure:
  ```
  document-server/
  ├── pyproject.toml
  ├── uv.lock
  └── src/
      └── __init__.py
  ```

---

## Phase 2: Pydantic Models (models.py)

- [ ] Create `document-server/src/models.py`
- [ ] Import required types: `from pydantic import BaseModel, Field`
- [ ] Import `from datetime import datetime`
- [ ] Implement `DocumentMetadata` model with fields:
  - [ ] `id: str` - Document unique identifier
  - [ ] `filename: str` - Original filename
  - [ ] `content_type: str` - MIME type (e.g., "text/markdown")
  - [ ] `size_bytes: int` - File size
  - [ ] `storage_path: str` - Internal filesystem path
  - [ ] `created_at: datetime` - Creation timestamp with default_factory
  - [ ] `updated_at: datetime` - Last update timestamp with default_factory
  - [ ] `tags: list[str]` - Optional tags with default empty list
  - [ ] `metadata: dict[str, str]` - Additional key-value metadata with default empty dict
- [ ] Implement `DocumentUploadRequest` model:
  - [ ] `filename: str` - Required filename
  - [ ] `content_type: str` - Required MIME type with default "text/markdown"
  - [ ] `tags: list[str]` - Optional tags with default empty list
  - [ ] `metadata: dict[str, str]` - Optional metadata with default empty dict
- [ ] Implement `DocumentQueryParams` model:
  - [ ] `tags: list[str] | None` - Optional tag filter with default None
  - [ ] `content_type: str | None` - Optional content type filter with default None
  - [ ] `limit: int` - Result limit with default 100
  - [ ] `offset: int` - Pagination offset with default 0
- [ ] Implement `DocumentResponse` model (public-facing, excludes storage_path):
  - [ ] `id: str`
  - [ ] `filename: str`
  - [ ] `content_type: str`
  - [ ] `size_bytes: int`
  - [ ] `created_at: datetime`
  - [ ] `updated_at: datetime`
  - [ ] `tags: list[str]`
  - [ ] `metadata: dict[str, str]`
- [ ] Implement `DeleteResponse` model:
  - [ ] `success: bool`
  - [ ] `message: str`
  - [ ] `document_id: str`
- [ ] Test imports: Run `python -c "from src.models import DocumentMetadata, DocumentResponse"`

---

## Phase 3: FastAPI Application (main.py)

### 3.1 Initial Setup

- [ ] Create `document-server/src/main.py`
- [ ] Import required modules:
  - [ ] `from fastapi import FastAPI, File, UploadFile, HTTPException, Query`
  - [ ] `from fastapi.responses import JSONResponse`
  - [ ] `from typing import Optional`
  - [ ] `import uvicorn, os`
- [ ] Import models: `from .models import DocumentMetadata, DocumentResponse, DocumentQueryParams, DeleteResponse`
- [ ] Create FastAPI app instance:
  - [ ] Set title: "Document Sync Server"
  - [ ] Set version: "0.1.0"
  - [ ] Set description: "FastAPI server for document management and synchronization"

### 3.2 Configuration

- [ ] Add centralized configuration constants:
  - [ ] `DEFAULT_HOST = "0.0.0.0"`
  - [ ] `DEFAULT_PORT = 8766`
  - [ ] `DEFAULT_STORAGE_DIR = "./storage"`
- [ ] Add environment variable reading:
  - [ ] `DOCUMENT_SERVER_HOST = os.getenv("DOCUMENT_SERVER_HOST", DEFAULT_HOST)`
  - [ ] `DOCUMENT_SERVER_PORT = int(os.getenv("DOCUMENT_SERVER_PORT", DEFAULT_PORT))`
  - [ ] `DOCUMENT_SERVER_STORAGE = os.getenv("DOCUMENT_SERVER_STORAGE", DEFAULT_STORAGE_DIR)`

### 3.3 POST /documents Endpoint

- [ ] Create `POST /documents` endpoint with:
  - [ ] Path: `/documents`
  - [ ] Response model: `DocumentResponse`
  - [ ] Status code: 201
- [ ] Add parameters:
  - [ ] `file: UploadFile = File(...)` - Required file upload
  - [ ] `tags: Optional[str] = Query(None)` - Comma-separated tags
  - [ ] `metadata: Optional[str] = Query(None)` - JSON string of metadata
- [ ] Implement stub logic:
  - [ ] Parse tags from comma-separated string to list
  - [ ] Parse metadata from JSON string to dict (handle parse errors)
  - [ ] Create dummy DocumentResponse with:
    - [ ] `id: "doc_stub_123"`
    - [ ] `filename: file.filename`
    - [ ] `content_type: file.content_type or "application/octet-stream"`
    - [ ] `size_bytes: 0`
    - [ ] `created_at: datetime.now()`
    - [ ] `updated_at: datetime.now()`
    - [ ] `tags: parsed_tags or []`
    - [ ] `metadata: parsed_metadata or {}`
  - [ ] Return JSONResponse with status_code=201

### 3.4 GET /documents/{id} Endpoint

- [ ] Create `GET /documents/{id}` endpoint with:
  - [ ] Path: `/documents/{document_id}`
  - [ ] Response model: `DocumentResponse`
  - [ ] Path parameter: `document_id: str`
- [ ] Implement stub logic:
  - [ ] Raise `HTTPException(status_code=501, detail="Document retrieval not yet implemented")`

### 3.5 GET /documents Endpoint

- [ ] Create `GET /documents` endpoint with:
  - [ ] Path: `/documents`
  - [ ] Response model: `list[DocumentResponse]`
- [ ] Add query parameters:
  - [ ] `tags: Optional[str] = Query(None)` - Comma-separated tag filter
  - [ ] `content_type: Optional[str] = Query(None)` - Content type filter
  - [ ] `limit: int = Query(100)` - Result limit
  - [ ] `offset: int = Query(0)` - Pagination offset
- [ ] Implement stub logic:
  - [ ] Parse tags if provided
  - [ ] Return empty list: `[]`
  - [ ] Add comment: "# Stub: Will query database in Block 02"

### 3.6 DELETE /documents/{id} Endpoint

- [ ] Create `DELETE /documents/{id}` endpoint with:
  - [ ] Path: `/documents/{document_id}`
  - [ ] Response model: `DeleteResponse`
  - [ ] Path parameter: `document_id: str`
- [ ] Implement stub logic:
  - [ ] Return DeleteResponse with:
    - [ ] `success: True`
    - [ ] `message: "Document deletion stub (not yet implemented)"`
    - [ ] `document_id: document_id`

### 3.7 Error Handling & Server Entry Point

- [ ] Add global exception handler for validation errors (optional but recommended)
- [ ] Add `if __name__ == "__main__":` block:
  - [ ] Call `uvicorn.run()`
  - [ ] Parameters: `app`, `host=DOCUMENT_SERVER_HOST`, `port=DOCUMENT_SERVER_PORT`
  - [ ] Add `reload=True` for development

---

## Phase 4: Stub Files

- [ ] Create `document-server/src/storage.py`:
  - [ ] Add docstring: "Storage layer for filesystem operations (Block 02 implementation)"
  - [ ] Create `DocumentStorage` class stub:
    - [ ] `def __init__(self, storage_dir: str): pass`
    - [ ] `async def save_document(self, doc_id: str, file_content: bytes) -> str: raise NotImplementedError()`
    - [ ] `async def get_document(self, doc_id: str) -> bytes: raise NotImplementedError()`
    - [ ] `async def delete_document(self, doc_id: str) -> bool: raise NotImplementedError()`
- [ ] Create `document-server/src/database.py`:
  - [ ] Add docstring: "Database layer for metadata persistence (Block 02 implementation)"
  - [ ] Create `DocumentDatabase` class stub:
    - [ ] `def __init__(self, db_path: str): pass`
    - [ ] `async def insert_metadata(self, metadata: DocumentMetadata) -> None: raise NotImplementedError()`
    - [ ] `async def get_metadata(self, doc_id: str) -> DocumentMetadata | None: raise NotImplementedError()`
    - [ ] `async def query_metadata(self, params: DocumentQueryParams) -> list[DocumentMetadata]: raise NotImplementedError()`
    - [ ] `async def delete_metadata(self, doc_id: str) -> bool: raise NotImplementedError()`

---

## Phase 5: Testing

### 5.1 Server Startup

- [ ] Navigate to `document-server/` directory
- [ ] Start server: `uv run src/main.py`
- [ ] Verify console output shows: "Uvicorn running on http://0.0.0.0:8766"
- [ ] Verify no startup errors or import failures
- [ ] Check server responds: `curl http://localhost:8766/docs` (should return HTML)

### 5.2 Endpoint Testing

- [ ] Test POST /documents with multipart form data:
  ```bash
  curl -X POST http://localhost:8766/documents \
    -F "file=@test.md" \
    -F "tags=test,demo" \
    -F "metadata={\"author\":\"test\"}"
  ```
  - [ ] Verify returns 201 status
  - [ ] Verify response contains `id: "doc_stub_123"`
  - [ ] Verify filename, tags, and metadata are parsed correctly

- [ ] Test GET /documents (list all):
  ```bash
  curl http://localhost:8766/documents
  ```
  - [ ] Verify returns 200 status
  - [ ] Verify returns empty array: `[]`

- [ ] Test GET /documents with query parameters:
  ```bash
  curl "http://localhost:8766/documents?tags=test&limit=10"
  ```
  - [ ] Verify returns 200 status
  - [ ] Verify returns empty array: `[]`

- [ ] Test GET /documents/{id} (single document):
  ```bash
  curl http://localhost:8766/documents/doc_123
  ```
  - [ ] Verify returns 501 status
  - [ ] Verify error detail: "Document retrieval not yet implemented"

- [ ] Test DELETE /documents/{id}:
  ```bash
  curl -X DELETE http://localhost:8766/documents/doc_123
  ```
  - [ ] Verify returns 200 status
  - [ ] Verify response: `{"success": true, "message": "...", "document_id": "doc_123"}`

### 5.3 FastAPI Interactive Docs

- [ ] Open browser to http://localhost:8766/docs
- [ ] Verify all 4 endpoints are listed:
  - [ ] POST /documents
  - [ ] GET /documents/{document_id}
  - [ ] GET /documents
  - [ ] DELETE /documents/{document_id}
- [ ] Test POST /documents through Swagger UI:
  - [ ] Upload a test file
  - [ ] Add tags and metadata
  - [ ] Verify 201 response with correct data
- [ ] Verify schema definitions show all models correctly

### 5.4 Validation Testing

- [ ] Test invalid POST request (missing file):
  ```bash
  curl -X POST http://localhost:8766/documents
  ```
  - [ ] Verify returns 422 Unprocessable Entity
  - [ ] Verify error mentions "field required"

- [ ] Test invalid query parameters (negative limit):
  ```bash
  curl "http://localhost:8766/documents?limit=-1"
  ```
  - [ ] Verify Pydantic validation (may return 422 if validation added)

- [ ] Test invalid JSON metadata:
  ```bash
  curl -X POST http://localhost:8766/documents \
    -F "file=@test.md" \
    -F "metadata=invalid-json"
  ```
  - [ ] Verify handles gracefully (check server logs)

### 5.5 Configuration Testing

- [ ] Stop the server (Ctrl+C)
- [ ] Test environment variable override:
  ```bash
  DOCUMENT_SERVER_PORT=9999 uv run src/main.py
  ```
  - [ ] Verify server starts on port 9999
  - [ ] Test endpoint: `curl http://localhost:9999/documents`
  - [ ] Stop server

- [ ] Restart server on default port 8766:
  ```bash
  uv run src/main.py
  ```
  - [ ] Verify clean startup
  - [ ] Verify port 8766 is used

### 5.6 Cleanup

- [ ] Stop server cleanly (Ctrl+C)
- [ ] Verify no zombie processes: `lsof -i :8766` (should be empty)

---

## Phase 6: Documentation

- [ ] Create `document-server/README.md` with sections:

### 6.1 Setup Instructions

- [ ] Add project overview and purpose
- [ ] Document prerequisites:
  - [ ] Python 3.11+
  - [ ] UV package manager
- [ ] Add installation steps:
  ```bash
  cd document-server
  uv sync
  ```
- [ ] Add startup instructions:
  ```bash
  uv run src/main.py
  ```

### 6.2 Available Endpoints

- [ ] Document POST /documents:
  - [ ] Description: Upload a new document
  - [ ] Request format: multipart/form-data
  - [ ] Parameters: file (required), tags (optional), metadata (optional)
  - [ ] Response: 201 Created with DocumentResponse
  - [ ] Current status: Stub implementation

- [ ] Document GET /documents:
  - [ ] Description: List all documents with optional filters
  - [ ] Query parameters: tags, content_type, limit, offset
  - [ ] Response: 200 OK with list of DocumentResponse
  - [ ] Current status: Returns empty list

- [ ] Document GET /documents/{id}:
  - [ ] Description: Retrieve a specific document by ID
  - [ ] Path parameter: document_id
  - [ ] Response: 200 OK with DocumentResponse
  - [ ] Current status: Returns 501 Not Implemented

- [ ] Document DELETE /documents/{id}:
  - [ ] Description: Delete a document by ID
  - [ ] Path parameter: document_id
  - [ ] Response: 200 OK with DeleteResponse
  - [ ] Current status: Stub implementation

### 6.3 Example curl Commands

- [ ] Add upload example:
  ```bash
  curl -X POST http://localhost:8766/documents \
    -F "file=@example.md" \
    -F "tags=documentation,example" \
    -F "metadata={\"author\":\"John Doe\",\"version\":\"1.0\"}"
  ```

- [ ] Add list example:
  ```bash
  curl http://localhost:8766/documents
  ```

- [ ] Add filtered list example:
  ```bash
  curl "http://localhost:8766/documents?tags=documentation&limit=10"
  ```

- [ ] Add retrieve example:
  ```bash
  curl http://localhost:8766/documents/doc_123
  ```

- [ ] Add delete example:
  ```bash
  curl -X DELETE http://localhost:8766/documents/doc_123
  ```

### 6.4 Environment Variables

- [ ] Document `DOCUMENT_SERVER_HOST`:
  - [ ] Description: Server bind address
  - [ ] Default: "0.0.0.0"
  - [ ] Example: `DOCUMENT_SERVER_HOST=127.0.0.1 uv run src/main.py`

- [ ] Document `DOCUMENT_SERVER_PORT`:
  - [ ] Description: Server port number
  - [ ] Default: 8766
  - [ ] Example: `DOCUMENT_SERVER_PORT=9000 uv run src/main.py`

- [ ] Document `DOCUMENT_SERVER_STORAGE`:
  - [ ] Description: Storage directory path
  - [ ] Default: "./storage"
  - [ ] Example: `DOCUMENT_SERVER_STORAGE=/var/documents uv run src/main.py`

### 6.5 Development Notes

- [ ] Add note about FastAPI interactive docs: http://localhost:8766/docs
- [ ] Add note about stub implementations and future work (Blocks 02-05)
- [ ] Add troubleshooting section:
  - [ ] Port already in use: Change port with environment variable
  - [ ] Import errors: Run `uv sync` to install dependencies
  - [ ] Module not found: Ensure running from document-server/ directory

---

## Success Criteria

Upon completion of this checklist, verify all criteria are met:

- [ ] FastAPI server starts successfully on port 8766
- [ ] All 4 HTTP endpoints (POST, GET list, GET single, DELETE) respond correctly
- [ ] POST /documents accepts multipart form data and returns 201 with stub response
- [ ] GET /documents returns empty list with 200 status
- [ ] GET /documents/{id} returns 501 Not Implemented
- [ ] DELETE /documents/{id} returns stub success response
- [ ] Pydantic models validate request/response data correctly
- [ ] Invalid requests return 422 validation errors
- [ ] Environment variables (PORT, HOST, STORAGE) override defaults correctly
- [ ] FastAPI interactive docs accessible at /docs
- [ ] Server can be stopped and restarted cleanly
- [ ] README.md documents setup, endpoints, and usage examples
- [ ] Project structure follows conventions:
  ```
  document-server/
  ├── pyproject.toml
  ├── uv.lock
  ├── README.md
  └── src/
      ├── __init__.py
      ├── main.py
      ├── models.py
      ├── storage.py
      └── database.py
  ```

---

## Implementation Notes

### Configuration Pattern

- Use environment variables for all runtime configuration
- Provide sensible defaults for development
- Read environment variables once at module level, not in request handlers
- Example: `PORT = int(os.getenv("DOCUMENT_SERVER_PORT", 8766))`

### Multipart Form Data Handling

- Use `UploadFile = File(...)` for file uploads
- Use `Query()` parameters for tags and metadata strings
- Parse comma-separated tags: `tags.split(",")` if tags else []
- Parse JSON metadata: `json.loads(metadata)` with try/except
- Content type auto-detected by FastAPI from file upload

### Stub Response Examples

- POST /documents returns static document ID: "doc_stub_123"
- All responses use proper Pydantic models (DocumentResponse, DeleteResponse)
- GET endpoints return empty collections or 501 status
- DELETE returns success=True with descriptive message

### Error Handling with HTTPException

- Use `HTTPException(status_code=501, detail="...")` for unimplemented endpoints
- Pydantic automatically returns 422 for validation errors
- Add try/except for JSON parsing in POST handler
- Return appropriate status codes: 201 for creation, 200 for success, 501 for not implemented

### Testing Multipart Uploads with curl

- Use `-F` flag for form data: `curl -F "file=@path/to/file"`
- Multiple form fields: `curl -F "file=@test.md" -F "tags=foo,bar"`
- JSON metadata as string: `curl -F "metadata={\"key\":\"value\"}"`
- Test file can be any text file (create test.md if needed)
- Use `-v` flag for verbose output to debug issues

---

**Next Steps**: After completing this checklist, proceed to Block 02 (Storage & Database) to implement actual storage and SQLite persistence.
