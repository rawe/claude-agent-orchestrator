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

    def edit_document_content(
        self,
        doc_id: str,
        old_string: str | None = None,
        new_string: str = "",
        replace_all: bool = False,
        offset: int | None = None,
        length: int | None = None
    ) -> tuple[int, str, dict]:
        """Edit content in an existing document.

        Two modes:
        1. String replacement (old_string provided): Find and replace text
        2. Offset-based (offset provided): Insert/replace/delete at position

        Args:
            doc_id: Document ID
            old_string: Text to find and replace (string mode)
            new_string: Replacement text or text to insert
            replace_all: Replace all occurrences (string mode only)
            offset: Character position for offset mode
            length: Characters to replace at offset (0 = insert)

        Returns:
            Tuple of (size_bytes, checksum, edit_info)
            edit_info contains: replacements_made (string mode) or edit_range (offset mode)

        Raises:
            ValueError: If document path is invalid, mode validation fails,
                       string not found, or ambiguous match
            FileNotFoundError: If document file doesn't exist
        """
        file_path = self.get_document_path(doc_id)

        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {doc_id}")

        # Read current content as UTF-8
        content = file_path.read_text(encoding="utf-8")
        edit_info = {}

        # Determine mode based on which parameters are provided
        has_old_string = old_string is not None
        has_offset = offset is not None

        if has_old_string and has_offset:
            raise ValueError("Cannot mix old_string and offset modes")

        if not has_old_string and not has_offset:
            raise ValueError("Must provide old_string or offset")

        if has_old_string:
            # String replacement mode
            count = content.count(old_string)

            if count == 0:
                raise ValueError("old_string not found in document")

            if count > 1 and not replace_all:
                raise ValueError(
                    f"old_string matches {count} times; use replace_all=true or provide more context"
                )

            if replace_all:
                new_content = content.replace(old_string, new_string)
                edit_info["replacements_made"] = count
            else:
                new_content = content.replace(old_string, new_string, 1)
                edit_info["replacements_made"] = 1

        else:
            # Offset-based mode
            content_length = len(content)
            edit_length = length if length is not None else 0

            if offset < 0:
                raise ValueError("offset must be non-negative")

            if offset > content_length:
                raise ValueError(f"offset {offset} exceeds document length {content_length}")

            if edit_length > 0 and (offset + edit_length) > content_length:
                raise ValueError(
                    f"range exceeds document length (offset={offset}, length={edit_length}, doc_length={content_length})"
                )

            # Perform operation: content[0:offset] + new_string + content[offset+length:]
            new_content = content[:offset] + new_string + content[offset + edit_length:]
            edit_info["edit_range"] = {
                "offset": offset,
                "old_length": edit_length,
                "new_length": len(new_string)
            }

        # Write modified content
        content_bytes = new_content.encode("utf-8")
        file_path.write_bytes(content_bytes)

        # Calculate checksum and size
        checksum = hashlib.sha256(content_bytes).hexdigest()
        size_bytes = len(content_bytes)

        return size_bytes, checksum, edit_info
