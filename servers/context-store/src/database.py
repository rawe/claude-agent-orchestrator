"""Database layer for metadata persistence using Neo4j graph database."""

import json
import os
from datetime import datetime
from typing import List, Optional

from neo4j import GraphDatabase

from .models import DocumentMetadata


class DocumentDatabase:
    """Manages document metadata in Neo4j graph database."""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """Initialize Neo4j connection and create schema constraints."""
        self._uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD", "context-store-secret")

        self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
        self._init_database()

    def _init_database(self):
        """Create schema constraints and indexes."""
        with self._driver.session() as session:
            # Unique constraint on Document.id
            session.run("""
                CREATE CONSTRAINT document_id_unique IF NOT EXISTS
                FOR (d:Document) REQUIRE d.id IS UNIQUE
            """)
            # Index on filename for faster queries
            session.run("""
                CREATE INDEX document_filename IF NOT EXISTS
                FOR (d:Document) ON (d.filename)
            """)
            # Index on tags for faster tag queries
            session.run("""
                CREATE INDEX document_tags IF NOT EXISTS
                FOR (d:Document) ON (d.tags)
            """)

    def close(self):
        """Close the Neo4j driver connection."""
        self._driver.close()

    def insert_document(self, metadata: DocumentMetadata):
        """Insert document metadata into database."""
        metadata_json = json.dumps(metadata.metadata) if metadata.metadata else None

        with self._driver.session() as session:
            session.run("""
                CREATE (d:Document {
                    id: $id,
                    filename: $filename,
                    content_type: $content_type,
                    size_bytes: $size_bytes,
                    checksum: $checksum,
                    storage_path: $storage_path,
                    created_at: $created_at,
                    updated_at: $updated_at,
                    tags: $tags,
                    metadata: $metadata
                })
            """, {
                "id": metadata.id,
                "filename": metadata.filename,
                "content_type": metadata.content_type,
                "size_bytes": metadata.size_bytes,
                "checksum": metadata.checksum,
                "storage_path": metadata.storage_path,
                "created_at": metadata.created_at.isoformat(),
                "updated_at": metadata.updated_at.isoformat(),
                "tags": metadata.tags,
                "metadata": metadata_json
            })

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Retrieve document metadata by ID."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (d:Document {id: $id})
                RETURN d
            """, {"id": doc_id})

            record = result.single()
            if not record:
                return None

            node = record["d"]
            return self._node_to_metadata(node)

    def _node_to_metadata(self, node) -> DocumentMetadata:
        """Convert a Neo4j node to DocumentMetadata."""
        metadata_dict = {}
        if node.get("metadata"):
            try:
                metadata_dict = json.loads(node["metadata"])
            except json.JSONDecodeError:
                metadata_dict = {}

        tags = list(node.get("tags", []))

        return DocumentMetadata(
            id=node["id"],
            filename=node["filename"],
            content_type=node["content_type"],
            size_bytes=node["size_bytes"],
            checksum=node["checksum"],
            storage_path=node["storage_path"],
            created_at=datetime.fromisoformat(node["created_at"]),
            updated_at=datetime.fromisoformat(node["updated_at"]),
            tags=tags,
            metadata=metadata_dict
        )

    def query_documents(
        self,
        filename: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[DocumentMetadata]:
        """Query documents with optional filters. Multiple tags use AND logic."""
        with self._driver.session() as session:
            # Build query based on filters
            if tags and len(tags) > 0 and filename:
                # Both tags and filename filter
                query = """
                    MATCH (d:Document)
                    WHERE d.filename CONTAINS $filename
                    AND ALL(tag IN $tags WHERE tag IN d.tags)
                    RETURN d
                """
                params = {"filename": filename, "tags": tags}
            elif tags and len(tags) > 0:
                # Tags only filter (AND logic)
                query = """
                    MATCH (d:Document)
                    WHERE ALL(tag IN $tags WHERE tag IN d.tags)
                    RETURN d
                """
                params = {"tags": tags}
            elif filename:
                # Filename only filter
                query = """
                    MATCH (d:Document)
                    WHERE d.filename CONTAINS $filename
                    RETURN d
                """
                params = {"filename": filename}
            else:
                # No filters - return all
                query = "MATCH (d:Document) RETURN d"
                params = {}

            result = session.run(query, params)
            return [self._node_to_metadata(record["d"]) for record in result]

    def delete_document(self, doc_id: str) -> bool:
        """Delete document and all its relationships."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (d:Document {id: $id})
                DETACH DELETE d
                RETURN count(d) AS deleted
            """, {"id": doc_id})

            record = result.single()
            return record["deleted"] > 0

    # ==================== Relation Methods ====================

    def create_relation(
        self,
        document_id: str,
        related_document_id: str,
        relation_type: str,
        note: Optional[str] = None
    ) -> int:
        """Create a relation between documents. Returns a unique relation ID."""
        now = datetime.now().isoformat()

        with self._driver.session() as session:
            # Generate a unique ID for the relationship using timestamp + hash
            result = session.run("""
                MATCH (from:Document {id: $from_id})
                MATCH (to:Document {id: $to_id})
                CREATE (from)-[r:RELATES_TO {
                    relation_type: $relation_type,
                    note: $note,
                    created_at: $created_at,
                    updated_at: $updated_at
                }]->(to)
                RETURN elementId(r) AS rel_id
            """, {
                "from_id": document_id,
                "to_id": related_document_id,
                "relation_type": relation_type,
                "note": note,
                "created_at": now,
                "updated_at": now
            })

            record = result.single()
            # Neo4j elementId returns a string, we'll use a hash for integer ID
            return self._element_id_to_int(record["rel_id"])

    def _element_id_to_int(self, element_id: str) -> int:
        """Convert Neo4j element ID to integer for API compatibility."""
        # Use hash of the element ID, masked to positive int
        return abs(hash(element_id)) % (2**31)

    def _get_relation_from_result(self, record) -> dict:
        """Extract relation dict from a query result record."""
        rel = record["r"]
        return {
            "id": self._element_id_to_int(record["rel_id"]),
            "document_id": record["from_id"],
            "related_document_id": record["to_id"],
            "relation_type": rel["relation_type"],
            "note": rel.get("note"),
            "created_at": datetime.fromisoformat(rel["created_at"]),
            "updated_at": datetime.fromisoformat(rel["updated_at"]),
            "_element_id": record["rel_id"]  # Keep for internal use
        }

    def get_relation(self, relation_id: int) -> Optional[dict]:
        """Get a single relation by ID."""
        with self._driver.session() as session:
            # We need to scan relations and find matching hash
            result = session.run("""
                MATCH (from:Document)-[r:RELATES_TO]->(to:Document)
                RETURN r, elementId(r) AS rel_id, from.id AS from_id, to.id AS to_id
            """)

            for record in result:
                if self._element_id_to_int(record["rel_id"]) == relation_id:
                    return self._get_relation_from_result(record)

            return None

    def get_document_relations(self, document_id: str) -> List[dict]:
        """Get all relations for a document (outgoing relations)."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (from:Document {id: $doc_id})-[r:RELATES_TO]->(to:Document)
                RETURN r, elementId(r) AS rel_id, from.id AS from_id, to.id AS to_id
            """, {"doc_id": document_id})

            return [self._get_relation_from_result(record) for record in result]

    def get_relations_batch(self, document_ids: List[str]) -> dict[str, List[dict]]:
        """Get all relations for multiple documents in one query."""
        if not document_ids:
            return {}

        result_dict: dict[str, List[dict]] = {doc_id: [] for doc_id in document_ids}

        with self._driver.session() as session:
            result = session.run("""
                MATCH (from:Document)-[r:RELATES_TO]->(to:Document)
                WHERE from.id IN $doc_ids
                RETURN r, elementId(r) AS rel_id, from.id AS from_id, to.id AS to_id
            """, {"doc_ids": document_ids})

            for record in result:
                rel_dict = self._get_relation_from_result(record)
                doc_id = rel_dict["document_id"]
                if doc_id in result_dict:
                    result_dict[doc_id].append(rel_dict)

        return result_dict

    def find_relation(
        self,
        document_id: str,
        related_document_id: str,
        relation_type: str
    ) -> Optional[dict]:
        """Find a specific relation by document IDs and type."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (from:Document {id: $from_id})-[r:RELATES_TO {relation_type: $rel_type}]->(to:Document {id: $to_id})
                RETURN r, elementId(r) AS rel_id, from.id AS from_id, to.id AS to_id
            """, {
                "from_id": document_id,
                "to_id": related_document_id,
                "rel_type": relation_type
            })

            record = result.single()
            if not record:
                return None

            return self._get_relation_from_result(record)

    def update_relation_note(self, relation_id: int, note: Optional[str]) -> bool:
        """Update the note for a relation."""
        # First find the relation to get its element ID
        relation = self.get_relation(relation_id)
        if not relation:
            return False

        now = datetime.now().isoformat()

        with self._driver.session() as session:
            result = session.run("""
                MATCH (from:Document {id: $from_id})-[r:RELATES_TO {relation_type: $rel_type}]->(to:Document {id: $to_id})
                SET r.note = $note, r.updated_at = $updated_at
                RETURN count(r) AS updated
            """, {
                "from_id": relation["document_id"],
                "to_id": relation["related_document_id"],
                "rel_type": relation["relation_type"],
                "note": note,
                "updated_at": now
            })

            record = result.single()
            return record["updated"] > 0

    def delete_relation(self, relation_id: int) -> bool:
        """Delete a single relation by ID."""
        # First find the relation to get its element ID
        relation = self.get_relation(relation_id)
        if not relation:
            return False

        with self._driver.session() as session:
            result = session.run("""
                MATCH (from:Document {id: $from_id})-[r:RELATES_TO {relation_type: $rel_type}]->(to:Document {id: $to_id})
                DELETE r
                RETURN count(r) AS deleted
            """, {
                "from_id": relation["document_id"],
                "to_id": relation["related_document_id"],
                "rel_type": relation["relation_type"]
            })

            record = result.single()
            return record["deleted"] > 0

    def get_child_document_ids(self, document_id: str) -> List[str]:
        """Get IDs of all child documents (where this document is the parent).

        A document is a parent when it has relations with relation_type='child',
        meaning it stores "related_document_id is my child".
        """
        with self._driver.session() as session:
            result = session.run("""
                MATCH (parent:Document {id: $doc_id})-[r:RELATES_TO {relation_type: 'child'}]->(child:Document)
                RETURN child.id AS child_id
            """, {"doc_id": document_id})

            return [record["child_id"] for record in result]

    def document_exists(self, document_id: str) -> bool:
        """Check if a document exists."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (d:Document {id: $id})
                RETURN count(d) AS count
            """, {"id": document_id})

            record = result.single()
            return record["count"] > 0
