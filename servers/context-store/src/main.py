from fastapi import FastAPI, HTTPException, Query, Response, Request
from starlette.datastructures import UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import uvicorn
import os
import json

from .models import (
    DocumentResponse, SearchResponse, SearchResultItem, SectionInfo, RelationInfo,
    # Relation models
    RelationDefinitions, RelationDefinitionResponse, RelationCreateRequest,
    RelationResponse, RelationCreateResponse, RelationUpdateRequest,
    DocumentRelationsResponse, RelationDeleteResponse, DeleteResponseWithCascade,
    # Partition models
    PartitionCreate, PartitionResponse, PartitionListResponse, PartitionDeleteResponse,
    validate_partition_name
)
from .storage import DocumentStorage
from .database import DocumentDatabase, GLOBAL_PARTITION
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


def get_document_url(document_id: str, partition: str | None = None) -> str:
    """
    Construct the full URL for retrieving a document.

    Uses DOCUMENT_SERVER_PUBLIC_URL as the base, which can be configured
    to handle Docker port mapping, reverse proxies, or custom domains.

    Args:
        document_id: The unique document identifier
        partition: Optional partition (if provided, uses partitioned URL)

    Returns:
        Fully qualified URL (e.g., "http://localhost:8766/documents/doc_123")
    """
    # Remove trailing slash if present to avoid double slashes
    base_url = DOCUMENT_SERVER_PUBLIC_URL.rstrip('/')
    if partition and partition != GLOBAL_PARTITION:
        return f"{base_url}/partitions/{partition}/documents/{document_id}"
    return f"{base_url}/documents/{document_id}"


async def validate_partition(partition: str) -> None:
    """Validate partition exists and name is valid.

    Args:
        partition: Partition name to validate

    Raises:
        HTTPException: 404 if partition not found, 400 if invalid name
    """
    if not validate_partition_name(partition):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid partition name: {partition}. Must start with letter or underscore, "
                   "contain only letters, numbers, hyphens, underscores, and be 1-64 characters."
        )
    if not db.partition_exists(partition):
        raise HTTPException(status_code=404, detail=f"Partition not found: {partition}")


@app.get("/health")
async def health_check():
    """Health check endpoint for container monitoring."""
    return {"status": "healthy", "service": "context-store"}


# ==================== Partition Endpoints ====================

@app.post("/partitions", response_model=PartitionResponse, status_code=201)
async def create_partition(request: PartitionCreate):
    """Create a new partition.

    Args:
        request: PartitionCreate with name and optional description

    Returns:
        201: PartitionResponse with created partition details
        400: Invalid partition name
        409: Partition already exists
    """
    # Check if partition already exists
    if db.partition_exists(request.name):
        raise HTTPException(status_code=409, detail=f"Partition already exists: {request.name}")

    # Create partition
    partition = db.create_partition(request.name, request.description)

    # Ensure partition directory exists
    storage.ensure_partition_directory(request.name)

    return PartitionResponse(
        name=partition["name"],
        description=partition["description"],
        created_at=partition["created_at"]
    )


@app.get("/partitions", response_model=PartitionListResponse)
async def list_partitions():
    """List all user-created partitions.

    Note: The internal '_global' partition is excluded from this listing.
    The global partition is an implementation detail - clients access it via
    the non-partitioned endpoints (e.g., /documents instead of /partitions/_global/documents).
    This keeps the partition concept transparent: clients see partitions as optional
    namespaces, with the default/global space accessed through standard endpoints.
    """
    partitions = db.list_partitions()
    return PartitionListResponse(
        partitions=[
            PartitionResponse(
                name=p["name"],
                description=p["description"],
                created_at=p["created_at"]
            )
            for p in partitions
            if p["name"] != GLOBAL_PARTITION
        ]
    )


