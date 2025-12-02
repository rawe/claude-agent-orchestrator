from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import uvicorn
import os
import json

from .models import (
    DocumentMetadata, DocumentResponse, DocumentQueryParams, DeleteResponse,
    SearchResponse, SearchResultItem, SectionInfo
)
from .storage import DocumentStorage
from .database import DocumentDatabase
from .semantic.config import config as semantic_config

# Configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8766
DEFAULT_STORAGE_DIR = "./document-data/files"
DEFAULT_DB_PATH = "./document-data/documents.db"

DOCUMENT_SERVER_HOST = os.getenv("DOCUMENT_SERVER_HOST", DEFAULT_HOST)
DOCUMENT_SERVER_PORT = int(os.getenv("DOCUMENT_SERVER_PORT", str(DEFAULT_PORT)))
STORAGE_DIR = os.getenv("DOCUMENT_SERVER_STORAGE", DEFAULT_STORAGE_DIR)
DB_PATH = os.getenv("DOCUMENT_SERVER_DB", DEFAULT_DB_PATH)

# Public URL configuration for generating document URLs
# This should be the externally accessible URL (important for Docker/proxy setups)
# Examples: "http://localhost:8766", "https://api.example.com", "http://192.168.1.100:9000"
DOCUMENT_SERVER_PUBLIC_URL = os.getenv(
    "DOCUMENT_SERVER_PUBLIC_URL",
    f"http://localhost:{DOCUMENT_SERVER_PORT}"  # Fallback to localhost with configured port
)

# Initialize storage and database
storage = DocumentStorage(STORAGE_DIR)
db = DocumentDatabase(DB_PATH)

# CORS configuration - allow frontend origins
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# FastAPI app instance
app = FastAPI(
    title="Context Store",
    version="0.1.0",
    description="FastAPI server for document management and synchronization"
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_document_url(document_id: str) -> str:
    """
    Construct the full URL for retrieving a document.

    Uses DOCUMENT_SERVER_PUBLIC_URL as the base, which can be configured
    to handle Docker port mapping, reverse proxies, or custom domains.

    Args:
        document_id: The unique document identifier

    Returns:
        Fully qualified URL (e.g., "http://localhost:8766/documents/doc_123")
    """
    # Remove trailing slash if present to avoid double slashes
    base_url = DOCUMENT_SERVER_PUBLIC_URL.rstrip('/')
    return f"{base_url}/documents/{document_id}"


@app.get("/health")
async def health_check():
    """Health check endpoint for container monitoring."""
    return {"status": "healthy", "service": "context-store"}


@app.get("/search", response_model=SearchResponse)
async def search_documents_endpoint(
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(10, description="Maximum documents to return", ge=1, le=100)
):
    """
    Semantic search across indexed documents.

    Only available when SEMANTIC_SEARCH_ENABLED=true.
    Returns documents ranked by semantic similarity to the query.
    """
    if not semantic_config.enabled:
        raise HTTPException(
            status_code=404,
            detail="Semantic search is not enabled"
        )

    from .semantic.search import search_documents

    # Perform semantic search
    results = search_documents(q, limit=limit)

    # Enrich results with document metadata
    enriched_results = []
    for result in results:
        doc_metadata = db.get_document(result["document_id"])
        if doc_metadata:
            enriched_results.append(
                SearchResultItem(
                    document_id=result["document_id"],
                    filename=doc_metadata.filename,
                    document_url=get_document_url(result["document_id"]),
                    sections=[SectionInfo(**s) for s in result["sections"]]
                )
            )

    return SearchResponse(query=q, results=enriched_results)


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

    # Store document and get metadata (use client's MIME type if provided)
    doc_metadata = storage.store_document(
        content,
        file.filename or "unknown",
        content_type=file.content_type
    )

    # Add tags to metadata
    doc_metadata.tags = parsed_tags
    doc_metadata.metadata = parsed_metadata

    # Insert into database
    db.insert_document(doc_metadata)

    # Index for semantic search if enabled (only for text content)
    if semantic_config.enabled and doc_metadata.content_type.startswith("text/"):
        from .semantic.indexer import index_document
        text_content = content.decode("utf-8", errors="ignore")
        index_document(doc_metadata.id, text_content)

    # Return response
    response = DocumentResponse(
        id=doc_metadata.id,
        filename=doc_metadata.filename,
        content_type=doc_metadata.content_type,
        size_bytes=doc_metadata.size_bytes,
        created_at=doc_metadata.created_at,
        updated_at=doc_metadata.updated_at,
        tags=doc_metadata.tags,
        metadata=doc_metadata.metadata,
        url=get_document_url(doc_metadata.id)
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
        metadata=doc_metadata.metadata,
        url=get_document_url(doc_metadata.id)
    )

    return response


@app.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    offset: Optional[int] = Query(None, description="Starting character position (0-indexed)"),
    limit: Optional[int] = Query(None, description="Number of characters to return")
):
    """
    Retrieve a specific document by ID.

    For text content types, supports partial retrieval with offset and limit parameters.
    Returns 206 Partial Content with X-Total-Chars and X-Char-Range headers.

    For binary content types, offset/limit parameters are not supported (returns 400).
    """
    # Get metadata from database
    doc_metadata = db.get_document(document_id)

    if not doc_metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get file path from storage
    try:
        file_path = storage.get_document_path(document_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if partial content is requested
    partial_requested = offset is not None or limit is not None

    if partial_requested:
        # Only allow partial reads for text content types
        if not doc_metadata.content_type.startswith("text/"):
            raise HTTPException(
                status_code=400,
                detail="Partial content retrieval is only supported for text content types"
            )

        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        total_chars = len(content)

        # Apply offset and limit
        start = offset if offset is not None else 0
        if start < 0:
            start = 0
        if start > total_chars:
            start = total_chars

        if limit is not None:
            end = min(start + limit, total_chars)
        else:
            end = total_chars

        partial_content = content[start:end]

        # Return partial content with 206 status and headers
        return Response(
            content=partial_content,
            status_code=206,
            media_type=doc_metadata.content_type,
            headers={
                "X-Total-Chars": str(total_chars),
                "X-Char-Range": f"{start}-{end}",
                "Content-Disposition": f'inline; filename="{doc_metadata.filename}"'
            }
        )

    # Return full file as response (original behavior)
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
            metadata=doc.metadata,
            url=get_document_url(doc.id)
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

    # Delete from semantic search index if enabled
    if semantic_config.enabled:
        from .semantic.indexer import delete_document_index
        delete_document_index(document_id)

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
