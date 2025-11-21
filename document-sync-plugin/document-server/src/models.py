from pydantic import BaseModel, Field
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Internal document metadata with storage details."""
    id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    filename: str
    content_type: str = "text/markdown"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentQueryParams(BaseModel):
    """Query parameters for document search."""
    tags: list[str] | None = None
    content_type: str | None = None
    limit: int = 100
    offset: int = 0


class DocumentResponse(BaseModel):
    """Public-facing document response (excludes storage_path)."""
    id: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime
    tags: list[str]
    metadata: dict[str, str]


class DeleteResponse(BaseModel):
    """Response model for document deletion."""
    success: bool
    message: str
    document_id: str
