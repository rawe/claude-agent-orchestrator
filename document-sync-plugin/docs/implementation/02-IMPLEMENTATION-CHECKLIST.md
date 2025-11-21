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
- [ ] Create `DocumentStorage` class skeleton
- [ ] Import required modules: `os`, `hashlib`, `secrets`, `mimetypes`, `pathlib.Path`
- [ ] Import `DocumentMetadata` from `models.py`

### 1.2 Initialization
- [ ] Implement `__init__(self, base_dir: str)` method
- [ ] Store `base_dir` as `Path` object
- [ ] Create base directory with `mkdir(parents=True, exist_ok=True)`

### 1.3 Store Document Method
- [ ] Implement `store_document(self, content: bytes, filename: str) -> DocumentMetadata`
- [ ] Generate unique document ID using pattern `doc_{secrets.token_hex(12)}`
- [ ] Calculate SHA256 checksum:
  ```python
  checksum = hashlib.sha256(content).hexdigest()
  ```
- [ ] Detect MIME type with fallback:
  ```python
  mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
  ```
- [ ] Calculate file size: `len(content)`
- [ ] Write file to flat structure: `base_dir / doc_id`
- [ ] Return `DocumentMetadata` object with all fields populated

### 1.4 Get Document Path Method
- [ ] Implement `get_document_path(self, doc_id: str) -> Path`
- [ ] Resolve absolute path
- [ ] Add path traversal protection:
  ```python
  if not resolved.is_relative_to(self.base_dir.resolve()):
      raise ValueError("Invalid document ID")
  ```
- [ ] Return resolved path

### 1.5 Delete Document Method
- [ ] Implement `delete_document(self, doc_id: str) -> bool`
- [ ] Get document path using `get_document_path()`
- [ ] Check if file exists
- [ ] Delete file using `unlink()` if exists
- [ ] Return `True` if deleted, `False` if not found

### 1.6 Isolation Testing
- [ ] Create test script to verify DocumentStorage independently
- [ ] Test storing a document
- [ ] Test retrieving document path
- [ ] Test deleting a document
- [ ] Verify checksum calculation is correct

---

## Phase 2: Implement DocumentDatabase (database.py)

### 2.1 Class Structure
- [ ] Create `DocumentDatabase` class skeleton
- [ ] Import required modules: `sqlite3`, `datetime`, `typing` (List, Optional)
- [ ] Import `DocumentMetadata` from `models.py`

### 2.2 Initialization and Schema
- [ ] Implement `__init__(self, db_path: str)` method
- [ ] Store connection: `self.conn = sqlite3.connect(db_path, check_same_thread=False)`
- [ ] Set row factory: `self.conn.row_factory = sqlite3.Row`
- [ ] Call `self._init_database()`

### 2.3 Database Schema Creation
- [ ] Implement `_init_database(self)` method
- [ ] Create `documents` table with columns:
  - `id TEXT PRIMARY KEY`
  - `name TEXT NOT NULL`
  - `mime_type TEXT NOT NULL`
  - `size_bytes INTEGER NOT NULL`
  - `checksum TEXT NOT NULL`
  - `upload_date TEXT NOT NULL`
  - `last_accessed TEXT`
  - `access_count INTEGER DEFAULT 0`
  - `storage_path TEXT NOT NULL`
- [ ] Create `document_tags` table with:
  - `document_id TEXT NOT NULL`
  - `tag TEXT NOT NULL`
  - `PRIMARY KEY (document_id, tag)`
  - `FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE`
- [ ] Create index on `document_tags(tag)`
- [ ] Create index on `documents(name)`

### 2.4 Insert Document Method
- [ ] Implement `insert_document(self, metadata: DocumentMetadata)`
- [ ] Convert upload_date to ISO string: `metadata.upload_date.isoformat()`
- [ ] Insert into `documents` table with all 9 columns
- [ ] Insert tags into `document_tags` table (loop through metadata.tags)
- [ ] Commit transaction

### 2.5 Get Document Method
- [ ] Implement `get_document(self, doc_id: str) -> Optional[DocumentMetadata]`
- [ ] Query `documents` table by `id`
- [ ] If not found, return `None`
- [ ] Fetch associated tags from `document_tags` table
- [ ] Parse `upload_date` from ISO string: `datetime.fromisoformat(row['upload_date'])`
- [ ] Construct and return `DocumentMetadata` object

### 2.6 Query Documents Method
- [ ] Implement `query_documents(self, name: Optional[str], tags: Optional[List[str]]) -> List[DocumentMetadata]`
- [ ] Build dynamic SQL query starting with base SELECT
- [ ] Add name filtering with LIKE if provided:
  ```python
  WHERE name LIKE ?  # params: [f"%{name}%"]
  ```
- [ ] Add tag filtering with AND logic if provided:
  ```python
  # Join with document_tags
  # WHERE tag IN (?, ?, ...)
  # GROUP BY document_id
  # HAVING COUNT(DISTINCT tag) = ?  # length of tags list
  ```
- [ ] Execute query with parameters
- [ ] For each result, fetch tags separately
- [ ] Parse upload_date for each row
- [ ] Return list of `DocumentMetadata` objects

### 2.7 Delete Document Method
- [ ] Implement `delete_document(self, doc_id: str) -> bool`
- [ ] Execute DELETE from `documents` WHERE `id = ?`
- [ ] CASCADE will automatically delete from `document_tags`
- [ ] Check `cursor.rowcount` to determine if deleted
- [ ] Commit transaction
- [ ] Return `True` if rowcount > 0, else `False`

### 2.8 Isolation Testing
- [ ] Create test script to verify DocumentDatabase independently
- [ ] Test inserting a document with tags
- [ ] Test getting a document by ID
- [ ] Test querying documents (all, by name, by tags, by both)
- [ ] Test tag AND logic with multiple tags
- [ ] Test deleting a document
- [ ] Verify CASCADE deletion removes tags

