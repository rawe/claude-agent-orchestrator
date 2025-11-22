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

- [x] Create `document-server/` directory at project root
- [x] Navigate to `document-server/` and run `uv init` to initialize UV project
- [x] Configure `document-server/pyproject.toml` with:
  - [x] Project name: "document-server"
  - [x] Python version requirement: ">=3.11"
  - [x] Dependencies: fastapi, uvicorn[standard], python-multipart
  - [x] Script entry point (optional): "start = document_server.main:main"
- [x] Run `uv sync` to create lockfile and install dependencies
- [x] Create `document-server/src/` directory
- [x] Create `document-server/src/__init__.py` (empty file to mark as package)
- [x] Verify directory structure:
  ```
  document-server/
  ├── pyproject.toml
  ├── uv.lock
  └── src/
      └── __init__.py
  ```

---

## Phase 2: Pydantic Models (models.py)

- [x] Create `document-server/src/models.py`
- [x] Import required types: `from pydantic import BaseModel, Field`
- [x] Import `from datetime import datetime`
- [x] Implement `DocumentMetadata` model with fields:
  - [x] `id: str` - Document unique identifier
  - [x] `filename: str` - Original filename
  - [x] `content_type: str` - MIME type (e.g., "text/markdown")
  - [x] `size_bytes: int` - File size
  - [x] `storage_path: str` - Internal filesystem path
  - [x] `created_at: datetime` - Creation timestamp with default_factory
  - [x] `updated_at: datetime` - Last update timestamp with default_factory
  - [x] `tags: list[str]` - Optional tags with default empty list
  - [x] `metadata: dict[str, str]` - Additional key-value metadata with default empty dict
- [x] Implement `DocumentUploadRequest` model:
  - [x] `filename: str` - Required filename
  - [x] `content_type: str` - Required MIME type with default "text/markdown"
  - [x] `tags: list[str]` - Optional tags with default empty list
  - [x] `metadata: dict[str, str]` - Optional metadata with default empty dict
- [x] Implement `DocumentQueryParams` model:
  - [x] `tags: list[str] | None` - Optional tag filter with default None
  - [x] `content_type: str | None` - Optional content type filter with default None
  - [x] `limit: int` - Result limit with default 100
  - [x] `offset: int` - Pagination offset with default 0
- [x] Implement `DocumentResponse` model (public-facing, excludes storage_path):
  - [x] `id: str`
  - [x] `filename: str`
  - [x] `content_type: str`
  - [x] `size_bytes: int`
  - [x] `created_at: datetime`
  - [x] `updated_at: datetime`
  - [x] `tags: list[str]`
  - [x] `metadata: dict[str, str]`
- [x] Implement `DeleteResponse` model:
  - [x] `success: bool`
  - [x] `message: str`
  - [x] `document_id: str`
- [x] Test imports: Run `python -c "from src.models import DocumentMetadata, DocumentResponse"`

---

## Phase 3: FastAPI Application (main.py)

### 3.1 Initial Setup

- [x] Create `document-server/src/main.py`
- [x] Import required modules:
  - [x] `from fastapi import FastAPI, File, UploadFile, HTTPException, Query`
  - [x] `from fastapi.responses import JSONResponse`
  - [x] `from typing import Optional`
  - [x] `import uvicorn, os`
- [x] Import models: `from .models import DocumentMetadata, DocumentResponse, DocumentQueryParams, DeleteResponse`
- [x] Create FastAPI app instance:
  - [x] Set title: "Document Sync Server"
  - [x] Set version: "0.1.0"
  - [x] Set description: "FastAPI server for document management and synchronization"

### 3.2 Configuration

- [x] Add centralized configuration constants:
  - [x] `DEFAULT_HOST = "0.0.0.0"`
  - [x] `DEFAULT_PORT = 8766`
  - [x] `DEFAULT_STORAGE_DIR = "./storage"`
- [x] Add environment variable reading:
  - [x] `DOCUMENT_SERVER_HOST = os.getenv("DOCUMENT_SERVER_HOST", DEFAULT_HOST)`
  - [x] `DOCUMENT_SERVER_PORT = int(os.getenv("DOCUMENT_SERVER_PORT", DEFAULT_PORT))`
  - [x] `DOCUMENT_SERVER_STORAGE = os.getenv("DOCUMENT_SERVER_STORAGE", DEFAULT_STORAGE_DIR)`

