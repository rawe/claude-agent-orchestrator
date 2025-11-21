from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime
import uvicorn
import os
import json

from .models import DocumentMetadata, DocumentResponse, DocumentQueryParams, DeleteResponse

# Configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8766
DEFAULT_STORAGE_DIR = "./storage"

DOCUMENT_SERVER_HOST = os.getenv("DOCUMENT_SERVER_HOST", DEFAULT_HOST)
DOCUMENT_SERVER_PORT = int(os.getenv("DOCUMENT_SERVER_PORT", str(DEFAULT_PORT)))
DOCUMENT_SERVER_STORAGE = os.getenv("DOCUMENT_SERVER_STORAGE", DEFAULT_STORAGE_DIR)

# FastAPI app instance
app = FastAPI(
    title="Document Sync Server",
    version="0.1.0",
    description="FastAPI server for document management and synchronization"
)


@app.post("/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None)
):
    """Upload a new document with optional tags and metadata."""
    # Parse tags from comma-separated string
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else []

    # Parse metadata from JSON string
    parsed_metadata = {}
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in metadata parameter")

    # Create stub response
    response = DocumentResponse(
        id="doc_stub_123",
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=parsed_tags,
        metadata=parsed_metadata
    )

    return JSONResponse(status_code=201, content=response.model_dump(mode="json"))


@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Retrieve a specific document by ID."""
    raise HTTPException(status_code=501, detail="Document retrieval not yet implemented")


@app.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    tags: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0)
):
    """List all documents with optional filtering."""
    # Parse tags if provided
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else None

    # Stub: Will query database in Block 02
    return []


@app.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    """Delete a document by ID."""
    return DeleteResponse(
        success=True,
        message="Document deletion stub (not yet implemented)",
        document_id=document_id
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=DOCUMENT_SERVER_HOST,
        port=DOCUMENT_SERVER_PORT,
        reload=True
    )
