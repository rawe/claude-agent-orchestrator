"""HTTP client for communicating with the document sync server."""
import httpx
from pathlib import Path
from typing import Optional
import mimetypes


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
