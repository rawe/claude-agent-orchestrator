"""Storage layer for filesystem operations (Block 02 implementation)"""


class DocumentStorage:
    """Manages document storage on the filesystem."""

    def __init__(self, storage_dir: str):
        """Initialize storage with a directory path."""
        pass

    async def save_document(self, doc_id: str, file_content: bytes) -> str:
        """Save document content to filesystem and return storage path."""
        raise NotImplementedError()

    async def get_document(self, doc_id: str) -> bytes:
        """Retrieve document content from filesystem."""
        raise NotImplementedError()

    async def delete_document(self, doc_id: str) -> bool:
        """Delete document from filesystem."""
        raise NotImplementedError()
