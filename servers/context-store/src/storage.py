"""Storage layer for filesystem operations (Block 02 implementation)"""

import hashlib
import secrets
import mimetypes
from pathlib import Path
from .models import DocumentMetadata


def _init_custom_mime_types():
    """Register custom MIME types for common file extensions not in system database."""
    custom_types = {
        '.md': 'text/markdown',
        '.markdown': 'text/markdown',
        '.yaml': 'text/yaml',
        '.yml': 'text/yaml',
        '.json': 'application/json',
        '.jsonl': 'application/jsonl',
        '.toml': 'application/toml',
        '.ini': 'text/plain',
        '.conf': 'text/plain',
        '.log': 'text/plain',
    }
    for ext, mime_type in custom_types.items():
        mimetypes.add_type(mime_type, ext)


# Initialize custom MIME types on module import
_init_custom_mime_types()


def infer_content_type(filename: str) -> str:
    """Infer MIME type from filename extension.

    Args:
        filename: Document filename

    Returns:
        MIME type string (defaults to application/octet-stream if unknown)
    """
    content_type = mimetypes.guess_type(filename)[0]
    return content_type if content_type else "application/octet-stream"


class DocumentStorage:
    """Manages document storage on the filesystem."""

    def __init__(self, base_dir: str):
        """Initialize storage with a directory path."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_document(self, content: bytes, filename: str, content_type: str | None = None) -> DocumentMetadata:
        """Store document and return metadata with checksum.

        Args:
            content: File content as bytes
            filename: Original filename
            content_type: Optional MIME type from client. If not provided, will detect from filename.

        Returns:
            DocumentMetadata with all file information
        """
        # Generate unique document ID
        doc_id = f"doc_{secrets.token_hex(12)}"

        # Calculate SHA256 checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Use client-provided MIME type, or detect from filename as fallback
        if not content_type:
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

    def create_placeholder(self, filename: str, content_type: str | None = None) -> DocumentMetadata:
        """Create an empty placeholder document.

        Args:
            filename: Document filename (used for content-type inference if not provided)
            content_type: Optional MIME type (inferred from filename if not provided)

        Returns:
            DocumentMetadata with generated ID, empty file, checksum=None, size_bytes=0
        """
        # Generate unique document ID
        doc_id = f"doc_{secrets.token_hex(12)}"

        # Infer content type from filename if not provided
        if not content_type:
            content_type = infer_content_type(filename)

        # Create empty file (0 bytes)
        file_path = self.base_dir / doc_id
        file_path.touch()

        # Return metadata with checksum=None to indicate placeholder
        return DocumentMetadata(
            id=doc_id,
            filename=filename,
            content_type=content_type,
            size_bytes=0,
            checksum=None,
            storage_path=str(file_path)
        )

    def write_document_content(self, doc_id: str, content: bytes) -> tuple[int, str]:
        """Write content to an existing document file.

        Args:
            doc_id: Document ID
            content: Content bytes to write

        Returns:
            Tuple of (size_bytes, checksum)

        Raises:
            ValueError: If document path is invalid (path traversal)
            FileNotFoundError: If document file doesn't exist
        """
        file_path = self.get_document_path(doc_id)

        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {doc_id}")

        # Write content (full replacement)
        file_path.write_bytes(content)

        # Calculate checksum and size
        checksum = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)

        return size_bytes, checksum
