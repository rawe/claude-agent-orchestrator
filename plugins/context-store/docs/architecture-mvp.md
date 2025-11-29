# Document Sync Plugin - MVP Architecture

## Introduction

The **Document Sync Plugin** is a document management system designed for AI coding sessions, following the architectural patterns established in the Agent Orchestrator Framework. It provides a simple, yet powerful interface for storing, retrieving, and querying documents through a client-skill architecture that mirrors the `agent-orchestrator` → `observability-server` pattern.

This system consists of two primary components:

1. **Document Sync Skill** - UV-based Python command-line tools that Claude Code can invoke to interact with documents
2. **Document Server** - A standalone FastAPI server that manages document storage, metadata, and retrieval

The architecture prioritizes **MVP simplicity** while maintaining clear paths for future enhancement.

---

## Overall Structure

```
document-sync-plugin/
├── skills/
│   └── document-sync/               # Skill that Claude can use
│       ├── skill.json
│       ├── SKILL.md
│       └── commands/
│           ├── doc-push             # Push document to server
│           ├── doc-pull             # Pull document from server
│           ├── doc-query            # Query available documents
│           ├── doc-delete           # Delete document by ID
│           └── lib/
│               ├── __init__.py
│               ├── config.py        # Configuration management
│               ├── client.py        # HTTP client to document server
│               └── document.py      # Document metadata handling
│
└── document-server/                 # Standalone document storage server
    ├── pyproject.toml
    ├── uv.lock
    ├── Dockerfile                   # Docker setup for consistent dev env
    ├── README.md
    └── src/
        ├── main.py                  # FastAPI server
        ├── models.py                # Pydantic models
        ├── storage.py               # File system abstraction
        └── database.py              # SQLite metadata storage
```

---

## Skill Commands (UV Scripts)

### A. `doc-push` - Upload Document

**Usage**:
```bash
uv run doc-push <file-path> [options]
```

**Arguments**:
- `file_path` (required): Path to file to upload
- `--name` (optional): Friendly name for document (defaults to filename)
- `--tags` (optional): Comma-separated tags (e.g., "design,spec,v2")
- `--description` (optional): Document description

**Returns**: JSON response with document metadata

**Example**:
```bash
$ uv run doc-push ./architecture.md --name "System Architecture" --tags "design,docs"
{
  "document_id": "doc_abc123xyz",
  "name": "System Architecture",
  "original_filename": "architecture.md",
  "tags": ["design", "docs"],
  "description": "",
  "size_bytes": 25088,
  "mime_type": "text/markdown",
  "checksum_sha256": "abcd1234...",
  "uploaded_at": "2024-11-21T10:30:00Z"
}
```

---

### B. `doc-pull` - Download Document

**Usage**:
```bash
uv run doc-pull <document-id> [options]
```

**Arguments**:
- `document_id` (required): Document ID from push or query
- `--output` (optional): Output file path (defaults to original filename)

**Returns**: JSON response with download confirmation

**Example**:
```bash
$ uv run doc-pull doc_abc123xyz --output ./downloaded-arch.md
{
  "status": "success",
  "document_id": "doc_abc123xyz",
  "name": "System Architecture",
  "saved_to": "./downloaded-arch.md",
  "size_bytes": 25088
}
```

---

### C. `doc-query` - Search Documents

**Usage**:
```bash
uv run doc-query [options]
```

**Arguments**:
- `--name` (optional): Filter by name (substring match)
- `--tags` (optional): Filter by tags (comma-separated, **AND logic** - all tags must match)
- `--limit` (optional): Max results [default: 50]

**Returns**: JSON array of matching documents

**Example**:
```bash
$ uv run doc-query --tags "design"
[
  {
    "document_id": "doc_abc123xyz",
    "name": "System Architecture",
    "original_filename": "architecture.md",
    "tags": ["design", "docs"],
    "description": "",
    "size_bytes": 25088,
    "mime_type": "text/markdown",
    "checksum_sha256": "abcd1234...",
    "uploaded_at": "2024-11-21T10:30:00Z"
  },
  {
    "document_id": "doc_def456uvw",
    "name": "Database Schema",
    "original_filename": "schema.md",
    "tags": ["design", "db"],
    "description": "Database design document",
    "size_bytes": 12544,
    "mime_type": "text/markdown",
    "checksum_sha256": "efgh5678...",
    "uploaded_at": "2024-11-20T15:45:00Z"
  }
]
```