### 3.3 POST /documents Endpoint

- [x] Create `POST /documents` endpoint with:
  - [x] Path: `/documents`
  - [x] Response model: `DocumentResponse`
  - [x] Status code: 201
- [x] Add parameters:
  - [x] `file: UploadFile = File(...)` - Required file upload
  - [x] `tags: Optional[str] = Form(None)` - Comma-separated tags
  - [x] `metadata: Optional[str] = Form(None)` - JSON string of metadata
- [x] Implement stub logic:
  - [x] Parse tags from comma-separated string to list
  - [x] Parse metadata from JSON string to dict (handle parse errors)
  - [x] Create dummy DocumentResponse with:
    - [x] `id: "doc_stub_123"`
    - [x] `filename: file.filename`
    - [x] `content_type: file.content_type or "application/octet-stream"`
    - [x] `size_bytes: 0`
    - [x] `created_at: datetime.now()`
    - [x] `updated_at: datetime.now()`
    - [x] `tags: parsed_tags or []`
    - [x] `metadata: parsed_metadata or {}`
  - [x] Return JSONResponse with status_code=201

### 3.4 GET /documents/{id} Endpoint

- [x] Create `GET /documents/{id}` endpoint with:
  - [x] Path: `/documents/{document_id}`
  - [x] Response model: `DocumentResponse`
  - [x] Path parameter: `document_id: str`
- [x] Implement stub logic:
  - [x] Raise `HTTPException(status_code=501, detail="Document retrieval not yet implemented")`

### 3.5 GET /documents Endpoint

- [x] Create `GET /documents` endpoint with:
  - [x] Path: `/documents`
  - [x] Response model: `list[DocumentResponse]`
- [x] Add query parameters:
  - [x] `tags: Optional[str] = Query(None)` - Comma-separated tag filter
  - [x] `content_type: Optional[str] = Query(None)` - Content type filter
  - [x] `limit: int = Query(100)` - Result limit
  - [x] `offset: int = Query(0)` - Pagination offset
- [x] Implement stub logic:
  - [x] Parse tags if provided
  - [x] Return empty list: `[]`
  - [x] Add comment: "# Stub: Will query database in Block 02"

### 3.6 DELETE /documents/{id} Endpoint

- [x] Create `DELETE /documents/{id}` endpoint with:
  - [x] Path: `/documents/{document_id}`
  - [x] Response model: `DeleteResponse`
  - [x] Path parameter: `document_id: str`
- [x] Implement stub logic:
  - [x] Return DeleteResponse with:
    - [x] `success: True`
    - [x] `message: "Document deletion stub (not yet implemented)"`
    - [x] `document_id: document_id`

### 3.7 Error Handling & Server Entry Point

- [x] Add global exception handler for validation errors (optional but recommended)
- [x] Add `if __name__ == "__main__":` block:
  - [x] Call `uvicorn.run()`
  - [x] Parameters: `app`, `host=DOCUMENT_SERVER_HOST`, `port=DOCUMENT_SERVER_PORT`
  - [x] Add `reload=True` for development

---

## Phase 4: Stub Files

- [x] Create `document-server/src/storage.py`:
  - [x] Add docstring: "Storage layer for filesystem operations (Block 02 implementation)"
  - [x] Create `DocumentStorage` class stub:
    - [x] `def __init__(self, storage_dir: str): pass`
    - [x] `async def save_document(self, doc_id: str, file_content: bytes) -> str: raise NotImplementedError()`
    - [x] `async def get_document(self, doc_id: str) -> bytes: raise NotImplementedError()`
    - [x] `async def delete_document(self, doc_id: str) -> bool: raise NotImplementedError()`
