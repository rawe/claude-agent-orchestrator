"""HTTP client for communicating with the document sync server."""
import httpx
from pathlib import Path
from typing import Optional
import mimetypes


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


# Supported MIME types for doc-read command (text files only)
SUPPORTED_TEXT_MIME_TYPES = [
    "text/*",
    "application/json",
    "application/xml",
]


def _is_text_mime_type(mime_type: str) -> bool:
    """Check if a MIME type is supported for text reading.

    Args:
        mime_type: The MIME type to check

    Returns:
        True if the MIME type is text-compatible, False otherwise
    """
    if not mime_type:
        return False

    for supported in SUPPORTED_TEXT_MIME_TYPES:
        if supported.endswith("*"):
            # Handle wildcard patterns like "text/*"
            prefix = supported[:-1]
            if mime_type.startswith(prefix):
                return True
        elif mime_type == supported:
            return True

    return False


class DocumentClient:
    """Client for interacting with the document sync server."""

    def __init__(self, config):
        """Initialize the client with configuration.

        Args:
            config: Config instance with base_url property
        """
        self.config = config
        self.base_url = config.base_url

    def push_document(
        self,
        file_path: str | Path,
        name: Optional[str] = None,
        tags: Optional[list[str]] = None,
        description: Optional[str] = None
    ) -> dict:
        """Upload a document to the server.

        Args:
            file_path: Path to the file to upload
            name: Custom name for the document (defaults to filename)
            tags: List of tags to associate with the document
            description: Description of the document

        Returns:
            JSON response from server with document metadata

        Raises:
            Exception: On network or HTTP errors
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file content
        content = file_path.read_bytes()

        # Determine filename
        filename = name if name else file_path.name

        # Detect content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = "application/octet-stream"

        # Prepare form data
        files = {"file": (filename, content, content_type)}
        data = {}

        # Add tags if provided
        if tags:
            data["tags"] = ",".join(tags)

        # Add metadata (description) if provided
        if description:
            import json
            data["metadata"] = json.dumps({"description": description})

        try:
            response = httpx.post(
                f"{self.base_url}/documents",
                files=files,
                data=data,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception("Server endpoint not found")
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Network error: {str(e)}")

    def query_documents(
        self,
        name: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: Optional[int] = None
    ) -> list[dict]:
        """Query documents from the server.

        Args:
            name: Filter by filename pattern
            tags: Filter by tags (AND logic - document must have all tags)
            limit: Maximum number of results to return

        Returns:
            List of document metadata dictionaries

        Raises:
            Exception: On network or HTTP errors
        """
        params = {}

        if name:
            params["filename"] = name

        if tags:
            params["tags"] = ",".join(tags)

        if limit:
            params["limit"] = limit

        try:
            response = httpx.get(
                f"{self.base_url}/documents",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Network error: {str(e)}")

    def pull_document(self, document_id: str) -> tuple[bytes, str]:
        """Download a document from the server.

        Args:
            document_id: ID of the document to download

        Returns:
            Tuple of (content_bytes, filename)

        Raises:
            Exception: On network or HTTP errors, including 404 if not found
        """
        try:
            response = httpx.get(
                f"{self.base_url}/documents/{document_id}",
                timeout=30.0
            )
            response.raise_for_status()

            # Extract filename from Content-Disposition header or use document_id
            filename = document_id
            content_disposition = response.headers.get("content-disposition", "")
            if "filename=" in content_disposition:
                # Parse filename from header
                parts = content_disposition.split("filename=")
                if len(parts) > 1:
                    filename = parts[1].strip('"\'')

            return response.content, filename

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"Document not found: {document_id}")
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Network error: {str(e)}")

    def delete_document(self, document_id: str) -> dict:
        """Delete a document from the server.

        Args:
            document_id: ID of the document to delete

        Returns:
            JSON response confirming deletion

        Raises:
            Exception: On network or HTTP errors, including 404 if not found
        """
        try:
            response = httpx.delete(
                f"{self.base_url}/documents/{document_id}",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"Document not found: {document_id}")
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Network error: {str(e)}")

    def get_document_info(self, document_id: str) -> dict:
        """Get metadata for a document without downloading the file.

        Args:
            document_id: ID of the document to get info for

        Returns:
            Dictionary with document metadata (id, filename, content_type,
            size_bytes, created_at, updated_at, tags, metadata)

        Raises:
            Exception: On network or HTTP errors, including 404 if not found
        """
        try:
            response = httpx.get(
                f"{self.base_url}/documents/{document_id}/metadata",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"Document not found: {document_id}")
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Network error: {str(e)}")

    def read_document(self, document_id: str) -> str:
        """Read text document content directly without downloading to file.

        This method only supports text files. For binary files, use pull_document().

        Args:
            document_id: ID of the document to read

        Returns:
            String content of the document (UTF-8 decoded)

        Raises:
            Exception: On network or HTTP errors, including:
                - 404 if document not found
                - Error if file is not a text file (non-text MIME type)
                - Error if file cannot be decoded as UTF-8
        """
        try:
            response = httpx.get(
                f"{self.base_url}/documents/{document_id}",
                timeout=30.0
            )
            response.raise_for_status()

            # Get content type from response headers
            content_type = response.headers.get("content-type", "")

            # Validate MIME type is text-compatible
            if not _is_text_mime_type(content_type):
                raise Exception(
                    f"Cannot read non-text file (MIME type: {content_type}). "
                    f"Use doc-pull to download binary files."
                )

            # Decode content to UTF-8 string
            try:
                return response.content.decode("utf-8")
            except UnicodeDecodeError:
                raise Exception(
                    "File is not valid UTF-8 text. Use doc-pull to download."
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"Document not found: {document_id}")
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Network error: {str(e)}")