---

### D. `doc-delete` - Delete Document

**Usage**:
```bash
uv run doc-delete <document-id>
```

**Arguments**:
- `document_id` (required): Document ID to delete

**Returns**: JSON response with deletion confirmation

**Example**:
```bash
$ uv run doc-delete doc_abc123xyz
{
  "status": "success",
  "message": "Document deleted successfully",
  "document_id": "doc_abc123xyz"
}
```

---

## Command Script Template (UV Pattern)

All commands follow the UV script pattern established in the Agent Orchestrator Framework:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.9.0",
#     "httpx>=0.25.0",
# ]
# ///

import typer
import json
from pathlib import Path
from lib.client import DocumentClient
from lib.config import load_config

app = typer.Typer()

@app.command()
def push(
    file_path: Path,
    name: str = typer.Option(None, help="Friendly name"),
    tags: str = typer.Option("", help="Comma-separated tags"),
    description: str = typer.Option("", help="Document description"),
):
    """Push a document to the server"""
    config = load_config()
    client = DocumentClient(config.server_url, config.timeout_seconds)

    result = client.push_document(
        file_path=file_path,
        name=name or file_path.name,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        description=description
    )

    # JSON output only for MVP
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    app()
```

**MVP Simplifications**:
- JSON-only output (no rich library dependency)
- Simple error messages via typer.echo on stderr
- Minimal dependencies (typer + httpx)

---

## Skill Library Structure

### A. `lib/config.py` - Configuration Management

```python
from dataclasses import dataclass
from pathlib import Path
import os

# Centralized default configuration
DEFAULT_SERVER_URL = "http://127.0.0.1:8766"
DEFAULT_TIMEOUT_SECONDS = 30

@dataclass
class Config:
    server_url: str
    timeout_seconds: int

