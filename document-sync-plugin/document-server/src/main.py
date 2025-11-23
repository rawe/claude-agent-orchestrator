from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
from datetime import datetime
import uvicorn
import os
import json

from .models import DocumentMetadata, DocumentResponse, DocumentQueryParams, DeleteResponse
from .storage import DocumentStorage
from .database import DocumentDatabase

# Configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8766
DEFAULT_STORAGE_DIR = "./document-data/files"
DEFAULT_DB_PATH = "./document-data/documents.db"

DOCUMENT_SERVER_HOST = os.getenv("DOCUMENT_SERVER_HOST", DEFAULT_HOST)
DOCUMENT_SERVER_PORT = int(os.getenv("DOCUMENT_SERVER_PORT", str(DEFAULT_PORT)))
STORAGE_DIR = os.getenv("DOCUMENT_SERVER_STORAGE", DEFAULT_STORAGE_DIR)
DB_PATH = os.getenv("DOCUMENT_SERVER_DB", DEFAULT_DB_PATH)

# Initialize storage and database
storage = DocumentStorage(STORAGE_DIR)
db = DocumentDatabase(DB_PATH)

# FastAPI app instance
app = FastAPI(
    title="Document Sync Server",
    version="0.1.0",
    description="FastAPI server for document management and synchronization"
)


@app.get("/health")
async def health_check():
    """Health check endpoint for container monitoring."""
    return {"status": "healthy", "service": "document-sync-server"}


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

    # Read file content
    content = await file.read()

    # Store document and get metadata
    doc_metadata = storage.store_document(content, file.filename or "unknown")

    # Add tags to metadata
    doc_metadata.tags = parsed_tags
    doc_metadata.metadata = parsed_metadata

    # Insert into database
    db.insert_document(doc_metadata)

    # Return response
    response = DocumentResponse(
        id=doc_metadata.id,
        filename=doc_metadata.filename,
        content_type=doc_metadata.content_type,
        size_bytes=doc_metadata.size_bytes,
        created_at=doc_metadata.created_at,
        updated_at=doc_metadata.updated_at,
        tags=doc_metadata.tags,
        metadata=doc_metadata.metadata
    )

    return JSONResponse(status_code=201, content=response.model_dump(mode="json"))


@app.get("/documents/{document_id}/metadata", response_model=DocumentResponse)
async def get_document_metadata(document_id: str):
    """Retrieve metadata for a specific document by ID."""
    # Get metadata from database
    doc_metadata = db.get_document(document_id)

    if not doc_metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # Return metadata response
    response = DocumentResponse(
        id=doc_metadata.id,
        filename=doc_metadata.filename,
        content_type=doc_metadata.content_type,
        size_bytes=doc_metadata.size_bytes,
        created_at=doc_metadata.created_at,
        updated_at=doc_metadata.updated_at,
        tags=doc_metadata.tags,
        metadata=doc_metadata.metadata
    )

    return response


@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Retrieve a specific document by ID and stream the file."""
    # Get metadata from database
    doc_metadata = db.get_document(document_id)

    if not doc_metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get file path from storage
    try:
        file_path = storage.get_document_path(document_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Return file as response
    return FileResponse(
        path=file_path,
        media_type=doc_metadata.content_type,
        filename=doc_metadata.filename
    )


@app.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    filename: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0)
):
    """List all documents with optional filtering by filename and/or tags."""
    # Parse tags if provided
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else None

    # Query database
    documents = db.query_documents(filename=filename, tags=parsed_tags)

    # Convert to response model
    responses = [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            size_bytes=doc.size_bytes,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            tags=doc.tags,
            metadata=doc.metadata
        )
        for doc in documents
    ]

    # Apply pagination (simple slicing)
    return responses[offset:offset + limit]


@app.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    """Delete a document by ID from both storage and database."""
    # Delete from database first
    db_deleted = db.delete_document(document_id)

    if not db_deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from storage
    storage_deleted = storage.delete_document(document_id)

    return DeleteResponse(
        success=True,
        message=f"Document {document_id} deleted successfully",
        document_id=document_id
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=DOCUMENT_SERVER_HOST,
        port=DOCUMENT_SERVER_PORT,
        reload=True
    )
