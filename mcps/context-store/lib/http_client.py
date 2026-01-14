"""Async HTTP client for the Context Store server."""

import mimetypes
from pathlib import Path
from typing import Any, Optional

import httpx

from .config import Config
from .exceptions import (
    ConnectionError,
    ContextStoreError,
    DocumentNotFoundError,
    NotTextFileError,
    RelationNotFoundError,
    SemanticSearchDisabledError,
    ValidationError,
)


def _init_custom_mime_types() -> None:
    """Register custom MIME types for common file extensions."""
    custom_types = {
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
        ".json": "application/json",
        ".jsonl": "application/jsonl",
        ".toml": "application/toml",
        ".ini": "text/plain",
        ".conf": "text/plain",
        ".log": "text/plain",
    }
    for ext, mime_type in custom_types.items():
        mimetypes.add_type(mime_type, ext)


# Initialize custom MIME types on module import
_init_custom_mime_types()


# Supported MIME types for text reading
SUPPORTED_TEXT_MIME_TYPES = [
    "text/*",
    "application/json",
    "application/xml",
]


def _is_text_mime_type(mime_type: str) -> bool:
    """Check if a MIME type is supported for text reading."""
    if not mime_type:
        return False

    for supported in SUPPORTED_TEXT_MIME_TYPES:
        if supported.endswith("*"):
            prefix = supported[:-1]
            if mime_type.startswith(prefix):
                return True
        elif mime_type == supported:
            return True

    return False