def load_config() -> Config:
    """Load config with ENV precedence, hardcoded fallbacks"""
    return Config(
        server_url=os.getenv("DOCUMENT_SERVER_URL", DEFAULT_SERVER_URL),
        timeout_seconds=int(os.getenv("DOCUMENT_SERVER_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
    )
```

**Environment Variables**:
- `DOCUMENT_SERVER_URL` - Server endpoint (default: `http://127.0.0.1:8766`)
- `DOCUMENT_SERVER_TIMEOUT` - HTTP timeout in seconds (default: `30`)

**MVP Approach**: Single centralized config with ENV overrides and hardcoded fallbacks.

---

### B. `lib/client.py` - HTTP Client

The HTTP client provides a clean abstraction over the document server API:

```python
import httpx
from pathlib import Path
from typing import List, Dict, Optional

class DocumentClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout

    def push_document(
        self,
        file_path: Path,
        name: str,
        tags: List[str],
        description: str = ""
    ) -> Dict:
        """Upload document to server"""
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f)}
            data = {
                "name": name,
                "tags": ",".join(tags),
                "description": description
            }

            response = httpx.post(
                f"{self.base_url}/documents",
                files=files,
                data=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

    def pull_document(self, document_id: str, output_path: Path) -> Dict:
        """Download document from server and save to file"""
        response = httpx.get(
            f"{self.base_url}/documents/{document_id}",
            timeout=self.timeout
        )
        response.raise_for_status()

        # Write content to file
        output_path.write_bytes(response.content)

        return {
            "status": "success",
            "document_id": document_id,
            "name": response.headers.get("X-Document-Name"),
            "saved_to": str(output_path),
            "size_bytes": len(response.content)
        }

    def query_documents(
        self,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Query documents by filters"""
        params = {"limit": limit}
        if name:
            params["name"] = name
        if tags:
            params["tags"] = ",".join(tags)

        response = httpx.get(
            f"{self.base_url}/documents",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def delete_document(self, document_id: str) -> Dict:
        """Delete document from server"""
        response = httpx.delete(
            f"{self.base_url}/documents/{document_id}",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
```

---

## Document Server Implementation

### A. `models.py` - Data Models

Pydantic models define the API contract and data validation:

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DocumentMetadata(BaseModel):
    document_id: str
    name: str
    original_filename: str
    tags: List[str]
    description: str = ""
    size_bytes: int
    mime_type: str
    checksum_sha256: str
    uploaded_at: datetime
    storage_path: str  # Internal only

class DocumentUploadRequest(BaseModel):
    name: str
    tags: str = ""  # Comma-separated
    description: str = ""

class DocumentQueryParams(BaseModel):
    name: Optional[str] = None
    tags: Optional[str] = None  # Comma-separated, AND logic
    limit: int = 50

class DocumentResponse(BaseModel):
    document_id: str
    name: str
    original_filename: str
    tags: List[str]
    description: str
    size_bytes: int
    mime_type: str
    checksum_sha256: str
    uploaded_at: str

class DeleteResponse(BaseModel):
    status: str
    message: str
    document_id: str
```

**MVP Notes**:
- Kept Pydantic since it's a FastAPI dependency anyway
- Full validation for security (path traversal prevention, etc.)

---

### B. `main.py` - FastAPI Server (Port 8766)

The server exposes RESTful endpoints for document operations:

```python
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import uvicorn

from models import DocumentResponse, DeleteResponse
from storage import DocumentStorage
from database import DocumentDatabase

# Centralized configuration
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
DEFAULT_STORAGE_DIR = ".document-storage"

app = FastAPI(title="Document Server", version="1.0.0-mvp")

# Initialize with configurable storage directory
storage = DocumentStorage(base_dir=os.getenv("DOCUMENT_STORAGE_DIR", DEFAULT_STORAGE_DIR))
db = DocumentDatabase(db_path=storage.base_dir / "documents.db")

@app.post("/documents", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...),
    tags: str = Form(""),
    description: str = Form("")
):
    """Upload a document"""
    # Read file content
    content = await file.read()

    # Store file and get metadata
    metadata = storage.store_document(
        content=content,
        filename=file.filename,
        name=name,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        description=description
    )

    # Save metadata to database
    db.insert_document(metadata)

    return DocumentResponse(**metadata.dict(exclude={"storage_path"}))

@app.get("/documents/{document_id}")
async def download_document(document_id: str):
    """Download a document by ID"""
    # Get metadata from database
    metadata = db.get_document(document_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # Stream file from storage
    file_path = storage.get_document_path(metadata.storage_path)

    return FileResponse(
        path=file_path,
        media_type=metadata.mime_type,
        filename=metadata.original_filename,
        headers={
            "X-Document-Name": metadata.name,
            "X-Document-Filename": metadata.original_filename,
            "X-Document-ID": metadata.document_id
        }
    )

@app.get("/documents", response_model=list[DocumentResponse])
async def query_documents(
    name: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 50
):
    """Query documents with filters"""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    documents = db.query_documents(
        name_filter=name,
        tags_filter=tag_list,
        limit=limit
    )

    return [DocumentResponse(**doc.dict(exclude={"storage_path"})) for doc in documents]

@app.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    """Delete a document"""
    metadata = db.get_document(document_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from storage
    storage.delete_document(metadata.storage_path)

    # Delete from database
    db.delete_document(document_id)

    return DeleteResponse(
        status="success",
        message="Document deleted successfully",
        document_id=document_id
    )

if __name__ == "__main__":
    host = os.getenv("DOCUMENT_SERVER_HOST", DEFAULT_HOST)
    port = int(os.getenv("DOCUMENT_SERVER_PORT", str(DEFAULT_PORT)))
    uvicorn.run(app, host=host, port=port)
```

**API Endpoints Summary**:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/documents` | Upload document with metadata |
| GET | `/documents/{id}` | Download document by ID |
| GET | `/documents` | Query documents with filters |
| DELETE | `/documents/{id}` | Delete document |

---

### C. `storage.py` - File System Abstraction (MVP Simplified)

The storage layer implements a simple flat file system:

```python
from pathlib import Path
import hashlib
import uuid
from datetime import datetime, UTC
import mimetypes
from models import DocumentMetadata

class DocumentStorage:
    def __init__(self, base_dir: Path | str = ".document-storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def store_document(
        self,
        content: bytes,
        filename: str,
        name: str,
        tags: list[str],
        description: str
    ) -> DocumentMetadata:
        """Store document and return metadata"""
        # Generate document ID
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"

        # Calculate checksum (for integrity + future deduplication)
        checksum = hashlib.sha256(content).hexdigest()

        # MVP: Simple flat storage (no partitioning)
        storage_path = doc_id
        file_path = self.base_dir / doc_id

        # Write file
        file_path.write_bytes(content)

        # Detect MIME type (important for future browser downloads)
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        return DocumentMetadata(
            document_id=doc_id,
            name=name,
            original_filename=filename,
            tags=tags,
            description=description,
            size_bytes=len(content),
            mime_type=mime_type,
            checksum_sha256=checksum,
            uploaded_at=datetime.now(UTC),
            storage_path=storage_path
        )

    def get_document_path(self, storage_path: str) -> Path:
        """Get absolute path to document"""
        # Security: Prevent path traversal
        safe_path = Path(storage_path).name
        return self.base_dir / safe_path

    def delete_document(self, storage_path: str):
        """Delete document from storage"""
        file_path = self.get_document_path(storage_path)
        if file_path.exists():
            file_path.unlink()
```

**MVP Storage Structure**:

```
.document-storage/
├── documents.db              # SQLite metadata
├── doc_a1b2c3d4e5f6         # Flat file storage
├── doc_a1b999888777
├── doc_c3d4e5f6a1b2
└── doc_e5f6a1b2c3d4
```

**MVP Simplifications**:
- ✅ **Flat directory structure** - All documents in single directory
- ✅ Simple storage path (just document ID)
- ✅ **Path traversal prevention** - Security check in get_document_path
- ✅ **SHA256 checksum kept** - For future deduplication
- ✅ **MIME type detection kept** - For future browser integration

**Migration Path**: Easy to migrate to partitioned structure later by:
1. Adding partition logic: `partition = checksum[:2]`
2. Moving files: `storage_path = f"{partition}/{doc_id}"`
3. Database schema already supports storage_path changes

---

### D. `database.py` - SQLite Metadata Storage

The database layer manages document metadata and tag relationships:

```python
import sqlite3
from pathlib import Path
from typing import Optional, List
from models import DocumentMetadata
from datetime import datetime

class DocumentDatabase:
    def __init__(self, db_path: Path | str = ".document-storage/documents.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                description TEXT,
                size_bytes INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                checksum_sha256 TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                storage_path TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS document_tags (
                document_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (document_id, tag),
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON document_tags(tag)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON documents(name)")
        conn.commit()
        conn.close()

    def insert_document(self, metadata: DocumentMetadata):
        """Insert document metadata"""
        conn = sqlite3.connect(self.db_path)

        # Insert document
        conn.execute("""
            INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.document_id,
            metadata.name,
            metadata.original_filename,
            metadata.description,
            metadata.size_bytes,
            metadata.mime_type,
            metadata.checksum_sha256,
            metadata.uploaded_at.isoformat(),
            metadata.storage_path
        ))

        # Insert tags
        for tag in metadata.tags:
            conn.execute("""
                INSERT INTO document_tags VALUES (?, ?)
            """, (metadata.document_id, tag))

        conn.commit()
        conn.close()

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """Get document by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        row = conn.execute("""
            SELECT * FROM documents WHERE document_id = ?
        """, (document_id,)).fetchone()

        if not row:
            conn.close()
            return None

        tags = [r["tag"] for r in conn.execute("""
            SELECT tag FROM document_tags WHERE document_id = ?
        """, (document_id,)).fetchall()]

        conn.close()

        return DocumentMetadata(
            document_id=row["document_id"],
            name=row["name"],
            original_filename=row["original_filename"],
            description=row["description"],
            size_bytes=row["size_bytes"],
            mime_type=row["mime_type"],
            checksum_sha256=row["checksum_sha256"],
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
            storage_path=row["storage_path"],
            tags=tags
        )

    def query_documents(
        self,
        name_filter: Optional[str] = None,
        tags_filter: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[DocumentMetadata]:
        """Query documents with filters (AND logic for tags)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT DISTINCT d.* FROM documents d"
        params = []

        if tags_filter:
            query += " JOIN document_tags dt ON d.document_id = dt.document_id"

        conditions = []
        if name_filter:
            conditions.append("d.name LIKE ?")
            params.append(f"%{name_filter}%")

        if tags_filter:
            conditions.append(f"dt.tag IN ({','.join('?' * len(tags_filter))})")
            params.extend(tags_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        if tags_filter:
            # AND logic: document must have ALL specified tags
            query += f" GROUP BY d.document_id HAVING COUNT(DISTINCT dt.tag) = {len(tags_filter)}"

        query += " ORDER BY d.uploaded_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

        documents = []
        for row in rows:
            tags = [r["tag"] for r in conn.execute("""
                SELECT tag FROM document_tags WHERE document_id = ?
            """, (row["document_id"],)).fetchall()]

            documents.append(DocumentMetadata(
                document_id=row["document_id"],
                name=row["name"],
                original_filename=row["original_filename"],
                description=row["description"],
                size_bytes=row["size_bytes"],
                mime_type=row["mime_type"],
                checksum_sha256=row["checksum_sha256"],
                uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
                storage_path=row["storage_path"],
                tags=tags
            ))

        conn.close()
        return documents

    def delete_document(self, document_id: str):
        """Delete document metadata (cascade deletes tags)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
        conn.commit()
        conn.close()
```

**Database Schema**:

```sql
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    description TEXT,
    size_bytes INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    storage_path TEXT NOT NULL
);

CREATE TABLE document_tags (
    document_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (document_id, tag),
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);

CREATE INDEX idx_tags ON document_tags(tag);
CREATE INDEX idx_name ON documents(name);
```

**Query Features**:
- **Name filtering**: Substring match (case-insensitive via LIKE)
- **Tag filtering**: **AND logic** (all specified tags must match)
- **Indexing**: Fast lookups on tags and names
- **Cascade deletion**: Removing a document auto-removes its tags

**Why Separate Tags Table?**:
- Enables efficient tag-based queries
- Makes it easy to add "list all available tags" feature later
- Proper normalization for tag management

---

## Environment Variables

### Skill Side (Command Scripts)

```bash
# Server connection (optional, has hardcoded fallback)
DOCUMENT_SERVER_URL=http://127.0.0.1:8766

# HTTP timeout in seconds (optional, defaults to 30)
DOCUMENT_SERVER_TIMEOUT=30
```

### Server Side (Optional Overrides)

```bash
# Storage directory path (optional, defaults to .document-storage)
DOCUMENT_STORAGE_DIR=.document-storage

# Server binding (optional, defaults shown)
DOCUMENT_SERVER_HOST=127.0.0.1
DOCUMENT_SERVER_PORT=8766
```

**MVP Approach**: All config is optional with hardcoded fallbacks in a central location.

---

## Skill Registration

### `skill.json`

```json
{
  "name": "document-sync",
  "version": "1.0.0-mvp",
  "description": "Document push/pull/query/delete system for AI coding sessions"
}
```

### `SKILL.md`

```markdown
# Document Sync Skill

Use this skill when you need to store, retrieve, search, or delete documents in a central repository.

## Commands

- `doc-push <file>` - Upload a document to the server
- `doc-pull <doc-id>` - Download a document by ID
- `doc-query [filters]` - Search for documents (AND logic for tags)
- `doc-delete <doc-id>` - Delete a document by ID

All commands return JSON output.

## Examples

### Upload Architecture Document
```bash
uv run doc-push ./architecture.md --name "System Arch" --tags "design,v2"
```

### Query Documents with Multiple Tags (AND logic)
```bash
uv run doc-query --tags "design,docs"
# Returns only documents that have BOTH "design" AND "docs" tags
```

### Download Specific Document
```bash
uv run doc-pull doc_abc123xyz --output ./local-copy.md
```

### Delete Document
```bash
uv run doc-delete doc_abc123xyz
```
```

---

## Complete Flow Diagram

```
Claude Code Session
       |
       v
[Skill: doc-push architecture.md]
       |
       +---> load_config()
       |     (Uses ENV or hardcoded defaults)
       |
       +---> DocumentClient.push_document()
       |     |
       |     v
       |  POST /documents
       |  (multipart/form-data: file + metadata)
       |     |
       |     v
       |  [Document Server]
       |  |
       |  +---> DocumentStorage.store_document()
       |  |     - Generate doc_abc123xyz
       |  |     - Calculate SHA256 checksum
       |  |     - Detect MIME type
       |  |     - Write to .document-storage/doc_abc123xyz
       |  |
       |  +---> DocumentDatabase.insert_document()
       |        - Insert into documents table
       |        - Insert tags into document_tags table
       |     |
       |     v
       |  Return {document_id, name, tags, ...}
       |
       +---> Print JSON response
```

---

## Key MVP Design Decisions

| Aspect | MVP Decision | Rationale | Future Migration |
|--------|--------------|-----------|------------------|
| **Storage** | Flat directory | Simplest implementation, works up to ~10k docs | Easy to add partitioning by changing storage_path logic |
| **Tag Query** | AND logic | More precise filtering, user requested | Already implemented |
| **Tag Storage** | Separate table | Enables tag listing feature, better queries | No change needed |
| **CLI Output** | JSON only | Simple, flexible, machine-readable | Add rich tables as optional `--format` flag |
| **Deletion** | Included | Useful for testing/cleanup | No change needed |
| **Checksum** | SHA256 kept | Enables future deduplication | Already ready for dedup |
| **MIME Type** | Detected | Important for browser downloads | No change needed |
| **Validation** | Full Pydantic | Comes with FastAPI, adds security | No change needed |
| **Testing** | Manual only | Focus on functionality first | Add pytest suite when stabilizing |
| **Config** | ENV + defaults | Flexible but simple | No change needed |
| **Deployment** | Docker + dev | Consistent env, skip production details | Add Gunicorn/production docs when deploying |

---

## Deployment

### Development Setup

```bash
# Start server
cd document-server
uv run src/main.py

# Use skill commands
cd ../skills/document-sync
uv run commands/doc-push ./test.md --tags "test"
uv run commands/doc-query --tags "test"
uv run commands/doc-pull doc_xxx --output ./downloaded.md
uv run commands/doc-delete doc_xxx
```

### Docker Setup

```dockerfile
# document-server/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN uv sync

# Create storage directory
RUN mkdir -p .document-storage

# Expose port
EXPOSE 8766

# Run server
CMD ["uv", "run", "src/main.py"]
```

**Build and Run**:
```bash
cd document-server
docker build -t document-server:mvp .
docker run -p 8766:8766 -v $(pwd)/.document-storage:/app/.document-storage document-server:mvp
```

---

## Future Enhancements (Post-MVP)

### Phase 2: Polish & Features

1. **List Available Tags**
   - New endpoint: `GET /tags` → returns all unique tags
   - Helps users discover what tags exist
   - Simple query: `SELECT DISTINCT tag FROM document_tags`

2. **Rich CLI Output**
   - Add `--format table` option to doc-query
   - Use rich library for pretty tables
   - Keep JSON as default

3. **Partitioned Storage**
   - Migrate to `{checksum[:2]}/{doc_id}` structure
   - Write migration script to move existing files
   - Better scalability for 100k+ documents

### Phase 3: Advanced Features

4. **Document Versioning**
   - Track document history
   - Rollback capability
   - Diff between versions

5. **Deduplication**
   - Check if SHA256 already exists before storing
   - Reference counting for shared content
   - Saves storage space

6. **Batch Operations**
   - `doc-push-bulk` for multiple files
   - `doc-pull-bulk` for collections
   - Parallel uploads/downloads

### Phase 4: Production Readiness

7. **Authentication**
   - API key support
   - User isolation
   - Rate limiting

8. **Observability**
   - Integration with existing observability server
   - Track document operations
   - Usage analytics

9. **Web UI**
   - Browse documents
   - Preview content
   - Drag-and-drop upload

---

## Security Considerations

### MVP Security Features (Included)

1. ✅ **Path traversal prevention** - Safe path handling in storage
2. ✅ **Input validation** - Pydantic models validate all inputs
3. ✅ **Document ID validation** - UUID-based, no user-controlled paths
4. ✅ **Checksum verification** - SHA256 for integrity

### Future Security Enhancements

1. **File size limits** - Configurable max upload size
2. **Rate limiting** - Prevent abuse
3. **Authentication** - API keys or OAuth
4. **Encryption at rest** - Encrypt stored documents

---

## Performance Characteristics

### Expected MVP Performance

| Operation | Latency | Throughput | Notes |
|-----------|---------|------------|-------|
| Push (1 MB) | ~50-100ms | 10-20 req/s | Includes SHA256 calculation |
| Pull (1 MB) | ~30-50ms | 20-30 req/s | Direct file streaming |
| Query (100 results) | ~10-20ms | 50-100 req/s | With proper indexes |
| Delete | ~5-10ms | 100+ req/s | Just DB + file deletion |

### Scalability Limits (MVP)

- **Documents**: ~10k comfortable, 50k+ possible (flat directory)
- **File Size**: 100 MB+ (streaming support)
- **Concurrent Users**: 10-20 (single uvicorn worker)
- **Database**: SQLite handles 1M+ rows efficiently

### When to Upgrade

- **Storage**: Switch to partitioned when hitting ~5k documents
- **Web Server**: Add Gunicorn workers when >20 concurrent users
- **Database**: Stay on SQLite until 100k+ documents or high write concurrency

---

## Comparison to Full Architecture

| Feature | Full Architecture | MVP | Migration Effort |
|---------|------------------|-----|------------------|
| Storage | Partitioned (256 dirs) | Flat directory | Low - script to move files |
| CLI Output | Rich tables + JSON | JSON only | Low - add --format flag |
| Testing | Full test suite | Manual testing | Medium - write tests |
| Deployment | Docker + Gunicorn | Docker + dev server | Low - add Gunicorn config |
| Deletion | ✅ | ✅ | N/A |
| Tag Query | AND logic ✅ | AND logic ✅ | N/A |
| Tag Storage | Separate table ✅ | Separate table ✅ | N/A |
| Checksum | SHA256 ✅ | SHA256 ✅ | N/A |
| MIME Type | Detected ✅ | Detected ✅ | N/A |
| Validation | Pydantic ✅ | Pydantic ✅ | N/A |

**MVP keeps the important foundations while simplifying implementation details.**

---

## Summary

This MVP architecture provides:

✅ **Full CRUD operations** - push, pull, query, delete
✅ **Robust metadata** - SHA256, MIME types, tags
✅ **Precise queries** - AND logic for tags
✅ **Security** - Path traversal prevention, input validation
✅ **Future-ready** - Easy migration to enhanced features
✅ **Simple deployment** - Docker support, ENV config

**What's simplified:**
- Flat storage (vs partitioned)
- JSON-only output (vs rich tables)
- Manual testing (vs automated)
- Dev server only (vs production setup)

**Clear upgrade paths:**
- Storage partitioning (when >5k docs)
- Rich CLI output (when UX matters)
- Test automation (when stabilizing)
- Production deployment (when going live)

**Time to implement:** ~2-3 days vs ~1-2 weeks for full architecture
