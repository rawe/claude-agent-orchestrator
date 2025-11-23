# Implementation Block 02: Storage & Database

## Goal
Implement the file storage system (DocumentStorage) and SQLite metadata database (DocumentDatabase). Connect these to the FastAPI endpoints to enable actual persistence.

## Benefit
🎯 **Persistent Document Storage** - Documents uploaded via API are saved to disk with metadata in SQLite. Data survives server restarts. The system becomes actually useful.

## MVP Architecture Reference

**Document**: [`architecture-mvp.md`](../architecture-mvp.md)

**Relevant Sections**:
- `storage.py - File System Abstraction (MVP Simplified)` (lines 463-534)
- `database.py - SQLite Metadata Storage` (lines 559-730)
- `main.py` - Integration points for storage/DB

## What Gets Built

### 1. File Storage System (storage.py)

**Key Features**:
- Flat directory structure (`.document-storage/`)
- Document ID generation: `doc_{12-char-hex}`
- SHA256 checksum calculation
- MIME type detection
- Path traversal protection

**Methods**:
- `store_document()` - Save file, return metadata
- `get_document_path()` - Safe path resolution
- `delete_document()` - Remove file from disk

### 2. SQLite Database (database.py)

**Schema**:
- `documents` table - Core metadata
- `document_tags` table - Tag relationships
- Indexes on `tag` and `name` columns
- CASCADE deletion for tags

**Methods**:
- `_init_database()` - Create tables/indexes
- `insert_document()` - Save metadata + tags
- `get_document()` - Retrieve by ID with tags
- `query_documents()` - Filter by name/tags (AND logic)
- `delete_document()` - Remove metadata

### 3. Integration with FastAPI

Wire storage and database into the endpoint stubs from Block 01:
- Initialize storage/DB instances in `main.py`
- Replace stub responses with actual storage/retrieval
- Add proper error handling
- Stream files for downloads

## Session Flow

### Step 1: Implement DocumentStorage (~60min)

1. **Create storage.py skeleton**
   - Import: pathlib, hashlib, uuid, datetime, mimetypes
   - Define DocumentStorage class with `__init__`
   - Create base directory on initialization

2. **Implement store_document()**
   - Generate document ID with uuid
   - Calculate SHA256 checksum
   - Detect MIME type using mimetypes
   - Write bytes to flat file (`.document-storage/{doc_id}`)
   - Return DocumentMetadata

3. **Implement get_document_path()**
   - Use `Path(storage_path).name` to prevent traversal
   - Return absolute path

4. **Implement delete_document()**
   - Get safe path, check exists, unlink

5. **Test in isolation**
   ```python
   # Test script
   storage = DocumentStorage()
   metadata = storage.store_document(
       content=b"test",
       filename="test.txt",
       name="Test",
       tags=["test"],
       description=""
   )
   print(metadata.document_id)
   path = storage.get_document_path(metadata.storage_path)
   print(path.read_bytes())
   storage.delete_document(metadata.storage_path)
   ```

### Step 2: Implement DocumentDatabase (~90min)

1. **Create database.py skeleton**
   - Import: sqlite3, pathlib, typing, models, datetime
   - Define DocumentDatabase class with db_path

2. **Implement _init_database()**
   - Create documents table (9 columns)
   - Create document_tags table (2 columns, compound PK)
   - Add foreign key constraint with CASCADE
   - Create indexes on tag and name
   - Call in `__init__`

3. **Implement insert_document()**
   - Insert into documents table (9 values)
   - Loop through tags, insert into document_tags
   - Commit transaction

4. **Implement get_document()**
   - Query documents by ID
   - Query tags separately
   - Return DocumentMetadata or None
   - Parse ISO datetime string

5. **Implement query_documents()**
   - Build dynamic SQL with JOIN for tags
   - Add WHERE conditions for name (LIKE) and tags (IN)
   - Use GROUP BY + HAVING for AND logic
   - ORDER BY uploaded_at DESC
   - Fetch tags for each result

6. **Implement delete_document()**
   - Simple DELETE (CASCADE handles tags)

7. **Test in isolation**
   ```python
   # Test script
   db = DocumentDatabase()
   db.insert_document(metadata)
   doc = db.get_document(metadata.document_id)
   print(doc.name)
   results = db.query_documents(tags_filter=["test"])
   print(len(results))
   db.delete_document(metadata.document_id)
   ```

### Step 3: Integrate with FastAPI Endpoints (~60min)

1. **Update main.py imports**
   - Import DocumentStorage, DocumentDatabase

2. **Initialize instances**
   ```python
   storage_dir = os.getenv("DOCUMENT_STORAGE_DIR", DEFAULT_STORAGE_DIR)
   storage = DocumentStorage(base_dir=storage_dir)
   db = DocumentDatabase(db_path=Path(storage_dir) / "documents.db")
   ```

3. **Implement POST /documents**
   - Read file content: `await file.read()`
   - Call `storage.store_document()`
   - Call `db.insert_document()`
   - Return DocumentResponse

4. **Implement GET /documents/{id}**
   - Call `db.get_document()`
   - Raise 404 if not found
   - Call `storage.get_document_path()`
   - Return FileResponse with headers