class ContextStoreClient:
    """Async client for interacting with the Context Store server."""

    def __init__(self, config: Config | None = None):
        """Initialize the client with configuration.

        Args:
            config: Config instance (uses defaults if not provided)
        """
        self.config = config or Config()
        self.base_url = self.config.base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ContextStoreClient":
        """Enter async context manager."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating one if necessary."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # =====================
    # Document Operations
    # =====================

    async def push_document(
        self,
        file_path: str | Path,
        name: Optional[str] = None,
        tags: Optional[list[str]] = None,
        description: Optional[str] = None,
    ) -> dict:
        """Upload a document to the Context Store.

        Args:
            file_path: Path to the file to upload
            name: Custom name for the document (defaults to filename)
            tags: List of tags to associate with the document
            description: Description of the document

        Returns:
            JSON response from server with document metadata

        Raises:
            FileNotFoundError: If the file does not exist
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_bytes()
        filename = name if name else file_path.name

        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = "application/octet-stream"

        files = {"file": (filename, content, content_type)}
        data = {}

        if tags:
            data["tags"] = ",".join(tags)

        if description:
            import json

            data["metadata"] = json.dumps({"description": description})

        try:
            client = self._get_client()
            response = await client.post(
                f"{self.base_url}/documents",
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def create_document(
        self,
        filename: str,
        tags: Optional[list[str]] = None,
        description: Optional[str] = None,
    ) -> dict:
        """Create a placeholder document without content.

        Args:
            filename: Document filename (used for content-type inference)
            tags: List of tags for categorization
            description: Human-readable description

        Returns:
            JSON response with document metadata including generated ID

        Raises:
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        payload = {
            "filename": filename,
            "tags": tags or [],
            "metadata": {},
        }

        if description:
            payload["metadata"]["description"] = description

        try:
            client = self._get_client()
            response = await client.post(
                f"{self.base_url}/documents",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def write_document_content(
        self,
        document_id: str,
        content: str | bytes,
    ) -> dict:
        """Write content to an existing document.

        Args:
            document_id: ID of the document to write to
            content: Content to write (string or bytes)

        Returns:
            JSON response with updated document metadata

        Raises:
            DocumentNotFoundError: If document not found
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        if isinstance(content, str):
            content = content.encode("utf-8")

        try:
            client = self._get_client()
            response = await client.put(
                f"{self.base_url}/documents/{document_id}/content",
                content=content,
                headers={"Content-Type": "application/octet-stream"},
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DocumentNotFoundError(document_id)
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def edit_document_content(
        self,
        document_id: str,
        new_string: str,
        old_string: Optional[str] = None,
        replace_all: bool = False,
        offset: Optional[int] = None,
        length: Optional[int] = None,
    ) -> dict:
        """Edit document content surgically without full replacement.

        Two modes:
        1. String replacement: Provide old_string + new_string
        2. Offset-based: Provide offset + new_string (+ optional length)

        Args:
            document_id: ID of the document to edit
            new_string: Replacement text or text to insert
            old_string: Text to find and replace (string mode)
            replace_all: Replace all occurrences (string mode only)
            offset: Character position for offset mode
            length: Characters to replace at offset (0 = insert)

        Returns:
            JSON response with updated document metadata and edit details

        Raises:
            DocumentNotFoundError: If document not found
            ValidationError: If edit parameters are invalid
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        payload: dict[str, Any] = {"new_string": new_string}

        if old_string is not None:
            payload["old_string"] = old_string
            payload["replace_all"] = replace_all
        elif offset is not None:
            payload["offset"] = offset
            if length is not None:
                payload["length"] = length

        try:
            client = self._get_client()
            response = await client.patch(
                f"{self.base_url}/documents/{document_id}/content",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DocumentNotFoundError(document_id)
            if e.response.status_code == 400:
                try:
                    detail = e.response.json().get("detail", e.response.text)
                except Exception:
                    detail = e.response.text
                raise ValidationError(f"Edit failed: {detail}")
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def query_documents(
        self,
        name: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: Optional[int] = None,
        include_relations: bool = False,
    ) -> list[dict]:
        """Query documents from the Context Store.

        Args:
            name: Filter by filename pattern
            tags: Filter by tags (AND logic - document must have all tags)
            limit: Maximum number of results to return
            include_relations: Include document relations in response

        Returns:
            List of document metadata dictionaries

        Raises:
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        params = {}

        if name:
            params["filename"] = name

        if tags:
            params["tags"] = ",".join(tags)

        if limit:
            params["limit"] = limit

        if include_relations:
            params["include_relations"] = "true"

        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/documents",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def search_documents(
        self,
        query: str,
        limit: Optional[int] = None,
        include_relations: bool = False,
    ) -> dict:
        """Semantic search for documents by meaning.

        Args:
            query: Natural language search query
            limit: Maximum number of results
            include_relations: Include document relations in response

        Returns:
            Search results with documents ranked by similarity

        Raises:
            SemanticSearchDisabledError: If semantic search not enabled
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        params: dict[str, Any] = {"q": query}

        if limit:
            params["limit"] = limit

        if include_relations:
            params["include_relations"] = "true"

        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/search",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise SemanticSearchDisabledError()
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def get_document_info(self, document_id: str) -> dict:
        """Get metadata for a document without downloading content.

        Args:
            document_id: ID of the document

        Returns:
            Document metadata (id, filename, content_type, size_bytes, etc.)

        Raises:
            DocumentNotFoundError: If document not found
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/documents/{document_id}/metadata",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DocumentNotFoundError(document_id)
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def read_document(
        self,
        document_id: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> tuple[str, Optional[int], Optional[str]]:
        """Read text document content directly.

        Only supports text files. For binary files, use pull_document().
        Supports partial content retrieval via offset and limit.

        Args:
            document_id: ID of the document to read
            offset: Starting character position (0-indexed)
            limit: Number of characters to return

        Returns:
            Tuple of (content, total_chars, char_range)

        Raises:
            DocumentNotFoundError: If document not found
            NotTextFileError: If file is not a text file
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        params = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit

        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/documents/{document_id}",
                params=params if params else None,
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if not _is_text_mime_type(content_type):
                raise NotTextFileError(content_type)

            total_chars = response.headers.get("x-total-chars")
            char_range = response.headers.get("x-char-range")

            total_chars = int(total_chars) if total_chars else None

            try:
                content = response.content.decode("utf-8")
                return content, total_chars, char_range
            except UnicodeDecodeError:
                raise ContextStoreError(
                    "File is not valid UTF-8 text. Use pull_document to download."
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DocumentNotFoundError(document_id)
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def pull_document(self, document_id: str) -> tuple[bytes, str]:
        """Download a document from the Context Store.

        Args:
            document_id: ID of the document to download

        Returns:
            Tuple of (content_bytes, filename)

        Raises:
            DocumentNotFoundError: If document not found
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/documents/{document_id}",
            )
            response.raise_for_status()

            filename = document_id
            content_disposition = response.headers.get("content-disposition", "")
            if "filename=" in content_disposition:
                parts = content_disposition.split("filename=")
                if len(parts) > 1:
                    filename = parts[1].strip("\"'")

            return response.content, filename

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DocumentNotFoundError(document_id)
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def delete_document(self, document_id: str) -> dict:
        """Delete a document from the Context Store.

        Args:
            document_id: ID of the document to delete

        Returns:
            JSON response confirming deletion

        Raises:
            DocumentNotFoundError: If document not found
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        try:
            client = self._get_client()
            response = await client.delete(
                f"{self.base_url}/documents/{document_id}",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DocumentNotFoundError(document_id)
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    # =====================
    # Relation Operations
    # =====================

    async def get_relation_definitions(self) -> list[dict]:
        """Get available relation definitions.

        Returns:
            List of relation definitions with name, description, etc.

        Raises:
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/relations/definitions",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def get_document_relations(self, document_id: str) -> dict:
        """Get all relations for a document.

        Args:
            document_id: ID of the document

        Returns:
            Dictionary with relations grouped by type

        Raises:
            DocumentNotFoundError: If document not found
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/documents/{document_id}/relations",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DocumentNotFoundError(document_id)
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def create_relation(
        self,
        from_document_id: str,
        to_document_id: str,
        definition: str,
        from_to_note: Optional[str] = None,
        to_from_note: Optional[str] = None,
    ) -> dict:
        """Create a bidirectional relation between documents.

        Args:
            from_document_id: Source document ID
            to_document_id: Target document ID
            definition: Relation type (e.g., 'parent-child', 'related')
            from_to_note: Note on edge from source to target
            to_from_note: Note on edge from target to source

        Returns:
            Dictionary with created relation details

        Raises:
            DocumentNotFoundError: If a document not found
            ValidationError: If relation is invalid
            ContextStoreError: On HTTP errors (including conflict)
            ConnectionError: On network errors
        """
        payload = {
            "definition": definition,
            "from_document_id": from_document_id,
            "to_document_id": to_document_id,
            "from_to_note": from_to_note,
            "to_from_note": to_from_note,
        }

        try:
            client = self._get_client()
            response = await client.post(
                f"{self.base_url}/relations",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DocumentNotFoundError("Document not found")
            if e.response.status_code == 400:
                raise ValidationError(f"Invalid relation: {e.response.text}")
            if e.response.status_code == 409:
                raise ContextStoreError("Relation already exists")
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def update_relation(
        self,
        relation_id: str,
        note: Optional[str],
    ) -> dict:
        """Update a relation's note.

        Args:
            relation_id: ID of the relation to update
            note: New note text (can be None to clear)

        Returns:
            Updated relation details

        Raises:
            RelationNotFoundError: If relation not found
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        try:
            client = self._get_client()
            response = await client.patch(
                f"{self.base_url}/relations/{relation_id}",
                json={"note": note},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RelationNotFoundError(relation_id)
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")

    async def delete_relation(self, relation_id: str) -> dict:
        """Delete a relation (removes both directions).

        Args:
            relation_id: ID of the relation to delete

        Returns:
            Dictionary with success status

        Raises:
            RelationNotFoundError: If relation not found
            ConnectionError: On network errors
            ContextStoreError: On HTTP errors
        """
        try:
            client = self._get_client()
            response = await client.delete(
                f"{self.base_url}/relations/{relation_id}",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RelationNotFoundError(relation_id)
            raise ContextStoreError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {str(e)}")
