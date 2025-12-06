from pydantic import BaseModel, Field
from dataclasses import dataclass
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Internal document metadata with storage details."""
    id: str
    filename: str
    content_type: str
    size_bytes: int
    checksum: str = ""  # SHA256 checksum for integrity verification
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


class RelationInfo(BaseModel):
    """Relation info for inclusion in document responses."""
    id: str
    related_document_id: str
    relation_type: str
    note: str | None


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
    url: str  # Fully qualified URL to retrieve the document
    relations: dict[str, list[RelationInfo]] | None = None  # Grouped by relation_type, optional


class DeleteResponse(BaseModel):
    """Response model for document deletion."""
    success: bool
    message: str
    document_id: str


class SectionInfo(BaseModel):
    """Information about a matching section in a document."""
    score: float
    offset: int
    limit: int


class SearchResultItem(BaseModel):
    """A single document result from semantic search."""
    document_id: str
    filename: str
    document_url: str
    sections: list[SectionInfo]
    relations: dict[str, list[RelationInfo]] | None = None  # Grouped by relation_type, optional


class SearchResponse(BaseModel):
    """Response model for semantic search."""
    query: str
    results: list[SearchResultItem]


# ==================== Relation Models ====================

@dataclass(frozen=True)
class RelationDefinition:
    """
    Defines a relation with its two sides for bidirectional linking.
    Immutable to ensure consistency.
    """
    name: str           # API identifier: "parent-child", "related"
    description: str    # Human-readable description
    from_type: str      # DB value for first document: "parent", "related"
    to_type: str        # DB value for second document: "child", "related"


class RelationDefinitions:
    """
    Central registry of all relation definitions.
    Use these constants instead of magic strings.
    """

    PARENT_CHILD = RelationDefinition(
        name="parent-child",
        description="Hierarchical relation where parent owns children. Cascade delete enabled.",
        from_type="child",
        to_type="parent"
    )

    RELATED = RelationDefinition(
        name="related",
        description="Peer relation between related documents.",
        from_type="related",
        to_type="related"
    )

    PREDECESSOR_SUCCESSOR = RelationDefinition(
        name="predecessor-successor",
        description="Sequential ordering relation.",
        from_type="successor",
        to_type="predecessor"
    )

    # Registry for lookups (initialized lazily)
    _BY_NAME: dict[str, RelationDefinition] = {}
    _BY_TYPE: dict[str, RelationDefinition] = {}

    @classmethod
    def _init_registry(cls):
        """Initialize lookup mappings."""
        all_definitions = [cls.PARENT_CHILD, cls.RELATED, cls.PREDECESSOR_SUCCESSOR]
        cls._BY_NAME = {d.name: d for d in all_definitions}
        cls._BY_TYPE = {}
        for d in all_definitions:
            cls._BY_TYPE[d.from_type] = d
            cls._BY_TYPE[d.to_type] = d

    @classmethod
    def get_by_name(cls, name: str) -> RelationDefinition | None:
        """Lookup by API name (e.g., 'parent-child'). Returns None if not found."""
        if not cls._BY_NAME:
            cls._init_registry()
        return cls._BY_NAME.get(name)

    @classmethod
    def get_by_type(cls, relation_type: str) -> RelationDefinition | None:
        """Lookup by database relation_type value (e.g., 'parent'). Returns None if not found."""
        if not cls._BY_TYPE:
            cls._init_registry()
        return cls._BY_TYPE.get(relation_type)

    @classmethod
    def get_inverse_type(cls, relation_type: str) -> str | None:
        """Get the inverse relation_type for bidirectional operations."""
        definition = cls.get_by_type(relation_type)
        if not definition:
            return None
        if relation_type == definition.from_type:
            return definition.to_type
        return definition.from_type

    @classmethod
    def get_all(cls) -> list[RelationDefinition]:
        """Get all available relation definitions."""
        return [cls.PARENT_CHILD, cls.RELATED, cls.PREDECESSOR_SUCCESSOR]


# Initialize registry on module load
RelationDefinitions._init_registry()


# ==================== Relation Pydantic Models ====================

class RelationDefinitionResponse(BaseModel):
    """Available relation definition for API response.

    Note: from_document_is/to_document_is describe what each document IS in the relationship,
    which is the inverse of internal from_type/to_type that describe what each document STORES.
    """
    name: str
    description: str
    from_document_is: str  # What the from_document IS in this relation (e.g., "parent")
    to_document_is: str    # What the to_document IS in this relation (e.g., "child")


class RelationCreateRequest(BaseModel):
    """Request to create a bidirectional relation.

    Mental model:
        [from_doc] ---from_to_note---> [to_doc]
                   <--to_from_note----
    """
    definition: str                      # "parent-child", "related", or "predecessor-successor"
    from_document_id: str                # First document
    to_document_id: str                  # Second document
    from_to_note: str | None = None      # Note on edge from source to target (from_doc's note about to_doc)
    to_from_note: str | None = None      # Note on edge from target to source (to_doc's note about from_doc)


class RelationResponse(BaseModel):
    """Single relation from a document's perspective."""
    id: str                              # String externally, int internally
    document_id: str
    related_document_id: str
    relation_type: str                   # DB value: "parent", "child", "related", "predecessor", "successor"
    note: str | None
    created_at: datetime
    updated_at: datetime


class RelationCreateResponse(BaseModel):
    """Response after creating a bidirectional relation."""
    success: bool
    message: str
    from_relation: RelationResponse
    to_relation: RelationResponse


class RelationUpdateRequest(BaseModel):
    """Update note for an existing relation."""
    note: str | None


class DocumentRelationsResponse(BaseModel):
    """All relations for a document, grouped by relation_type."""
    document_id: str
    relations: dict[str, list[RelationResponse]]  # Grouped by relation_type


class RelationDeleteResponse(BaseModel):
    """Response after deleting a relation."""
    success: bool
    message: str
    deleted_relation_ids: list[str]  # Both sides of bidirectional relation (string externally)


class DeleteResponseWithCascade(BaseModel):
    """Response for document deletion with cascade information."""
    success: bool
    message: str
    deleted_document_ids: list[str]  # All deleted documents including children