@app.delete("/partitions/{partition}", response_model=PartitionDeleteResponse)
async def delete_partition(partition: str):
    """Delete a partition and all its documents.

    Args:
        partition: Partition name to delete

    Returns:
        200: PartitionDeleteResponse with deleted document count
        403: Cannot delete _global partition
        404: Partition not found
    """
    # Cannot delete global partition
    if partition == GLOBAL_PARTITION:
        raise HTTPException(status_code=403, detail="Cannot delete the global partition")

    # Check if partition exists
    if not db.partition_exists(partition):
        raise HTTPException(status_code=404, detail=f"Partition not found: {partition}")

    # Delete all document indices from semantic search
    if semantic_config.enabled:
        from .semantic.indexer import delete_document_index
        doc_ids = db.get_partition_document_ids(partition)
        for doc_id in doc_ids:
            delete_document_index(doc_id)

    # Delete partition and documents from database
    deleted_count = db.delete_partition(partition)

    # Delete partition directory from storage
    storage.delete_partition_directory(partition)

    return PartitionDeleteResponse(
        success=True,
        message=f"Partition '{partition}' deleted",
        deleted_document_count=deleted_count
    )


# ==================== Partitioned Document Endpoints ====================

@app.post("/partitions/{partition}/documents", response_model=DocumentResponse, status_code=201)
async def create_document_partitioned(partition: str, request: Request):
    """Create a new document in a specific partition."""
    await validate_partition(partition)
    content_type_header = request.headers.get("content-type", "")

    if "application/json" in content_type_header:
        return await _create_placeholder_document(request, partition)
    else:
        return await _upload_document_file(request, partition)


@app.get("/partitions/{partition}/documents", response_model=list[DocumentResponse])
async def list_documents_partitioned(
    partition: str,
    filename: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0),
    include_relations: bool = Query(False, description="Include document relations in response")
):
    """List all documents in a specific partition."""
    await validate_partition(partition)
    return await _list_documents_impl(partition, filename, tags, limit, offset, include_relations)


@app.get("/partitions/{partition}/documents/{document_id}")
async def get_document_partitioned(
    partition: str,
    document_id: str,
    offset: Optional[int] = Query(None, description="Starting character position (0-indexed)"),
    limit: Optional[int] = Query(None, description="Number of characters to return")
):
    """Retrieve a specific document by ID from a partition."""
    await validate_partition(partition)
    return await _get_document_content_impl(document_id, partition, offset, limit)


@app.get("/partitions/{partition}/documents/{document_id}/metadata", response_model=DocumentResponse)
async def get_document_metadata_partitioned(partition: str, document_id: str):
    """Retrieve metadata for a specific document in a partition."""
    await validate_partition(partition)
    return await _get_document_metadata_impl(document_id, partition)


@app.put("/partitions/{partition}/documents/{document_id}/content", response_model=DocumentResponse)
async def write_document_content_partitioned(partition: str, document_id: str, request: Request):
    """Write or replace content of an existing document in a partition."""
    await validate_partition(partition)
    return await _write_document_content_impl(document_id, request, partition)


@app.patch("/partitions/{partition}/documents/{document_id}/content")
async def edit_document_content_partitioned(partition: str, document_id: str, request: Request):
    """Edit content of an existing document in a partition."""
    await validate_partition(partition)
    return await _edit_document_content_impl(document_id, request, partition)


@app.delete("/partitions/{partition}/documents/{document_id}", response_model=DeleteResponseWithCascade)
async def delete_document_partitioned(partition: str, document_id: str):
    """Delete a document by ID from a specific partition."""
    await validate_partition(partition)
    return await _delete_document_impl(document_id, partition)


@app.get("/partitions/{partition}/documents/{document_id}/relations", response_model=DocumentRelationsResponse)
async def get_document_relations_partitioned(partition: str, document_id: str):
    """Get all relations for a document in a partition."""
    await validate_partition(partition)
    # Validate document exists in partition
    if not db.document_exists(document_id, partition):
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


@app.get("/partitions/{partition}/search", response_model=SearchResponse)
async def search_documents_partitioned(
    partition: str,
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(10, description="Maximum documents to return", ge=1, le=100),
    include_relations: bool = Query(False, description="Include document relations in response")
):
    """Semantic search within a specific partition."""
    await validate_partition(partition)
    return await _search_documents_impl(q, partition, limit, include_relations)