- [x] Create `document-server/src/database.py`:
  - [x] Add docstring: "Database layer for metadata persistence (Block 02 implementation)"
  - [x] Create `DocumentDatabase` class stub:
    - [x] `def __init__(self, db_path: str): pass`
    - [x] `async def insert_metadata(self, metadata: DocumentMetadata) -> None: raise NotImplementedError()`
    - [x] `async def get_metadata(self, doc_id: str) -> DocumentMetadata | None: raise NotImplementedError()`
    - [x] `async def query_metadata(self, params: DocumentQueryParams) -> list[DocumentMetadata]: raise NotImplementedError()`
    - [x] `async def delete_metadata(self, doc_id: str) -> bool: raise NotImplementedError()`

---

## Phase 5: Testing

### 5.1 Server Startup

- [x] Navigate to `document-server/` directory
- [x] Start server: `uv run src/main.py`
- [x] Verify console output shows: "Uvicorn running on http://0.0.0.0:8766"
- [x] Verify no startup errors or import failures
- [x] Check server responds: `curl http://localhost:8766/docs` (should return HTML)

### 5.2 Endpoint Testing

- [x] Test POST /documents with multipart form data:
  ```bash
  curl -X POST http://localhost:8766/documents \
    -F "file=@test.md" \
    -F "tags=test,demo" \
    -F "metadata={\"author\":\"test\"}"
  ```
  - [x] Verify returns 201 status
  - [x] Verify response contains `id: "doc_stub_123"`
  - [x] Verify filename, tags, and metadata are parsed correctly

- [x] Test GET /documents (list all):
  ```bash
  curl http://localhost:8766/documents
  ```
  - [x] Verify returns 200 status
  - [x] Verify returns empty array: `[]`

- [x] Test GET /documents with query parameters:
  ```bash
  curl "http://localhost:8766/documents?tags=test&limit=10"
  ```
  - [x] Verify returns 200 status
  - [x] Verify returns empty array: `[]`

- [x] Test GET /documents/{id} (single document):
  ```bash
  curl http://localhost:8766/documents/doc_123
  ```
  - [x] Verify returns 501 status
  - [x] Verify error detail: "Document retrieval not yet implemented"

- [x] Test DELETE /documents/{id}:
  ```bash
  curl -X DELETE http://localhost:8766/documents/doc_123
  ```
  - [x] Verify returns 200 status
  - [x] Verify response: `{"success": true, "message": "...", "document_id": "doc_123"}`

### 5.3 FastAPI Interactive Docs

- [x] Open browser to http://localhost:8766/docs
- [x] Verify all 4 endpoints are listed:
  - [x] POST /documents
  - [x] GET /documents/{document_id}
  - [x] GET /documents
  - [x] DELETE /documents/{document_id}
- [x] Test POST /documents through Swagger UI:
  - [x] Upload a test file
  - [x] Add tags and metadata
  - [x] Verify 201 response with correct data
- [x] Verify schema definitions show all models correctly

### 5.4 Validation Testing

- [x] Test invalid POST request (missing file):
  ```bash
  curl -X POST http://localhost:8766/documents
  ```
  - [x] Verify returns 422 Unprocessable Entity
  - [x] Verify error mentions "field required"

- [x] Test invalid query parameters (negative limit):
  ```bash
  curl "http://localhost:8766/documents?limit=-1"
  ```
  - [x] Verify Pydantic validation (may return 422 if validation added)

- [x] Test invalid JSON metadata:
  ```bash
  curl -X POST http://localhost:8766/documents \
    -F "file=@test.md" \
    -F "metadata=invalid-json"
  ```
  - [x] Verify handles gracefully (check server logs)

### 5.5 Configuration Testing

- [x] Stop the server (Ctrl+C)
- [x] Test environment variable override:
  ```bash
  DOCUMENT_SERVER_PORT=9999 uv run src/main.py
  ```
  - [x] Verify server starts on port 9999
  - [x] Test endpoint: `curl http://localhost:9999/documents`
  - [x] Stop server

- [x] Restart server on default port 8766:
  ```bash
  uv run src/main.py
  ```
  - [x] Verify clean startup
  - [x] Verify port 8766 is used

### 5.6 Cleanup

- [x] Stop server cleanly (Ctrl+C)
- [x] Verify no zombie processes: `lsof -i :8766` (should be empty)

---

## Phase 6: Documentation

