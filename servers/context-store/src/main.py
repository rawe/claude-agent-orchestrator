from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
import os
import json

from .models import (
    DocumentResponse, SearchResponse, SearchResultItem, SectionInfo, RelationInfo,
    # Relation models
    RelationDefinitions, RelationDefinitionResponse, RelationCreateRequest,
    RelationResponse, RelationCreateResponse, RelationUpdateRequest,
    DocumentRelationsResponse, RelationDeleteResponse, DeleteResponseWithCascade
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
    limit: int = Query(10, description="Maximum documents to return", ge=1, le=100),
    include_relations: bool = Query(False, description="Include document relations in response")
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

    # Collect document IDs for batch relation fetching
    doc_ids = [result["document_id"] for result in results]

    # Fetch relations in batch if requested
    relations_by_doc: dict[str, list[dict]] = {}
    if include_relations and doc_ids:
        relations_by_doc = db.get_relations_batch(doc_ids)

    # Enrich results with document metadata
    enriched_results = []
    for result in results:
        doc_metadata = db.get_document(result["document_id"])
        if doc_metadata:
            relations = None
            if include_relations:
                doc_relations = relations_by_doc.get(result["document_id"], [])
                relations = _group_relations_for_response(doc_relations) if doc_relations else {}

            enriched_results.append(
                SearchResultItem(
                    document_id=result["document_id"],
                    filename=doc_metadata.filename,
                    document_url=get_document_url(result["document_id"]),
                    sections=[SectionInfo(**s) for s in result["sections"]],
                    relations=relations
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


def _group_relations_for_response(relations: list[dict]) -> dict[str, list[RelationInfo]]:
    """Group relation dicts by relation_type and convert to RelationInfo."""
    grouped: dict[str, list[RelationInfo]] = {}
    for rel in relations:
        rel_type = rel["relation_type"]
        if rel_type not in grouped:
            grouped[rel_type] = []
        grouped[rel_type].append(RelationInfo(
            id=str(rel["id"]),
            related_document_id=rel["related_document_id"],
            relation_type=rel["relation_type"],
            note=rel["note"]
        ))
    return grouped


@app.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    filename: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0),
    include_relations: bool = Query(False, description="Include document relations in response")
):
    """List all documents with optional filtering by filename and/or tags."""
    # Parse tags if provided
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else None

    # Query database
    documents = db.query_documents(filename=filename, tags=parsed_tags)

    # Apply pagination first (before fetching relations)
    paginated_docs = documents[offset:offset + limit]

    # Fetch relations in batch if requested
    relations_by_doc: dict[str, list[dict]] = {}
    if include_relations and paginated_docs:
        doc_ids = [doc.id for doc in paginated_docs]
        relations_by_doc = db.get_relations_batch(doc_ids)

    # Convert to response model
    responses = []
    for doc in paginated_docs:
        relations = None
        if include_relations:
            doc_relations = relations_by_doc.get(doc.id, [])
            relations = _group_relations_for_response(doc_relations) if doc_relations else {}

        responses.append(DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            size_bytes=doc.size_bytes,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            tags=doc.tags,
            metadata=doc.metadata,
            url=get_document_url(doc.id),
            relations=relations
        ))

    return responses


# ==================== Relation Endpoints ====================

def _relation_dict_to_response(rel: dict) -> RelationResponse:
    """Convert database relation dict to response model with string ID."""
    return RelationResponse(
        id=str(rel["id"]),  # Convert int to str for external API
        document_id=rel["document_id"],
        related_document_id=rel["related_document_id"],
        relation_type=rel["relation_type"],
        note=rel["note"],
        created_at=rel["created_at"],
        updated_at=rel["updated_at"]
    )


@app.get("/relations/definitions", response_model=list[RelationDefinitionResponse])
async def list_relation_definitions():
    """List all available relation definitions."""
    definitions = RelationDefinitions.get_all()
    return [
        RelationDefinitionResponse(
            name=d.name,
            description=d.description,
            from_type=d.from_type,
            to_type=d.to_type
        )
        for d in definitions
    ]


@app.post("/relations", response_model=RelationCreateResponse, status_code=201)
async def create_relation(request: RelationCreateRequest):
    """
    Create a bidirectional relation between two documents.

    Creates two relation rows:
    - From document stores relation_type = definition.from_type
    - To document stores relation_type = definition.to_type
    """
    # Validate definition
    definition = RelationDefinitions.get_by_name(request.definition)
    if not definition:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid relation definition: {request.definition}. "
                   f"Valid options: {[d.name for d in RelationDefinitions.get_all()]}"
        )

    # Validate documents exist
    if not db.document_exists(request.from_document_id):
        raise HTTPException(status_code=404, detail=f"Document not found: {request.from_document_id}")
    if not db.document_exists(request.to_document_id):
        raise HTTPException(status_code=404, detail=f"Document not found: {request.to_document_id}")

    # Check if relation already exists
    existing = db.find_relation(
        request.from_document_id,
        request.to_document_id,
        definition.from_type
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Relation already exists between these documents with type '{definition.name}'"
        )

    # Create both relation rows
    from_relation_id = db.create_relation(
        request.from_document_id,
        request.to_document_id,
        definition.from_type,
        request.from_note
    )
    to_relation_id = db.create_relation(
        request.to_document_id,
        request.from_document_id,
        definition.to_type,
        request.to_note
    )

    # Retrieve created relations for response
    from_relation = db.get_relation(from_relation_id)
    to_relation = db.get_relation(to_relation_id)

    return RelationCreateResponse(
        success=True,
        message="Relation created",
        from_relation=_relation_dict_to_response(from_relation),
        to_relation=_relation_dict_to_response(to_relation)
    )


