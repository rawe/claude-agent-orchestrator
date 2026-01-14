"""Custom exceptions for the Context Store client."""


class ContextStoreError(Exception):
    """Base exception for Context Store operations."""

    pass


class ConnectionError(ContextStoreError):
    """Raised when unable to connect to the Context Store server."""

    pass


class DocumentNotFoundError(ContextStoreError):
    """Raised when a requested document does not exist."""

    def __init__(self, document_id: str):
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class RelationNotFoundError(ContextStoreError):
    """Raised when a requested relation does not exist."""

    def __init__(self, relation_id: str):
        self.relation_id = relation_id
        super().__init__(f"Relation not found: {relation_id}")


class ValidationError(ContextStoreError):
    """Raised when input validation fails."""

    pass


class NotTextFileError(ContextStoreError):
    """Raised when attempting to read a non-text file as text."""

    def __init__(self, mime_type: str):
        self.mime_type = mime_type
        super().__init__(
            f"Cannot read non-text file (MIME type: {mime_type}). "
            "Use pull_document to download binary files."
        )


class SemanticSearchDisabledError(ContextStoreError):
    """Raised when semantic search is not enabled on the server."""

    def __init__(self):
        super().__init__("Semantic search is not enabled on the server")
