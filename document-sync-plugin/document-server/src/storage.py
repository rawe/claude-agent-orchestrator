"""Storage layer for filesystem operations (Block 02 implementation)"""

import os
import hashlib
import secrets
import mimetypes
from pathlib import Path
from .models import DocumentMetadata


class DocumentStorage:
    """Manages document storage on the filesystem."""

    def __init__(self, base_dir: str):
        """Initialize storage with a directory path."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_document(self, content: bytes, filename: str) -> DocumentMetadata:
        """Store document and return metadata with checksum."""
        # Generate unique document ID
        doc_id = f"doc_{secrets.token_hex(12)}"

        # Calculate SHA256 checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Detect MIME type with fallback
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        # Calculate file size
        size_bytes = len(content)

        # Write file to storage (flat structure)
        file_path = self.base_dir / doc_id
        file_path.write_bytes(content)

        # Return metadata
        return DocumentMetadata(
            id=doc_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum=checksum,
            storage_path=str(file_path)
        )

    def get_document_path(self, doc_id: str) -> Path:
        """Get document path with path traversal protection."""
        file_path = self.base_dir / doc_id
        resolved = file_path.resolve()

        # Path traversal protection
        if not resolved.is_relative_to(self.base_dir.resolve()):
            raise ValueError("Invalid document ID - path traversal attempt")

        return resolved

    def delete_document(self, doc_id: str) -> bool:
        """Delete document from filesystem. Returns True if deleted, False if not found."""
        try:
            file_path = self.get_document_path(doc_id)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except ValueError:
            # Path traversal attempt
            return False
