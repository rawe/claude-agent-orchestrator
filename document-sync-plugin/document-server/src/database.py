"""Database layer for metadata persistence (Block 02 implementation)"""

from .models import DocumentMetadata, DocumentQueryParams


class DocumentDatabase:
    """Manages document metadata in SQLite database."""

    def __init__(self, db_path: str):
        """Initialize database connection."""
        pass

    async def insert_metadata(self, metadata: DocumentMetadata) -> None:
        """Insert document metadata into database."""
        raise NotImplementedError()

    async def get_metadata(self, doc_id: str) -> DocumentMetadata | None:
        """Retrieve document metadata by ID."""
        raise NotImplementedError()

    async def query_metadata(self, params: DocumentQueryParams) -> list[DocumentMetadata]:
        """Query documents by filters (tags, content_type, etc.)."""
        raise NotImplementedError()

    async def delete_metadata(self, doc_id: str) -> bool:
        """Delete document metadata from database."""
        raise NotImplementedError()
