# Document Sync Plugin - Architecture Draft

## Introduction

The **Document Sync Plugin** is a document management system designed for AI coding sessions, following the architectural patterns established in the Agent Orchestrator Framework. It provides a simple, yet powerful interface for storing, retrieving, and querying documents through a client-skill architecture that mirrors the `agent-orchestrator` → `observability-server` pattern.

This system consists of two primary components:

1. **Document Sync Skill** - UV-based Python command-line tools that Claude Code can invoke to interact with documents
2. **Document Server** - A standalone FastAPI server that manages document storage, metadata, and retrieval

The architecture prioritizes simplicity, scalability, and consistency with existing patterns in the Agent Orchestrator Framework.

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
│           └── lib/
│               ├── __init__.py
│               ├── config.py        # Configuration management
│               ├── client.py        # HTTP client to document server
│               └── document.py      # Document metadata handling
│
└── document-server/                 # Standalone document storage server
    ├── pyproject.toml
    ├── uv.lock
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

**Returns**: Document ID (UUID) assigned by server

**Example**:
```bash
$ uv run doc-push ./architecture.md --name "System Architecture" --tags "design,docs"
Document pushed successfully!
Document ID: doc_abc123xyz
Name: System Architecture
Tags: design, docs
URL: http://localhost:8766/documents/doc_abc123xyz
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
- `--overwrite` (optional): Overwrite if file exists

**Returns**: Downloads file to local filesystem

**Example**:
```bash
$ uv run doc-pull doc_abc123xyz --output ./downloaded-arch.md
Downloaded: System Architecture
Saved to: ./downloaded-arch.md
Size: 24.5 KB
```

---

### C. `doc-query` - Search Documents

**Usage**:
```bash
uv run doc-query [options]
```

**Arguments**:
- `--name` (optional): Filter by name (substring match)
- `--tags` (optional): Filter by tags (comma-separated, AND logic)
- `--format` (optional): Output format (table|json) [default: table]
- `--limit` (optional): Max results [default: 50]

**Returns**: List of matching documents with metadata

**Example**:
```bash
$ uv run doc-query --tags "design"
┌──────────────────┬──────────────────────────┬────────────┬─────────────────────┐
│ Document ID      │ Name                     │ Tags       │ Uploaded            │
├──────────────────┼──────────────────────────┼────────────┼─────────────────────┤
│ doc_abc123xyz    │ System Architecture      │ design,docs│ 2024-11-21 10:30:00 │
│ doc_def456uvw    │ Database Schema          │ design,db  │ 2024-11-20 15:45:00 │
└──────────────────┴──────────────────────────┴────────────┴─────────────────────┘

$ uv run doc-query --name "arch" --format json
[
  {
    "document_id": "doc_abc123xyz",
    "name": "System Architecture",
    "tags": ["design", "docs"],
    "size_bytes": 25088,
    "uploaded_at": "2024-11-21T10:30:00Z",
    "checksum": "sha256:abcd..."
  }
]
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
#     "rich>=13.0.0",  # For pretty tables
# ]
# ///

import typer
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
    client = DocumentClient(config.server_url)

    result = client.push_document(
        file_path=file_path,
        name=name or file_path.name,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        description=description
    )

    typer.echo(f"Document pushed successfully!")
    typer.echo(f"Document ID: {result['document_id']}")
    typer.echo(f"Name: {result['name']}")

if __name__ == "__main__":
    app()
```

---

## Skill Library Structure

### A. `lib/config.py` - Configuration Management

```python
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class Config:
    server_url: str
    timeout_seconds: int

def load_config() -> Config:
    """Load config with ENV precedence"""
    return Config(
        server_url=os.getenv(
            "DOCUMENT_SERVER_URL",
            "http://127.0.0.1:8766"
        ),
        timeout_seconds=int(os.getenv(
            "DOCUMENT_SERVER_TIMEOUT",
            "30"
        ))
    )
```

**Environment Variables**:
- `DOCUMENT_SERVER_URL` - Server endpoint (default: `http://127.0.0.1:8766`)
- `DOCUMENT_SERVER_TIMEOUT` - HTTP timeout in seconds (default: `30`)

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

    def pull_document(self, document_id: str) -> tuple[bytes, Dict]:
        """Download document from server"""
        response = httpx.get(
            f"{self.base_url}/documents/{document_id}",
            timeout=self.timeout
        )
        response.raise_for_status()

        metadata = {
            "filename": response.headers.get("X-Document-Filename"),
            "name": response.headers.get("X-Document-Name"),
            "size": int(response.headers.get("Content-Length", 0))
        }

        return response.content, metadata

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
    description: Optional[str] = ""
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
```

---

### B. `main.py` - FastAPI Server (Port 8766)

The server exposes RESTful endpoints for document operations:

```python
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional
import uvicorn

