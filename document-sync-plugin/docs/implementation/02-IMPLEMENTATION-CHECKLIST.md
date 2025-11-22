# Block 02: Storage & Database - Implementation Checklist

## Project Structure Reference

```
document-sync-plugin/
├── skills/document-sync/           # Skill for Claude Code (Blocks 03, 05)
│   └── commands/lib/               # Client library
└── document-server/                # THIS BLOCK - Extends Block 01
    ├── pyproject.toml
    ├── uv.lock
    └── src/
        ├── main.py                 # Update to integrate storage/DB
        ├── models.py               # Already exists from Block 01
        ├── storage.py              # IMPLEMENT in this block
        └── database.py             # IMPLEMENT in this block
```

**This block focuses on: `document-server/src/storage.py` and `document-server/src/database.py`**

## Overall Goal

Implement persistent document storage with a file system backend (DocumentStorage) and SQLite metadata database (DocumentDatabase), then integrate both with the FastAPI endpoints to provide full CRUD operations.

## Checkpoint Instructions

Mark each checkbox as done `[x]` when you complete that step. Work through the phases sequentially, testing as you go.

## Referenced Files

- `document-server/src/storage.py` - Replace stub with full DocumentStorage implementation
- `document-server/src/database.py` - Replace stub with full DocumentDatabase implementation
- `document-server/src/main.py` - Integrate storage and database with FastAPI endpoints

---

## Phase 1: Implement DocumentStorage (storage.py)

### 1.1 Class Structure
- [x] Create `DocumentStorage` class skeleton
- [x] Import required modules: `os`, `hashlib`, `secrets`, `mimetypes`, `pathlib.Path`
- [x] Import `DocumentMetadata` from `models.py`

### 1.2 Initialization
- [x] Implement `__init__(self, base_dir: str)` method
- [x] Store `base_dir` as `Path` object
- [x] Create base directory with `mkdir(parents=True, exist_ok=True)`

### 1.3 Store Document Method
- [x] Implement `store_document(self, content: bytes, filename: str) -> DocumentMetadata`
- [x] Generate unique document ID using pattern `doc_{secrets.token_hex(12)}`
- [x] Calculate SHA256 checksum:
  ```python
  checksum = hashlib.sha256(content).hexdigest()
  ```
- [x] Detect MIME type with fallback:
  ```python
  content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
  ```
- [x] Calculate file size: `len(content)`
- [x] Write file to flat structure: `base_dir / doc_id`
- [x] Return `DocumentMetadata` object with all fields populated

### 1.4 Get Document Path Method
- [x] Implement `get_document_path(self, doc_id: str) -> Path`
- [x] Resolve absolute path
- [x] Add path traversal protection:
  ```python
  if not resolved.is_relative_to(self.base_dir.resolve()):
      raise ValueError("Invalid document ID")
  ```
- [x] Return resolved path

### 1.5 Delete Document Method
- [x] Implement `delete_document(self, doc_id: str) -> bool`
- [x] Get document path using `get_document_path()`
- [x] Check if file exists
- [x] Delete file using `unlink()` if exists
- [x] Return `True` if deleted, `False` if not found

### 1.6 Isolation Testing
- [x] Create test script to verify DocumentStorage independently
- [x] Test storing a document
- [x] Test retrieving document path
- [x] Test deleting a document
- [x] Verify checksum calculation is correct

---

## Phase 2: Implement DocumentDatabase (database.py)

### 2.1 Class Structure
- [x] Create `DocumentDatabase` class skeleton
- [x] Import required modules: `sqlite3`, `datetime`, `typing` (List, Optional)
- [x] Import `DocumentMetadata` from `models.py`

### 2.2 Initialization and Schema
- [x] Implement `__init__(self, db_path: str)` method
- [x] Store connection: `self.conn = sqlite3.connect(db_path, check_same_thread=False)`
- [x] Set row factory: `self.conn.row_factory = sqlite3.Row`
- [x] Call `self._init_database()`

### 2.3 Database Schema Creation
- [x] Implement `_init_database(self)` method
- [x] Create `documents` table with columns (using consistent field names):
  - `id TEXT PRIMARY KEY`
  - `filename TEXT NOT NULL` (keeping Block 01 naming)
  - `content_type TEXT NOT NULL` (keeping Block 01 naming)
  - `size_bytes INTEGER NOT NULL`
  - `checksum TEXT NOT NULL`
  - `storage_path TEXT NOT NULL`
  - `created_at TEXT NOT NULL` (keeping Block 01 naming)
  - `updated_at TEXT NOT NULL` (keeping Block 01 naming)
  - ~~`last_accessed TEXT`~~ (YAGNI - not implemented)
  - ~~`access_count INTEGER DEFAULT 0`~~ (YAGNI - not implemented)
- [x] Create `document_tags` table with:
  - `document_id TEXT NOT NULL`
  - `tag TEXT NOT NULL`
  - `PRIMARY KEY (document_id, tag)`
  - `FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE`