- [x] Create `document-server/README.md` with sections:

### 6.1 Setup Instructions

- [x] Add project overview and purpose
- [x] Document prerequisites:
  - [x] Python 3.11+
  - [x] UV package manager
- [x] Add installation steps:
  ```bash
  cd document-server
  uv sync
  ```
- [x] Add startup instructions:
  ```bash
  uv run src/main.py
  ```

### 6.2 Available Endpoints

- [x] Document POST /documents:
  - [x] Description: Upload a new document
  - [x] Request format: multipart/form-data
  - [x] Parameters: file (required), tags (optional), metadata (optional)
  - [x] Response: 201 Created with DocumentResponse
  - [x] Current status: Stub implementation

- [x] Document GET /documents:
  - [x] Description: List all documents with optional filters
  - [x] Query parameters: tags, content_type, limit, offset
  - [x] Response: 200 OK with list of DocumentResponse
  - [x] Current status: Returns empty list

- [x] Document GET /documents/{id}:
  - [x] Description: Retrieve a specific document by ID
  - [x] Path parameter: document_id
  - [x] Response: 200 OK with DocumentResponse
  - [x] Current status: Returns 501 Not Implemented

- [x] Document DELETE /documents/{id}:
  - [x] Description: Delete a document by ID
  - [x] Path parameter: document_id
  - [x] Response: 200 OK with DeleteResponse
  - [x] Current status: Stub implementation

### 6.3 Example curl Commands

- [x] Add upload example:
  ```bash
  curl -X POST http://localhost:8766/documents \
    -F "file=@example.md" \
    -F "tags=documentation,example" \
    -F "metadata={\"author\":\"John Doe\",\"version\":\"1.0\"}"
  ```

- [x] Add list example:
  ```bash
  curl http://localhost:8766/documents
  ```

- [x] Add filtered list example:
  ```bash
  curl "http://localhost:8766/documents?tags=documentation&limit=10"
  ```

- [x] Add retrieve example:
  ```bash
  curl http://localhost:8766/documents/doc_123
  ```

- [x] Add delete example:
  ```bash
  curl -X DELETE http://localhost:8766/documents/doc_123
  ```

### 6.4 Environment Variables

- [x] Document `DOCUMENT_SERVER_HOST`:
  - [x] Description: Server bind address
  - [x] Default: "0.0.0.0"
  - [x] Example: `DOCUMENT_SERVER_HOST=127.0.0.1 uv run src/main.py`

- [x] Document `DOCUMENT_SERVER_PORT`:
  - [x] Description: Server port number
  - [x] Default: 8766
  - [x] Example: `DOCUMENT_SERVER_PORT=9000 uv run src/main.py`

- [x] Document `DOCUMENT_SERVER_STORAGE`:
  - [x] Description: Storage directory path
  - [x] Default: "./storage"
  - [x] Example: `DOCUMENT_SERVER_STORAGE=/var/documents uv run src/main.py`

### 6.5 Development Notes

- [x] Add note about FastAPI interactive docs: http://localhost:8766/docs
- [x] Add note about stub implementations and future work (Blocks 02-05)
- [x] Add troubleshooting section:
  - [x] Port already in use: Change port with environment variable
  - [x] Import errors: Run `uv sync` to install dependencies
  - [x] Module not found: Ensure running from document-server/ directory

---

## Success Criteria

Upon completion of this checklist, verify all criteria are met:

- [x] FastAPI server starts successfully on port 8766
- [x] All 4 HTTP endpoints (POST, GET list, GET single, DELETE) respond correctly
- [x] POST /documents accepts multipart form data and returns 201 with stub response
- [x] GET /documents returns empty list with 200 status
- [x] GET /documents/{id} returns 501 Not Implemented
- [x] DELETE /documents/{id} returns stub success response
- [x] Pydantic models validate request/response data correctly
- [x] Invalid requests return 422 validation errors
- [x] Environment variables (PORT, HOST, STORAGE) override defaults correctly
- [x] FastAPI interactive docs accessible at /docs
- [x] Server can be stopped and restarted cleanly
- [x] README.md documents setup, endpoints, and usage examples
- [x] Project structure follows conventions:
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