5. **Implement GET /documents**
   - Parse tags from comma-separated string
   - Call `db.query_documents()`
   - Return list of DocumentResponse

6. **Implement DELETE /documents/{id}**
   - Get metadata from DB (404 if missing)
   - Call `storage.delete_document()`
   - Call `db.delete_document()`
   - Return DeleteResponse

### Step 4: End-to-End Testing (~30min)

1. **Start fresh server**
   ```bash
   rm -rf .document-storage  # Clean slate
   uv run src/main.py
   ```

2. **Test upload**
   ```bash
   echo "Architecture doc content" > arch.md
   curl -X POST http://localhost:8766/documents \
     -F "file=@arch.md" \
     -F "name=Architecture" \
     -F "tags=design,docs" \
     -F "description=System architecture"
   # Save document_id from response
   ```

3. **Test query**
   ```bash
   # Query all
   curl http://localhost:8766/documents | jq

   # Query by tag
   curl http://localhost:8766/documents?tags=design | jq

   # Query by name
   curl http://localhost:8766/documents?name=arch | jq

   # AND logic test - upload another doc with different tags
   curl http://localhost:8766/documents?tags=design,docs | jq
   ```

4. **Test download**
   ```bash
   curl http://localhost:8766/documents/{DOC_ID} -o downloaded.md
   diff arch.md downloaded.md  # Should be identical
   ```

5. **Test delete**
   ```bash
   curl -X DELETE http://localhost:8766/documents/{DOC_ID}
   # Verify query returns empty
   curl http://localhost:8766/documents | jq
   # Verify file deleted from .document-storage/
   ls .document-storage/
   ```

6. **Test persistence**
   - Stop server (Ctrl+C)
   - Upload a document
   - Restart server
   - Query - should return the document
   - Check `.document-storage/` directory structure

7. **Test error cases**
   ```bash
   # 404 on missing document
   curl http://localhost:8766/documents/doc_nonexistent

   # Path traversal attempt
   curl http://localhost:8766/documents/../../../etc/passwd
   ```

## Success Criteria ✅

- [ ] `.document-storage/` directory created automatically
- [ ] `documents.db` created with correct schema
- [ ] Files saved with doc_* IDs (flat structure)
- [ ] Upload → Query → Download → Delete flow works
- [ ] SHA256 checksums calculated correctly
- [ ] MIME types detected properly (test .md, .txt, .json)
- [ ] Tag AND logic works (query with multiple tags)
- [ ] Data persists across server restarts
- [ ] Path traversal protection works
- [ ] CASCADE deletion removes tags when document deleted

## Implementation Hints & Gotchas

### SHA256 Calculation
```python
import hashlib
checksum = hashlib.sha256(content).hexdigest()
# Returns hex string like "a1b2c3d4..."
```

### MIME Type Fallback
```python
import mimetypes
mime_type, _ = mimetypes.guess_type(filename)
if not mime_type:
    mime_type = "application/octet-stream"
```

### SQLite Row Factory
For easier column access by name:
```python
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * ...").fetchone()
print(row["document_id"])  # Access by name
```

### AND Logic SQL
The tricky part - must use GROUP BY + HAVING:
```sql
SELECT DISTINCT d.*
FROM documents d
JOIN document_tags dt ON d.document_id = dt.document_id
WHERE dt.tag IN ('design', 'docs')
GROUP BY d.document_id
HAVING COUNT(DISTINCT dt.tag) = 2  -- Must match ALL tags
```

### FileResponse Headers
Important for client-side filename handling:
```python
from fastapi.responses import FileResponse
return FileResponse(
    path=file_path,
    media_type=metadata.mime_type,
    filename=metadata.original_filename,  # Browser uses this
    headers={
        "X-Document-Name": metadata.name,
        "X-Document-ID": metadata.document_id
    }
)
```

### DateTime Handling
SQLite stores as ISO string, must parse:
```python
from datetime import datetime
uploaded_at=datetime.fromisoformat(row["uploaded_at"])
```

### Testing Path Traversal Protection
The `Path(storage_path).name` trick strips directory components:
```python
Path("../../../etc/passwd").name  # Returns "passwd"
Path("doc_abc123").name           # Returns "doc_abc123"
```

## Common Issues

**Issue**: Database locked error
- **Solution**: Always close connections, use context managers

**Issue**: Tags not filtering correctly
- **Solution**: Check AND logic in query_documents - must count distinct tags

**Issue**: MIME type always generic
- **Solution**: Ensure filename passed correctly, check mimetypes.guess_type

**Issue**: Files not deleted from disk
- **Solution**: Check get_document_path returns correct path, file.exists() before unlink

## Dependencies for Next Block
- ✅ Storage system working
- ✅ Database schema created
- ✅ All CRUD operations functional
- ✅ Data persists across restarts

## Estimated Time
**3-4 hours** including implementation, testing, and debugging.

## Notes
- Test each component in isolation before integration
- SQLite is forgiving but watch for SQL injection (use parameterized queries)
- The flat storage is intentional - easy to migrate to partitioned later
- Keep test documents small for faster iteration