async def _search_documents_impl(
    q: str,
    partition: str = GLOBAL_PARTITION,
    limit: int = 10,
    include_relations: bool = False
) -> SearchResponse:
    """Internal implementation for semantic search."""
    if not semantic_config.enabled:
        raise HTTPException(
            status_code=404,
            detail="Semantic search is not enabled"
        )

    from .semantic.search import search_documents

    # Perform semantic search with partition filter
    results = search_documents(q, partition=partition, limit=limit)

    # Collect document IDs for batch relation fetching
    doc_ids = [result["document_id"] for result in results]

    # Fetch relations in batch if requested
    relations_by_doc: dict[str, list[dict]] = {}
    if include_relations and doc_ids:
        relations_by_doc = db.get_relations_batch(doc_ids)

    # Enrich results with document metadata
    enriched_results = []
    for result in results:
        doc_metadata = db.get_document(result["document_id"], partition)
        if doc_metadata:
            relations = None
            if include_relations:
                doc_relations = relations_by_doc.get(result["document_id"], [])
                relations = _group_relations_for_response(doc_relations) if doc_relations else {}

            enriched_results.append(
                SearchResultItem(
                    document_id=result["document_id"],
                    filename=doc_metadata.filename,
                    document_url=get_document_url(result["document_id"], doc_metadata.partition),
                    sections=[SectionInfo(**s) for s in result["sections"]],
                    relations=relations
                )
            )

    return SearchResponse(query=q, results=enriched_results)


@app.get("/search", response_model=SearchResponse)
async def search_documents_endpoint(
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(10, description="Maximum documents to return", ge=1, le=100),
    include_relations: bool = Query(False, description="Include document relations in response")
):
    """Semantic search across indexed documents in global partition."""
    return await _search_documents_impl(q, GLOBAL_PARTITION, limit, include_relations)


@app.post("/documents", response_model=DocumentResponse, status_code=201)
async def create_document(request: Request):
    """Create a new document.

    Two modes based on Content-Type header:
    1. application/json: Create placeholder document without content
       - Body: {"filename": "doc.md", "tags": ["tag1"], "metadata": {"key": "value"}}
    2. multipart/form-data: Upload file with content (existing behavior)
       - file: The file to upload
       - tags: Comma-separated tags (optional)
       - metadata: JSON metadata string (optional)
    """
    content_type_header = request.headers.get("content-type", "")

    if "application/json" in content_type_header:
        # Placeholder creation mode
        return await _create_placeholder_document(request)
    else:
        # Multipart file upload mode (existing behavior)
        return await _upload_document_file(request)


