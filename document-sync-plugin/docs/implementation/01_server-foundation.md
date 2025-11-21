# Implementation Block 01: Server Foundation

## Goal
Build the FastAPI server skeleton with all HTTP endpoints, Pydantic models, and basic routing. Create a working HTTP server that can be tested with curl/Postman.

## Benefit
🎯 **Testable HTTP API** - By the end of this session, you'll have a running server on port 8766 that responds to requests, even if it doesn't persist data yet.

## MVP Architecture Reference

**Document**: [`architecture-mvp.md`](../architecture-mvp.md)

**Relevant Sections**:
- `main.py - FastAPI Server (Port 8766)` (lines 350-460)
- `models.py - Data Models` (lines 305-346)
- `Environment Variables` (lines 766-787)

## What Gets Built

### 1. Project Structure
```
document-server/
├── pyproject.toml          # UV project config
├── uv.lock                 # Lockfile
├── src/
│   ├── __init__.py
│   ├── main.py             # FastAPI app + endpoints
│   ├── models.py           # Pydantic models
│   ├── storage.py          # Stub for now
│   └── database.py         # Stub for now
└── README.md
```

### 2. Core Components

**pyproject.toml**
- Project metadata
- Dependencies: `fastapi`, `uvicorn`, `httpx`, `pydantic`
- Python version: `>=3.11`

**models.py**
- `DocumentMetadata` - Full metadata model with storage_path
- `DocumentUploadRequest` - Form data validation
- `DocumentQueryParams` - Query parameter validation
- `DocumentResponse` - API response model (excludes storage_path)
- `DeleteResponse` - Deletion confirmation model

**main.py**
- FastAPI app initialization with title/version
- Configuration loading from ENV with hardcoded fallbacks
- Four endpoint stubs:
  - `POST /documents` - Upload (returns dummy response)
  - `GET /documents/{id}` - Download (returns 501 Not Implemented)
  - `GET /documents` - Query (returns empty list)
  - `DELETE /documents/{id}` - Delete (returns dummy response)
- Proper error handling (404, 400, 500)
- `if __name__ == "__main__"` block to run uvicorn

**storage.py & database.py**
- Empty class stubs with docstrings
- Will be implemented in Block 02

## Session Flow

### Step 1: Initialize Project (~30min)
1. Create `document-server/` directory
2. Run `uv init` to create pyproject.toml
3. Add dependencies to pyproject.toml
4. Run `uv sync` to create lockfile
5. Create `src/` directory structure

### Step 2: Build Pydantic Models (~30min)
1. Create `models.py` with all 5 model classes
2. Ensure proper imports (datetime, Optional, List)
3. Add field descriptions and defaults
4. Test models work with `uv run python -c "from src.models import *"`

### Step 3: Create FastAPI App (~60min)
1. Create `main.py` with app initialization
2. Add centralized config constants (host, port, defaults)
3. Implement all 4 endpoint function signatures
4. Add basic error handling
5. Return stub responses (hardcoded example data)

### Step 4: Test Server (~30min)
1. Start server: `uv run src/main.py`
2. Verify server starts on port 8766
3. Test each endpoint with curl:
   ```bash
   # Upload (multipart form-data)
   curl -X POST http://localhost:8766/documents \
     -F "file=@test.txt" \
     -F "name=Test Doc" \
     -F "tags=test"

   # Query
   curl http://localhost:8766/documents

   # Download (expect 501)
   curl http://localhost:8766/documents/doc_test123

   # Delete
   curl -X DELETE http://localhost:8766/documents/doc_test123
   ```
4. Verify JSON responses match models

### Step 5: Documentation (~20min)
1. Create `README.md` with:
   - How to run the server
   - Available endpoints
   - Example curl commands
   - Environment variables
2. Access FastAPI auto-docs: `http://localhost:8766/docs`

## Success Criteria ✅

- [ ] `uv sync` completes without errors
- [ ] Server starts and listens on port 8766
- [ ] All 4 endpoints respond (even with stub data)
- [ ] FastAPI docs accessible at `/docs`
- [ ] Pydantic validation works (try invalid data, get 422)
- [ ] ENV variables override defaults (test DOCUMENT_SERVER_PORT)
- [ ] Can stop and restart server cleanly

## Implementation Hints & Gotchas

### Configuration Pattern
Use this pattern for centralized defaults:
```python
# At top of main.py
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
DEFAULT_STORAGE_DIR = ".document-storage"

# In code
host = os.getenv("DOCUMENT_SERVER_HOST", DEFAULT_HOST)
```

### Multipart Form Data
The upload endpoint uses `File(...)` and `Form(...)` - FastAPI handles this automatically:
```python
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...),
    tags: str = Form(""),
    description: str = Form("")
):
    content = await file.read()  # bytes
    # For now, just return dummy response
```

### Stub Responses
Don't try to store data yet - just return valid JSON:
```python
return DocumentResponse(
    document_id="doc_stub123",
    name=name,
    original_filename=file.filename,
    tags=[t.strip() for t in tags.split(",") if t.strip()],
    description=description,
    size_bytes=len(content),
    mime_type="application/octet-stream",
    checksum_sha256="stub_checksum",
    uploaded_at=datetime.now(UTC).isoformat()
)
```

### Error Handling
Use FastAPI's HTTPException:
```python
if not found:
    raise HTTPException(status_code=404, detail="Document not found")
```

### Testing Multipart Uploads
Use curl with `-F` flag for multipart form data. Create a test file first:
```bash
echo "test content" > test.txt
curl -X POST http://localhost:8766/documents \
  -F "file=@test.txt" \
  -F "name=Test" \
  -F "tags=test,demo"
```

## Dependencies for Next Block
- ✅ FastAPI server running
- ✅ All endpoint signatures defined
- ✅ Pydantic models validated
- ✅ Project structure in place

## Estimated Time
**3-4 hours** including setup, implementation, testing, and documentation.

## Notes
- Don't worry about persistence yet - stubs are fine
- Focus on getting the HTTP layer working correctly
- FastAPI auto-docs (`/docs`) are great for testing without curl
- The server won't be useful yet, but this foundation is critical