@app.get("/documents/{document_id}/relations", response_model=DocumentRelationsResponse)
async def get_document_relations(document_id: str):
    """Get all relations for a document, grouped by relation_type."""
    # Validate document exists
    if not db.document_exists(document_id):
        raise HTTPException(status_code=404, detail="Document not found")

    # Get all relations
    relations = db.get_document_relations(document_id)

    # Group by relation_type
    grouped: dict[str, list[RelationResponse]] = {}
    for rel in relations:
        rel_type = rel["relation_type"]
        if rel_type not in grouped:
            grouped[rel_type] = []
        grouped[rel_type].append(_relation_dict_to_response(rel))

    return DocumentRelationsResponse(
        document_id=document_id,
        relations=grouped
    )


@app.patch("/relations/{relation_id}", response_model=RelationResponse)
async def update_relation_note(relation_id: str, request: RelationUpdateRequest):
    """Update the note for an existing relation."""
    # Convert string ID to int for internal use
    try:
        internal_id = int(relation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid relation ID format")

    # Check if relation exists
    relation = db.get_relation(internal_id)
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")

    # Update the note
    db.update_relation_note(internal_id, request.note)

    # Return updated relation
    updated = db.get_relation(internal_id)
    return _relation_dict_to_response(updated)


@app.delete("/relations/{relation_id}", response_model=RelationDeleteResponse)
async def delete_relation(relation_id: str):
    """
    Delete a relation and its bidirectional counterpart.

    This removes the relation only, NOT the documents.
    Both relation rows (the relation and its inverse) are deleted.
    """
    # Convert string ID to int for internal use
    try:
        internal_id = int(relation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid relation ID format")

    # Get the relation being deleted
    relation = db.get_relation(internal_id)
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")

    deleted_ids = [str(internal_id)]  # Store as strings for response

    # Find and delete the counterpart relation
    inverse_type = RelationDefinitions.get_inverse_type(relation["relation_type"])
    if inverse_type:
        counterpart = db.find_relation(
            relation["related_document_id"],
            relation["document_id"],
            inverse_type
        )
        if counterpart:
            db.delete_relation(counterpart["id"])
            deleted_ids.append(str(counterpart["id"]))  # Convert to string

    # Delete the original relation
    db.delete_relation(internal_id)

    return RelationDeleteResponse(
        success=True,
        message="Relation removed",
        deleted_relation_ids=deleted_ids
    )


def _delete_document_with_cascade(doc_id: str) -> list[str]:
    """
    Delete a document with cascade deletion of children (parent-child relations).

    Uses recursive calls so each document handles its own cleanup
    (file, Elasticsearch, database).

    Returns list of all deleted document IDs.
    """
    deleted_ids = []

    # Get children (where this document is a parent)
    children = db.get_child_document_ids(doc_id)

    # Recursively delete children first
    for child_id in children:
        deleted_ids.extend(_delete_document_with_cascade(child_id))

    # Delete this document's resources
    storage.delete_document(doc_id)

    # Delete from semantic search index if enabled
    if semantic_config.enabled:
        from .semantic.indexer import delete_document_index
        delete_document_index(doc_id)

    # Delete from database (relations auto-deleted via FK CASCADE)
    db.delete_document(doc_id)
    deleted_ids.append(doc_id)

    return deleted_ids


@app.delete("/documents/{document_id}", response_model=DeleteResponseWithCascade)
async def delete_document(document_id: str):
    """
    Delete a document by ID from storage, database, and search index.

    For documents with parent-child relations:
    - If the document is a parent, all children are recursively deleted first
    - Related documents (non-hierarchical) are NOT deleted, only their relations are removed
    """
    # Check if document exists
    if not db.document_exists(document_id):
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete with cascade
    deleted_ids = _delete_document_with_cascade(document_id)

    return DeleteResponseWithCascade(
        success=True,
        message=f"Deleted {len(deleted_ids)} document(s)",
        deleted_document_ids=deleted_ids
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=DOCUMENT_SERVER_HOST,
        port=DOCUMENT_SERVER_PORT,
        reload=True
    )