from models import DocumentResponse, DocumentQueryParams
from storage import DocumentStorage
from database import DocumentDatabase

app = FastAPI(title="Document Server", version="1.0.0")

storage = DocumentStorage()
db = DocumentDatabase()

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

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    metadata = db.get_document(document_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from storage
    storage.delete_document(metadata.storage_path)

    # Delete from database
    db.delete_document(document_id)

    return {"message": "Document deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8766)
```

**API Endpoints Summary**:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/documents` | Upload document with metadata |
| GET | `/documents/{id}` | Download document by ID |
| GET | `/documents` | Query documents with filters |
| DELETE | `/documents/{id}` | Delete document |

---

### C. `storage.py` - File System Abstraction

The storage layer implements a content-addressed, partitioned file system:

```python
from pathlib import Path
import hashlib
import uuid
from datetime import datetime, UTC
import mimetypes
from models import DocumentMetadata

class DocumentStorage:
    def __init__(self, base_dir: Path = Path(".document-storage")):
        self.base_dir = base_dir
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

        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Determine storage path (content-addressed + partitioning)
        partition = checksum[:2]  # First 2 chars for partitioning
        storage_path = f"{partition}/{doc_id}"

        # Create partition directory
        partition_dir = self.base_dir / partition
        partition_dir.mkdir(exist_ok=True)

        # Write file
        file_path = partition_dir / doc_id
        file_path.write_bytes(content)

        # Detect MIME type
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
        return self.base_dir / storage_path

    def delete_document(self, storage_path: str):
        """Delete document from storage"""
        file_path = self.get_document_path(storage_path)
        if file_path.exists():
            file_path.unlink()
```

**Storage Structure**:

```
.document-storage/
├── documents.db                     # SQLite metadata
├── ab/                              # Partition by first 2 chars of SHA256
│   ├── doc_a1b2c3d4e5f6            # Actual file content
│   └── doc_a1b999888777
├── cd/
│   └── doc_c3d4e5f6a1b2
└── ef/
    └── doc_e5f6a1b2c3d4
```

**Benefits**:
- Content-addressed for integrity verification
- Partitioned directories prevent single directory from containing 10k+ files
- Simple flat structure within partitions
- Original filename preserved in metadata
- Future-ready for deduplication (same SHA256 = same content)

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
    def __init__(self, db_path: Path = Path(".document-storage/documents.db")):
        self.db_path = db_path
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
        """Query documents with filters"""
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
            # Ensure ALL tags match (AND logic)
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
        """Delete document metadata"""
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
- **Tag filtering**: AND logic (all tags must match)
- **Indexing**: Fast lookups on tags and names
- **Cascade deletion**: Removing a document auto-removes its tags

---

## Environment Variables

### Skill Side (Command Scripts)

```bash
# Server connection
DOCUMENT_SERVER_URL=http://127.0.0.1:8766

# HTTP timeout (seconds)
DOCUMENT_SERVER_TIMEOUT=30
```

### Server Side (Optional Overrides)

```bash
# Storage directory path
DOCUMENT_STORAGE_DIR=.document-storage

# Server binding
DOCUMENT_SERVER_HOST=127.0.0.1
DOCUMENT_SERVER_PORT=8766
```

---

## Skill Registration

### `skill.json`

```json
{
  "name": "document-sync",
  "version": "1.0.0",
  "description": "Document push/pull/query system for AI coding sessions"
}
```

### `SKILL.md`

```markdown
# Document Sync Skill

Use this skill when you need to store, retrieve, or search documents in a central repository.

## Commands

- `doc-push <file>` - Upload a document to the server
- `doc-pull <doc-id>` - Download a document by ID
- `doc-query [filters]` - Search for documents

## Examples

### Upload Architecture Document
```bash
uv run doc-push ./architecture.md --tags "design,v2"
```

### Query Design Documents
```bash
uv run doc-query --tags "design"
```

### Download Specific Document
```bash
uv run doc-pull doc_abc123xyz --output ./local-copy.md
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
       |     (DOCUMENT_SERVER_URL from ENV)
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
       |  |     - Write to .document-storage/ab/doc_abc123xyz
       |  |
       |  +---> DocumentDatabase.insert_document()
       |        - Insert into documents table
       |        - Insert tags into document_tags table
       |     |
       |     v
       |  Return {document_id, name, tags, ...}
       |
       +---> Print success message with document_id
```

---

## Key Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Document ID** | `doc_{12-char-hex}` | Short, unique, URL-safe identifier |
| **Storage** | Content-addressed + partitioned | Scalable to millions of documents, enables future deduplication |
| **Tags** | AND logic in queries | More precise filtering (document must have ALL specified tags) |
| **Metadata** | SQLite + JSON responses | Fast queries, relational integrity, web-friendly API |
| **Server Port** | 8766 | Avoids conflict with observability server (8765) |
| **File Upload** | Multipart form-data | Standard HTTP pattern, supports binary + metadata |
| **Download** | Streaming response | Memory-efficient for large files |
| **Error Handling** | HTTP exceptions | Standard REST semantics (404, 400, 500) |
| **Checksum** | SHA256 | Industry-standard integrity verification |
| **Partitioning** | First 2 chars of SHA256 | Balanced distribution across 256 directories |

---

## Comparison to Observability Pattern

| Feature | Observability | Document Sync |
|---------|---------------|---------------|
| **Skill Commands** | `ao-new`, `ao-resume`, `ao-status` | `doc-push`, `doc-pull`, `doc-query` |
| **Server Port** | 8765 | 8766 |
| **Protocol** | HTTP POST events | HTTP multipart upload/download |
| **Storage** | SQLite events + JSONL files | SQLite metadata + content-addressed filesystem |
| **Real-time** | WebSocket broadcasting | Not needed (stateless operations) |
| **Hook Integration** | Pre/post tool hooks | Not needed |
| **CLI Framework** | Typer | Typer |
| **HTTP Client** | httpx | httpx |
| **UV Scripts** | ✅ | ✅ |
| **Async Support** | AsyncIO hooks | Sync operations (simpler) |

---

## Implementation Phases

### Phase 1: Minimal Viable Product (MVP)
- Basic push/pull/query commands
- Simple file storage (no partitioning initially)
- SQLite metadata storage
- Core API endpoints

### Phase 2: Enhanced Features
- Partitioned storage system
- Content-addressed storage
- Rich CLI output (tables, colors)
- Comprehensive error handling

### Phase 3: Advanced Features
- Deduplication based on SHA256
- Compression support
- Batch operations (push/pull multiple documents)
- Document versioning
- Access control / authentication

### Phase 4: Integration & Optimization
- WebSocket support for real-time updates (optional)
- Frontend dashboard (similar to observability)
- Performance optimization for large files
- Caching layer

---

## Security Considerations

1. **Input Validation**
   - Validate document IDs (prevent path traversal)
   - Sanitize filenames
   - Limit file sizes (configurable max size)

2. **Storage Isolation**
   - Documents stored outside web-accessible directories
   - Use storage_path abstraction to prevent direct access

3. **Future Enhancements**
   - API key authentication
   - Rate limiting
   - User isolation (multi-tenancy)
   - Encryption at rest

---

## Performance Characteristics

### Expected Performance

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Push (1 MB file) | ~50-100ms | 10-20 req/s |
| Pull (1 MB file) | ~30-50ms | 20-30 req/s |
| Query (100 results) | ~10-20ms | 50-100 req/s |

### Scalability Limits

- **Documents**: 1M+ documents (with partitioning)
- **File Size**: 100 MB+ per file (streaming support)
- **Concurrent Users**: 10-50 (single uvicorn worker)
- **Database**: SQLite handles 1M+ rows efficiently

### Optimization Strategies

1. **Caching**: Add Redis for frequently accessed metadata
2. **CDN**: Serve static documents via CDN for global distribution
3. **Async Workers**: Use Celery for background processing
4. **Horizontal Scaling**: Load balance multiple server instances

---

## Testing Strategy

### Unit Tests
- `test_storage.py` - File operations, partitioning, checksums
- `test_database.py` - CRUD operations, query logic
- `test_client.py` - HTTP client methods
- `test_models.py` - Pydantic validation

### Integration Tests
- `test_api.py` - End-to-end API workflows
- `test_commands.py` - CLI command execution

### Load Tests
- Concurrent push operations
- Large file uploads (100 MB+)
- Query performance with 10k+ documents

---

## Deployment

### Development
```bash
# Start server
cd document-server
uv run src/main.py

# Use skill commands
cd ../skills/document-sync
uv run commands/doc-push ./test.md
```

### Production
```bash
# Run with uvicorn + gunicorn
gunicorn -k uvicorn.workers.UvicornWorker \
  -w 4 \
  -b 0.0.0.0:8766 \
  src.main:app
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv
RUN uv sync
CMD ["uv", "run", "src/main.py"]
```

---

## Future Enhancements

1. **Document Versioning**
   - Track document history
   - Rollback to previous versions
   - Diff between versions

2. **Advanced Search**
   - Full-text search (SQLite FTS5)
   - Fuzzy matching
   - Date range filtering

3. **Collaboration Features**
   - Shared collections
   - Access permissions
   - Audit logs

4. **Integration**
   - Git integration (auto-push on commit)
   - S3 backend support
   - Webhook notifications

5. **Analytics**
   - Usage statistics
   - Popular documents
   - Storage trends