- [x] Create index on `document_tags(tag)`
- [x] Create index on `documents(filename)`

### 2.4 Insert Document Method
- [x] Implement `insert_document(self, metadata: DocumentMetadata)`
- [x] Convert created_at to ISO string: `metadata.created_at.isoformat()`
- [x] Insert into `documents` table with all columns
- [x] Insert tags into `document_tags` table (loop through metadata.tags)
- [x] Commit transaction

### 2.5 Get Document Method
- [x] Implement `get_document(self, doc_id: str) -> Optional[DocumentMetadata]`
- [x] Query `documents` table by `id`
- [x] If not found, return `None`
- [x] Fetch associated tags from `document_tags` table
- [x] Parse `created_at` from ISO string: `datetime.fromisoformat(row['created_at'])`
- [x] Construct and return `DocumentMetadata` object

### 2.6 Query Documents Method
- [x] Implement `query_documents(self, filename: Optional[str], tags: Optional[List[str]]) -> List[DocumentMetadata]`
- [x] Build dynamic SQL query starting with base SELECT
- [x] Add filename filtering with LIKE if provided:
  ```python
  WHERE filename LIKE ?  # params: [f"%{filename}%"]
  ```
- [x] Add tag filtering with AND logic if provided:
  ```python
  # Join with document_tags
  # WHERE tag IN (?, ?, ...)
  # GROUP BY document_id
  # HAVING COUNT(DISTINCT tag) = ?  # length of tags list
  ```
- [x] Execute query with parameters
- [x] For each result, fetch tags separately
- [x] Parse created_at for each row
- [x] Return list of `DocumentMetadata` objects

### 2.7 Delete Document Method
- [x] Implement `delete_document(self, doc_id: str) -> bool`
- [x] Execute DELETE from `documents` WHERE `id = ?`
- [x] CASCADE will automatically delete from `document_tags`
- [x] Check `cursor.rowcount` to determine if deleted
- [x] Commit transaction
- [x] Return `True` if rowcount > 0, else `False`

### 2.8 Isolation Testing
- [x] Create test script to verify DocumentDatabase independently
- [x] Test inserting a document with tags
- [x] Test getting a document by ID
- [x] Test querying documents (all, by filename, by tags, by both)
- [x] Test tag AND logic with multiple tags
- [x] Test deleting a document
- [x] Verify CASCADE deletion removes tags

---

## Phase 3: Integrate with FastAPI (main.py)

### 3.1 Setup
- [x] Import `DocumentStorage` from `storage`
- [x] Import `DocumentDatabase` from `database`
- [x] Create `STORAGE_DIR = "document-data/files"` constant
- [x] Create `DB_PATH = "document-data/documents.db"` constant
- [x] Initialize global instances:
  ```python
  storage = DocumentStorage(STORAGE_DIR)
  db = DocumentDatabase(DB_PATH)
  ```

### 3.2 POST /documents Endpoint
- [x] Update endpoint to use storage and database
- [x] Read file content: `content = await file.read()`
- [x] Store document: `metadata = storage.store_document(content, file.filename)`
- [x] Set storage_path in metadata (done automatically by storage)
- [x] Insert into database: `db.insert_document(metadata)`
- [x] Return metadata as JSON response

### 3.3 GET /documents/{id} Endpoint
- [x] Update endpoint to retrieve and stream files
- [x] Get metadata from database: `metadata = db.get_document(document_id)`
- [x] Return 404 if not found
- [ ] ~~Update last_accessed and increment access_count in database~~ (YAGNI - not implemented)
- [x] Get file path: `file_path = storage.get_document_path(document_id)`
- [x] Return `FileResponse` with headers:
  ```python
  FileResponse(
      file_path,
      media_type=metadata.content_type,
      filename=metadata.filename
  )
  ```

### 3.4 GET /documents Endpoint (Query)
- [x] Update endpoint to query database
- [x] Parse query parameters: `filename` and `tags`
- [x] Convert tags from comma-separated string to list if provided
- [x] Call `db.query_documents(filename, tags)`
- [x] Return list of metadata as JSON response

### 3.5 DELETE /documents/{id} Endpoint
- [x] Update endpoint to delete from both storage and database
- [x] Delete from database: `db_deleted = db.delete_document(document_id)`
- [x] Delete from storage: `storage_deleted = storage.delete_document(document_id)`
- [x] Return 404 if not found in database
- [x] Return success response

---

## Phase 4: End-to-End Testing

### 4.1 Upload Flow
- [x] Start FastAPI server
- [x] Upload a test document with tags using POST /documents
- [x] Verify response contains correct metadata (ID, checksum, size, MIME type)
- [x] Verify file exists in `document-data/files/` directory
- [x] Verify database entry exists with correct metadata