async def _create_placeholder_document(request: Request, partition: str = GLOBAL_PARTITION) -> JSONResponse:
    """Create a placeholder document without content."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Validate required fields
    if "filename" not in body:
        raise HTTPException(status_code=400, detail="filename is required")

    filename = body["filename"]
    tags = body.get("tags", [])
    metadata = body.get("metadata", {})

    # Validate types
    if not isinstance(filename, str):
        raise HTTPException(status_code=400, detail="filename must be a string")
    if not isinstance(tags, list):
        raise HTTPException(status_code=400, detail="tags must be a list")
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be an object")

    # Create placeholder document in storage
    doc_metadata = storage.create_placeholder(filename, partition)

    # Add tags and metadata
    doc_metadata.tags = tags
    doc_metadata.metadata = metadata

    # Insert into database
    db.insert_document(doc_metadata, partition)

    # Do NOT index for semantic search - placeholder has no content

    # Return response
    response = DocumentResponse(
        id=doc_metadata.id,
        filename=doc_metadata.filename,
        content_type=doc_metadata.content_type,
        size_bytes=doc_metadata.size_bytes,
        checksum=doc_metadata.checksum,
        created_at=doc_metadata.created_at,
        updated_at=doc_metadata.updated_at,
        tags=doc_metadata.tags,
        metadata=doc_metadata.metadata,
        url=get_document_url(doc_metadata.id, partition),
        partition=partition if partition != GLOBAL_PARTITION else None
    )

    return JSONResponse(status_code=201, content=response.model_dump(mode="json"))


async def _upload_document_file(request: Request, partition: str = GLOBAL_PARTITION) -> JSONResponse:
    """Upload a document file with content (original behavior)."""
    form = await request.form()

    # Get file from form
    file = form.get("file")
    if not file or not isinstance(file, UploadFile):
        raise HTTPException(status_code=400, detail="file is required")

    # Parse tags from comma-separated string
    tags_str = form.get("tags")
    parsed_tags = []
    if tags_str and isinstance(tags_str, str):
        parsed_tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

    # Parse metadata from JSON string
    parsed_metadata = {}
    metadata_str = form.get("metadata")
    if metadata_str and isinstance(metadata_str, str):
        try:
            parsed_metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in metadata parameter")

    # Read file content
    content = await file.read()

    # Store document and get metadata (use client's MIME type if provided)
    doc_metadata = storage.store_document(
        content,
        file.filename or "unknown",
        partition,
        content_type=file.content_type
    )

    # Add tags to metadata
    doc_metadata.tags = parsed_tags
    doc_metadata.metadata = parsed_metadata

    # Insert into database
    db.insert_document(doc_metadata, partition)

    # Index for semantic search if enabled (only for text content)
    if semantic_config.enabled and doc_metadata.content_type.startswith("text/"):
        from .semantic.indexer import index_document
        text_content = content.decode("utf-8", errors="ignore")
        index_document(doc_metadata.id, text_content, partition)

    # Return response
    response = DocumentResponse(
        id=doc_metadata.id,
        filename=doc_metadata.filename,
        content_type=doc_metadata.content_type,
        size_bytes=doc_metadata.size_bytes,
        checksum=doc_metadata.checksum,
        created_at=doc_metadata.created_at,
        updated_at=doc_metadata.updated_at,
        tags=doc_metadata.tags,
        metadata=doc_metadata.metadata,
        url=get_document_url(doc_metadata.id, partition),
        partition=partition if partition != GLOBAL_PARTITION else None
    )

    return JSONResponse(status_code=201, content=response.model_dump(mode="json"))


async def _get_document_metadata_impl(document_id: str, partition: str = GLOBAL_PARTITION) -> DocumentResponse:
    """Internal implementation for getting document metadata."""
    # Get metadata from database with partition filter
    doc_metadata = db.get_document(document_id, partition)

    if not doc_metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # Return metadata response
    return DocumentResponse(
        id=doc_metadata.id,
        filename=doc_metadata.filename,
        content_type=doc_metadata.content_type,
        size_bytes=doc_metadata.size_bytes,
        checksum=doc_metadata.checksum,
        created_at=doc_metadata.created_at,
        updated_at=doc_metadata.updated_at,
        tags=doc_metadata.tags,
        metadata=doc_metadata.metadata,
        url=get_document_url(doc_metadata.id, doc_metadata.partition),
        partition=doc_metadata.partition if doc_metadata.partition and doc_metadata.partition != GLOBAL_PARTITION else None
    )


@app.get("/documents/{document_id}/metadata", response_model=DocumentResponse)
async def get_document_metadata(document_id: str):
    """Retrieve metadata for a specific document by ID (global partition)."""
    return await _get_document_metadata_impl(document_id, GLOBAL_PARTITION)


async def _get_document_content_impl(
    document_id: str,
    partition: str = GLOBAL_PARTITION,
    offset: Optional[int] = None,
    limit: Optional[int] = None
):
    """Internal implementation for getting document content."""
    # Get metadata from database with partition filter
    doc_metadata = db.get_document(document_id, partition)

    if not doc_metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get file path from storage
    try:
        file_path = storage.get_document_path(document_id, partition)
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


@app.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    offset: Optional[int] = Query(None, description="Starting character position (0-indexed)"),
    limit: Optional[int] = Query(None, description="Number of characters to return")
):
    """Retrieve a specific document by ID (global partition)."""
    return await _get_document_content_impl(document_id, GLOBAL_PARTITION, offset, limit)


async def _write_document_content_impl(document_id: str, request: Request, partition: str = GLOBAL_PARTITION) -> DocumentResponse:
    """Internal implementation for writing document content."""
    # 1. Verify document exists in partition
    doc_metadata = db.get_document(document_id, partition)
    if not doc_metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # 2. Read raw body content
    content = await request.body()

    # 3. Write to storage
    try:
        size_bytes, checksum = storage.write_document_content(document_id, partition, content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage write failed: {str(e)}")

    # 4. Update database
    now = datetime.now()
    db.update_document(
        document_id,
        size_bytes=size_bytes,
        checksum=checksum,
        updated_at=now
    )

    # 5. Re-index for semantic search if enabled
    if semantic_config.enabled:
        from .semantic.indexer import delete_document_index, index_document

        # Delete old chunks first
        delete_document_index(document_id)

        # Index new content (only for text types with content)
        if doc_metadata.content_type.startswith("text/") and len(content) > 0:
            text_content = content.decode("utf-8", errors="ignore")
            index_document(document_id, text_content, partition)

    # 6. Fetch and return updated metadata
    updated_metadata = db.get_document(document_id, partition)
    if not updated_metadata:
        raise HTTPException(status_code=404, detail="Document not found after update")
    return DocumentResponse(
        id=updated_metadata.id,
        filename=updated_metadata.filename,
        content_type=updated_metadata.content_type,
        size_bytes=updated_metadata.size_bytes,
        checksum=updated_metadata.checksum,
        created_at=updated_metadata.created_at,
        updated_at=updated_metadata.updated_at,
        tags=updated_metadata.tags,
        metadata=updated_metadata.metadata,
        url=get_document_url(updated_metadata.id, updated_metadata.partition),
        partition=updated_metadata.partition if updated_metadata.partition and updated_metadata.partition != GLOBAL_PARTITION else None
    )


@app.put("/documents/{document_id}/content", response_model=DocumentResponse)
async def write_document_content(document_id: str, request: Request):
    """Write or replace content of an existing document (global partition)."""
    return await _write_document_content_impl(document_id, request, GLOBAL_PARTITION)


async def _edit_document_content_impl(document_id: str, request: Request, partition: str = GLOBAL_PARTITION) -> JSONResponse:
    """Internal implementation for editing document content."""
    # 1. Verify document exists in partition
    doc_metadata = db.get_document(document_id, partition)
    if not doc_metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    # 2. Only allow edits on text content types
    if not doc_metadata.content_type.startswith("text/"):
        raise HTTPException(
            status_code=400,
            detail=f"Edit only supported for text content types (got: {doc_metadata.content_type})"
        )

    # 3. Parse JSON body
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # 4. Extract parameters
    old_string = body.get("old_string")
    new_string = body.get("new_string", "")
    replace_all = body.get("replace_all", False)
    offset = body.get("offset")
    length = body.get("length")

    # 5. Validate new_string is provided
    if "new_string" not in body:
        raise HTTPException(status_code=400, detail="new_string is required")

    # 6. Perform edit in storage
    try:
        size_bytes, checksum, edit_info = storage.edit_document_content(
            document_id,
            partition,
            old_string=old_string,
            new_string=new_string,
            replace_all=replace_all,
            offset=offset,
            length=length
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage edit failed: {str(e)}")

    # 7. Update database
    now = datetime.now()
    db.update_document(
        document_id,
        size_bytes=size_bytes,
        checksum=checksum,
        updated_at=now
    )

    # 8. Re-index for semantic search if enabled
    if semantic_config.enabled:
        from .semantic.indexer import delete_document_index, index_document

        # Delete old chunks first
        delete_document_index(document_id)

        # Index new content (only if non-empty)
        if size_bytes > 0:
            file_path = storage.get_document_path(document_id, partition)
            text_content = file_path.read_text(encoding="utf-8")
            index_document(document_id, text_content, partition)

    # 9. Fetch and return updated metadata with edit info
    updated_metadata = db.get_document(document_id, partition)
    if not updated_metadata:
        raise HTTPException(status_code=404, detail="Document not found after update")
    response_data = {
        "id": updated_metadata.id,
        "filename": updated_metadata.filename,
        "content_type": updated_metadata.content_type,
        "size_bytes": updated_metadata.size_bytes,
        "checksum": updated_metadata.checksum,
        "created_at": updated_metadata.created_at.isoformat() if hasattr(updated_metadata.created_at, 'isoformat') else str(updated_metadata.created_at),
        "updated_at": updated_metadata.updated_at.isoformat() if hasattr(updated_metadata.updated_at, 'isoformat') else str(updated_metadata.updated_at),
        "tags": updated_metadata.tags,
        "metadata": updated_metadata.metadata,
        "url": get_document_url(updated_metadata.id, updated_metadata.partition),
    }
    if updated_metadata.partition and updated_metadata.partition != GLOBAL_PARTITION:
        response_data["partition"] = updated_metadata.partition
    # Add edit-specific info
    response_data.update(edit_info)

    return JSONResponse(content=response_data)


@app.patch("/documents/{document_id}/content")
async def edit_document_content(document_id: str, request: Request):
    """Edit content of an existing document (global partition)."""
    return await _edit_document_content_impl(document_id, request, GLOBAL_PARTITION)


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


async def _list_documents_impl(
    partition: str = GLOBAL_PARTITION,
    filename: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    include_relations: bool = False
) -> list[DocumentResponse]:
    """Internal implementation for listing documents."""
    # Parse tags if provided
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else None

    # Query database with partition
    documents = db.query_documents(partition, filename=filename, tags=parsed_tags)

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
            checksum=doc.checksum,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            tags=doc.tags,
            metadata=doc.metadata,
            url=get_document_url(doc.id, doc.partition),
            relations=relations,
            partition=doc.partition if doc.partition and doc.partition != GLOBAL_PARTITION else None
        ))

    return responses


@app.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    filename: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0),
    include_relations: bool = Query(False, description="Include document relations in response")
):
    """List all documents with optional filtering (global partition)."""
    return await _list_documents_impl(GLOBAL_PARTITION, filename, tags, limit, offset, include_relations)


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
    """List all available relation definitions.

    Note: from_document_is/to_document_is describe what each document IS in the relationship.
    This is the inverse of internal from_type/to_type (what each document STORES).
    Example: parent-child has from_type="child", to_type="parent" internally,
    but from_document_is="parent", to_document_is="child" in the API response.
    """
    definitions = RelationDefinitions.get_all()
    return [
        RelationDefinitionResponse(
            name=d.name,
            description=d.description,
            # Swap: from_document IS what to_type says, to_document IS what from_type says
            from_document_is=d.to_type,
            to_document_is=d.from_type
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
    # from_to_note: note on edge from source to target (stored with from_document's relation row)
    # to_from_note: note on edge from target to source (stored with to_document's relation row)
    from_relation_id = db.create_relation(
        request.from_document_id,
        request.to_document_id,
        definition.from_type,
        request.from_to_note
    )
    to_relation_id = db.create_relation(
        request.to_document_id,
        request.from_document_id,
        definition.to_type,
        request.to_from_note
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


# ==================== Partitioned Relation Endpoints ====================

@app.post("/partitions/{partition}/relations", response_model=RelationCreateResponse, status_code=201)
async def create_relation_partitioned(partition: str, request: RelationCreateRequest):
    """Create a bidirectional relation between two documents in a partition.

    Both documents must be in the same partition (cross-partition relations not allowed).
    """
    await validate_partition(partition)

    # Validate definition
    definition = RelationDefinitions.get_by_name(request.definition)
    if not definition:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid relation definition: {request.definition}. "
                   f"Valid options: {[d.name for d in RelationDefinitions.get_all()]}"
        )

    # Validate both documents exist in the same partition
    if not db.document_exists(request.from_document_id, partition):
        raise HTTPException(status_code=404, detail=f"Document not found in partition: {request.from_document_id}")
    if not db.document_exists(request.to_document_id, partition):
        raise HTTPException(status_code=404, detail=f"Document not found in partition: {request.to_document_id}")

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
        request.from_to_note
    )
    to_relation_id = db.create_relation(
        request.to_document_id,
        request.from_document_id,
        definition.to_type,
        request.to_from_note
    )

    # Retrieve created relations for response
    from_relation = db.get_relation(from_relation_id)
    to_relation = db.get_relation(to_relation_id)
    if not from_relation or not to_relation:
        raise HTTPException(status_code=500, detail="Failed to retrieve created relations")

    return RelationCreateResponse(
        success=True,
        message="Relation created",
        from_relation=_relation_dict_to_response(from_relation),
        to_relation=_relation_dict_to_response(to_relation)
    )


@app.get("/partitions/{partition}/relations/definitions", response_model=list[RelationDefinitionResponse])
async def list_relation_definitions_partitioned(partition: str):
    """List all available relation definitions (same for all partitions)."""
    await validate_partition(partition)
    definitions = RelationDefinitions.get_all()
    return [
        RelationDefinitionResponse(
            name=d.name,
            description=d.description,
            from_document_is=d.to_type,
            to_document_is=d.from_type
        )
        for d in definitions
    ]


@app.patch("/partitions/{partition}/relations/{relation_id}", response_model=RelationResponse)
async def update_relation_note_partitioned(partition: str, relation_id: str, request: RelationUpdateRequest):
    """Update the note for an existing relation in a partition."""
    await validate_partition(partition)

    # Convert string ID to int for internal use
    try:
        internal_id = int(relation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid relation ID format")

    # Check if relation exists
    relation = db.get_relation(internal_id)
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")

    # Verify the related document is in the partition
    if not db.document_exists(relation["document_id"], partition):
        raise HTTPException(status_code=404, detail="Relation not found in partition")

    # Update the note
    db.update_relation_note(internal_id, request.note)

    # Return updated relation
    updated = db.get_relation(internal_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Relation not found after update")
    return _relation_dict_to_response(updated)


@app.delete("/partitions/{partition}/relations/{relation_id}", response_model=RelationDeleteResponse)
async def delete_relation_partitioned(partition: str, relation_id: str):
    """Delete a relation and its bidirectional counterpart from a partition."""
    await validate_partition(partition)

    # Convert string ID to int for internal use
    try:
        internal_id = int(relation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid relation ID format")

    # Get the relation being deleted
    relation = db.get_relation(internal_id)
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")

    # Verify the related document is in the partition
    if not db.document_exists(relation["document_id"], partition):
        raise HTTPException(status_code=404, detail="Relation not found in partition")

    deleted_ids = [str(internal_id)]

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
            deleted_ids.append(str(counterpart["id"]))

    # Delete the original relation
    db.delete_relation(internal_id)

    return RelationDeleteResponse(
        success=True,
        message="Relation removed",
        deleted_relation_ids=deleted_ids
    )


def _delete_document_with_cascade(doc_id: str, partition: str = GLOBAL_PARTITION) -> list[str]:
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
        deleted_ids.extend(_delete_document_with_cascade(child_id, partition))

    # Delete this document's resources
    storage.delete_document(doc_id, partition)

    # Delete from semantic search index if enabled
    if semantic_config.enabled:
        from .semantic.indexer import delete_document_index
        delete_document_index(doc_id)

    # Delete from database (relations auto-deleted via FK CASCADE)
    db.delete_document(doc_id)
    deleted_ids.append(doc_id)

    return deleted_ids


async def _delete_document_impl(document_id: str, partition: str = GLOBAL_PARTITION) -> DeleteResponseWithCascade:
    """Internal implementation for deleting a document."""
    # Check if document exists in partition
    if not db.document_exists(document_id, partition):
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete with cascade
    deleted_ids = _delete_document_with_cascade(document_id, partition)

    return DeleteResponseWithCascade(
        success=True,
        message=f"Deleted {len(deleted_ids)} document(s)",
        deleted_document_ids=deleted_ids
    )


@app.delete("/documents/{document_id}", response_model=DeleteResponseWithCascade)
async def delete_document(document_id: str):
    """Delete a document by ID (global partition)."""
    return await _delete_document_impl(document_id, GLOBAL_PARTITION)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=DOCUMENT_SERVER_HOST,
        port=DOCUMENT_SERVER_PORT,
        reload=True
    )