---

## Phase 3: Integrate with FastAPI (main.py)

### 3.1 Setup
- [ ] Import `DocumentStorage` from `storage`
- [ ] Import `DocumentDatabase` from `database`
- [ ] Create `STORAGE_DIR = "document-data/files"` constant
- [ ] Create `DB_PATH = "document-data/documents.db"` constant
- [ ] Initialize global instances:
  ```python
  storage = DocumentStorage(STORAGE_DIR)
  db = DocumentDatabase(DB_PATH)
  ```

### 3.2 POST /documents Endpoint
- [ ] Update endpoint to use storage and database
- [ ] Read file content: `content = await file.read()`
- [ ] Store document: `metadata = storage.store_document(content, file.filename)`
- [ ] Set storage_path in metadata
- [ ] Insert into database: `db.insert_document(metadata)`
- [ ] Return metadata as JSON response

### 3.3 GET /documents/{id} Endpoint
- [ ] Update endpoint to retrieve and stream files
- [ ] Get metadata from database: `metadata = db.get_document(document_id)`
- [ ] Return 404 if not found
- [ ] Update last_accessed and increment access_count in database
- [ ] Get file path: `file_path = storage.get_document_path(document_id)`
- [ ] Return `FileResponse` with headers:
  ```python
  FileResponse(
      file_path,
      media_type=metadata.mime_type,
      filename=metadata.name
  )
  ```

### 3.4 GET /documents Endpoint (Query)
- [ ] Update endpoint to query database
- [ ] Parse query parameters: `name` and `tags`
- [ ] Convert tags from comma-separated string to list if provided
- [ ] Call `db.query_documents(name, tags)`
- [ ] Return list of metadata as JSON response

### 3.5 DELETE /documents/{id} Endpoint
- [ ] Update endpoint to delete from both storage and database
- [ ] Delete from database: `db_deleted = db.delete_document(document_id)`
- [ ] Delete from storage: `storage_deleted = storage.delete_document(document_id)`
- [ ] Return 404 if not found in database
- [ ] Return success response

---

## Phase 4: End-to-End Testing

### 4.1 Upload Flow
- [ ] Start FastAPI server
- [ ] Upload a test document with tags using POST /documents
- [ ] Verify response contains correct metadata (ID, checksum, size, MIME type)
- [ ] Verify file exists in `document-data/files/` directory
- [ ] Verify database entry exists with correct metadata

### 4.2 Query Operations
- [ ] Test GET /documents (retrieve all documents)
- [ ] Test GET /documents?name=partial (partial name match)
- [ ] Test GET /documents?tags=tag1 (single tag filter)
- [ ] Test GET /documents?tags=tag1,tag2 (multiple tags with AND logic)
- [ ] Test GET /documents?name=partial&tags=tag1 (combined filters)
- [ ] Verify AND logic: documents must have ALL specified tags

### 4.3 Download and Integrity
- [ ] Test GET /documents/{id} to download document
- [ ] Verify Content-Type header matches MIME type
- [ ] Verify Content-Disposition header contains original filename
- [ ] Calculate SHA256 of downloaded content
- [ ] Verify checksum matches original
- [ ] Verify access_count incremented in database

### 4.4 Delete Operations
- [ ] Test DELETE /documents/{id} for existing document
- [ ] Verify 200 response
- [ ] Verify file removed from storage directory
- [ ] Verify database entry removed
- [ ] Verify tags removed from document_tags table (CASCADE)
- [ ] Test DELETE /documents/{id} for non-existent document (404)

### 4.5 Persistence
- [ ] Upload multiple documents
- [ ] Stop FastAPI server
- [ ] Restart FastAPI server
- [ ] Query documents and verify all are still present
- [ ] Download a document and verify integrity

### 4.6 Error Cases
- [ ] Test GET /documents/{id} with invalid ID (404)
- [ ] Test path traversal attempt: `../../../etc/passwd`
- [ ] Verify path traversal protection works
- [ ] Test DELETE /documents/{id} with invalid ID (404)
- [ ] Test uploading very large file (if size limits implemented)

---

## Success Criteria

- [ ] **DocumentStorage fully functional**: Can store, retrieve paths, and delete files with correct checksums and MIME types
- [ ] **DocumentDatabase fully functional**: Can insert, query, retrieve, and delete documents with tag support
- [ ] **Tag AND logic works correctly**: Querying with multiple tags returns only documents having ALL tags
- [ ] **FastAPI integration complete**: All endpoints use storage and database, no more stub responses
- [ ] **File integrity verified**: Downloaded files match uploaded files (checksum validation)
- [ ] **Persistence confirmed**: Data survives server restarts
- [ ] **Path traversal protection**: Cannot access files outside storage directory
- [ ] **CASCADE deletion works**: Deleting document removes all associated tags
- [ ] **Access tracking works**: last_accessed and access_count updated on document retrieval
- [ ] **Error handling**: Proper 404 responses for missing documents

---

## Implementation Notes

### SHA256 Checksum Calculation
```python
import hashlib
checksum = hashlib.sha256(content).hexdigest()
```

### MIME Type Detection with Fallback
```python
import mimetypes
mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
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
    media_type=metadata.mime_type,
    filename=metadata.name  # Sets Content-Disposition header
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

## Getting Started

1. Start with Phase 1 (DocumentStorage) and test it in isolation
2. Move to Phase 2 (DocumentDatabase) and test it in isolation
3. Integrate both in Phase 3 (FastAPI endpoints)
4. Complete comprehensive testing in Phase 4
5. Check off all success criteria before considering block complete