### 4.2 Query Operations
- [x] Test GET /documents (retrieve all documents)
- [x] Test GET /documents?filename=partial (partial filename match)
- [x] Test GET /documents?tags=tag1 (single tag filter)
- [x] Test GET /documents?tags=tag1,tag2 (multiple tags with AND logic)
- [x] Test GET /documents?filename=partial&tags=tag1 (combined filters)
- [x] Verify AND logic: documents must have ALL specified tags

### 4.3 Download and Integrity
- [x] Test GET /documents/{id} to download document
- [x] Verify Content-Type header matches MIME type
- [x] Verify Content-Disposition header contains original filename
- [x] Calculate SHA256 of downloaded content
- [x] Verify checksum matches original
- [ ] ~~Verify access_count incremented in database~~ (YAGNI - not implemented)

### 4.4 Delete Operations
- [x] Test DELETE /documents/{id} for existing document
- [x] Verify 200 response
- [x] Verify file removed from storage directory
- [x] Verify database entry removed
- [x] Verify tags removed from document_tags table (CASCADE)
- [x] Test DELETE /documents/{id} for non-existent document (404)

### 4.5 Persistence
- [x] Upload multiple documents
- [x] Stop FastAPI server
- [x] Restart FastAPI server
- [x] Query documents and verify all are still present
- [x] Download a document and verify integrity

### 4.6 Error Cases
- [x] Test GET /documents/{id} with invalid ID (404)
- [x] Test path traversal attempt: `../../../etc/passwd`
- [x] Verify path traversal protection works
- [x] Test DELETE /documents/{id} with invalid ID (404)
- [ ] Test uploading very large file (if size limits implemented) - Not required

---

## Success Criteria

- [x] **DocumentStorage fully functional**: Can store, retrieve paths, and delete files with correct checksums and MIME types
- [x] **DocumentDatabase fully functional**: Can insert, query, retrieve, and delete documents with tag support
- [x] **Tag AND logic works correctly**: Querying with multiple tags returns only documents having ALL tags
- [x] **FastAPI integration complete**: All endpoints use storage and database, no more stub responses
- [x] **File integrity verified**: Downloaded files match uploaded files (checksum validation)
- [x] **Persistence confirmed**: Data survives server restarts
- [x] **Path traversal protection**: Cannot access files outside storage directory
- [x] **CASCADE deletion works**: Deleting document removes all associated tags
- [ ] ~~**Access tracking works**: last_accessed and access_count updated on document retrieval~~ (YAGNI - not implemented)
- [x] **Error handling**: Proper 404 responses for missing documents

---

## Implementation Notes

### Field Name Consistency

**Decision**: We maintained consistent field names from Block 01 throughout the implementation:
- `filename` (not `name`)
- `content_type` (not `mime_type`)
- `created_at` / `updated_at` (not `upload_date`)

This ensures compatibility with Block 01 and avoids confusing field name mappings between the Python model and database.

### YAGNI Principle Applied

The following features were intentionally omitted as unnecessary (YAGNI):
- `last_accessed` field - Not needed for MVP
- `access_count` field - Not needed for MVP

We can add these later if actual usage shows they're needed.

### SHA256 Checksum Calculation
```python
import hashlib
checksum = hashlib.sha256(content).hexdigest()
```

### MIME Type Detection with Fallback
```python
import mimetypes
content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
```

### SQLite Row Factory (for column access by name)
```python
conn.row_factory = sqlite3.Row
# Then access columns as: row['column_name']
```

### Tag AND Logic SQL Pattern
```python
# To find documents with ALL specified tags (e.g., ['python', 'tutorial'])
query = """
    SELECT DISTINCT d.* FROM documents d
    JOIN document_tags dt ON d.id = dt.document_id
    WHERE dt.tag IN (?, ?)
    GROUP BY d.id
    HAVING COUNT(DISTINCT dt.tag) = 2
"""
```

### FileResponse Headers
```python
from fastapi.responses import FileResponse

FileResponse(
    path=file_path,
    media_type=metadata.content_type,
    filename=metadata.filename
)
```

### DateTime Handling (ISO String Storage/Parsing)
```python
from datetime import datetime

# Store as ISO string
iso_string = datetime.now().isoformat()

# Parse from ISO string
dt = datetime.fromisoformat(iso_string)
```

### Path Traversal Protection
```python
from pathlib import Path

resolved = path.resolve()
if not resolved.is_relative_to(self.base_dir.resolve()):
    raise ValueError("Invalid document ID - path traversal attempt")
```

### Document ID Generation
```python
import secrets
doc_id = f"doc_{secrets.token_hex(12)}"  # Generates: doc_a1b2c3d4e5f6a7b8c9d0e1f2
```

---

## Status: ✅ COMPLETE

Block 02 has been successfully implemented and tested. All core functionality is working:
- Document storage with checksums and MIME type detection
- SQLite database with tag support and AND logic
- Full CRUD operations via FastAPI endpoints
- Path traversal protection
- CASCADE deletion
- Data persistence across server restarts

Ready to proceed to Block 03: CLI Commands implementation.
