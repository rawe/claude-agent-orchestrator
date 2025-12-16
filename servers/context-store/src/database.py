"""Database layer for metadata persistence (Block 02 implementation)"""

import sqlite3
from datetime import datetime
from typing import List, Optional
from .models import DocumentMetadata


class DocumentDatabase:
    """Manages document metadata in SQLite database."""

    def __init__(self, db_path: str):
        """Initialize database connection and create schema."""
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_database()

    def _init_database(self):
        """Create database schema if it doesn't exist."""
        cursor = self.conn.cursor()

        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                checksum TEXT,
                storage_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            )
        """)

        # Create document_tags table with cascade delete
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_tags (
                document_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (document_id, tag),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags ON document_tags(tag)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_filename ON documents(filename)")

        # Create document_relations table for bidirectional document linking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                related_document_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (related_document_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE(document_id, related_document_id, relation_type)
            )
        """)

        # Create indexes for relation queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_document_id ON document_relations(document_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_related_document_id ON document_relations(related_document_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON document_relations(relation_type)")

        self.conn.commit()

    def insert_document(self, metadata: DocumentMetadata):
        """Insert document metadata and tags into database."""
        import json
        cursor = self.conn.cursor()

        # Serialize metadata dict to JSON string
        metadata_json = json.dumps(metadata.metadata) if metadata.metadata else None

        # Insert into documents table
        cursor.execute("""
            INSERT INTO documents (
                id, filename, content_type, size_bytes, checksum,
                storage_path, created_at, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.id,
            metadata.filename,
            metadata.content_type,
            metadata.size_bytes,
            metadata.checksum,
            metadata.storage_path,
            metadata.created_at.isoformat(),
            metadata.updated_at.isoformat(),
            metadata_json
        ))

        # Insert tags
        for tag in metadata.tags:
            cursor.execute("""
                INSERT INTO document_tags (document_id, tag)
                VALUES (?, ?)
            """, (metadata.id, tag))

        self.conn.commit()

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Retrieve document metadata by ID."""
        import json
        cursor = self.conn.cursor()

        # Get document metadata
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Get associated tags
        cursor.execute("SELECT tag FROM document_tags WHERE document_id = ?", (doc_id,))
        tags = [tag_row['tag'] for tag_row in cursor.fetchall()]

        # Deserialize metadata JSON string to dict
        metadata_dict = {}
        if row['metadata']:
            try:
                metadata_dict = json.loads(row['metadata'])
            except json.JSONDecodeError:
                metadata_dict = {}

        # Construct DocumentMetadata
        return DocumentMetadata(
            id=row['id'],
            filename=row['filename'],
            content_type=row['content_type'],
            size_bytes=row['size_bytes'],
            checksum=row['checksum'],
            storage_path=row['storage_path'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            tags=tags,
            metadata=metadata_dict
        )

    def query_documents(
        self,
        filename: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[DocumentMetadata]:
        """Query documents with optional filters. Multiple tags use AND logic."""
        cursor = self.conn.cursor()

        # Build query based on filters
        if tags and len(tags) > 0:
            # Tag filtering with AND logic (document must have ALL tags)
            placeholders = ','.join(['?' for _ in tags])
            query = f"""
                SELECT DISTINCT d.* FROM documents d
                JOIN document_tags dt ON d.id = dt.document_id
                WHERE dt.tag IN ({placeholders})
            """
            params = list(tags)

            # Add filename filter if provided
            if filename:
                query += " AND d.filename LIKE ?"
                params.append(f"%{filename}%")

            # Group by and ensure all tags match
            query += f"""
                GROUP BY d.id
                HAVING COUNT(DISTINCT dt.tag) = ?
            """
            params.append(len(tags))

        elif filename:
            # Filename-only filtering
            query = "SELECT * FROM documents WHERE filename LIKE ?"
            params = [f"%{filename}%"]

        else:
            # No filters - return all
            query = "SELECT * FROM documents"
            params = []

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Build DocumentMetadata objects
        import json
        results = []
        for row in rows:
            # Get tags for this document
            cursor.execute("SELECT tag FROM document_tags WHERE document_id = ?", (row['id'],))
            tags_list = [tag_row['tag'] for tag_row in cursor.fetchall()]

            # Deserialize metadata JSON string to dict
            metadata_dict = {}
            if row['metadata']:
                try:
                    metadata_dict = json.loads(row['metadata'])
                except json.JSONDecodeError:
                    metadata_dict = {}

            results.append(DocumentMetadata(
                id=row['id'],
                filename=row['filename'],
                content_type=row['content_type'],
                size_bytes=row['size_bytes'],
                checksum=row['checksum'],
                storage_path=row['storage_path'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                tags=tags_list,
                metadata=metadata_dict
            ))

        return results

    def delete_document(self, doc_id: str) -> bool:
        """Delete document metadata. CASCADE automatically deletes tags and relations."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.commit()

        return cursor.rowcount > 0

    def update_document(
        self,
        doc_id: str,
        size_bytes: Optional[int] = None,
        checksum: Optional[str] = None,
        updated_at: Optional[datetime] = None
    ) -> bool:
        """Update document metadata fields.

        Args:
            doc_id: Document ID to update
            size_bytes: New size in bytes (optional)
            checksum: New checksum value (optional)
            updated_at: New updated timestamp (optional, defaults to now)

        Returns:
            True if document was updated, False if not found
        """
        # Build dynamic update query based on provided fields
        updates = []
        params = []

        if size_bytes is not None:
            updates.append("size_bytes = ?")
            params.append(size_bytes)

        if checksum is not None:
            updates.append("checksum = ?")
            params.append(checksum)

        # Always update updated_at
        updates.append("updated_at = ?")
        if updated_at is not None:
            params.append(updated_at.isoformat())
        else:
            params.append(datetime.now().isoformat())

        if not updates:
            return False

        params.append(doc_id)
        query = f"UPDATE documents SET {', '.join(updates)} WHERE id = ?"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()

        return cursor.rowcount > 0

    # ==================== Relation Methods ====================

    def create_relation(
        self,
        document_id: str,
        related_document_id: str,
        relation_type: str,
        note: Optional[str] = None
    ) -> int:
        """Create a single relation row. Returns the relation ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO document_relations (document_id, related_document_id, relation_type, note)
            VALUES (?, ?, ?, ?)
        """, (document_id, related_document_id, relation_type, note))
        self.conn.commit()
        return cursor.lastrowid

    def get_relation(self, relation_id: int) -> Optional[dict]:
        """Get a single relation by ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, document_id, related_document_id, relation_type, note, created_at, updated_at
            FROM document_relations WHERE id = ?
        """, (relation_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "document_id": row["document_id"],
            "related_document_id": row["related_document_id"],
            "relation_type": row["relation_type"],
            "note": row["note"],
            "created_at": datetime.fromisoformat(row["created_at"]),
            "updated_at": datetime.fromisoformat(row["updated_at"])
        }

    def get_document_relations(self, document_id: str) -> List[dict]:
        """Get all relations for a document."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, document_id, related_document_id, relation_type, note, created_at, updated_at
            FROM document_relations WHERE document_id = ?
        """, (document_id,))
        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "document_id": row["document_id"],
                "related_document_id": row["related_document_id"],
                "relation_type": row["relation_type"],
                "note": row["note"],
                "created_at": datetime.fromisoformat(row["created_at"]),
                "updated_at": datetime.fromisoformat(row["updated_at"])
            }
            for row in rows
        ]

    def get_relations_batch(self, document_ids: List[str]) -> dict[str, List[dict]]:
        """Get all relations for multiple documents in one query.

        Returns a dict mapping document_id -> list of relation dicts.
        """
        if not document_ids:
            return {}

        cursor = self.conn.cursor()
        placeholders = ','.join(['?' for _ in document_ids])
        cursor.execute(f"""
            SELECT id, document_id, related_document_id, relation_type, note, created_at, updated_at
            FROM document_relations WHERE document_id IN ({placeholders})
        """, document_ids)
        rows = cursor.fetchall()

        # Group by document_id
        result: dict[str, List[dict]] = {doc_id: [] for doc_id in document_ids}
        for row in rows:
            relation = {
                "id": row["id"],
                "document_id": row["document_id"],
                "related_document_id": row["related_document_id"],
                "relation_type": row["relation_type"],
                "note": row["note"],
                "created_at": datetime.fromisoformat(row["created_at"]),
                "updated_at": datetime.fromisoformat(row["updated_at"])
            }
            result[row["document_id"]].append(relation)

        return result

    def find_relation(
        self,
        document_id: str,
        related_document_id: str,
        relation_type: str
    ) -> Optional[dict]:
        """Find a specific relation by document IDs and type."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, document_id, related_document_id, relation_type, note, created_at, updated_at
            FROM document_relations
            WHERE document_id = ? AND related_document_id = ? AND relation_type = ?
        """, (document_id, related_document_id, relation_type))
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "document_id": row["document_id"],
            "related_document_id": row["related_document_id"],
            "relation_type": row["relation_type"],
            "note": row["note"],
            "created_at": datetime.fromisoformat(row["created_at"]),
            "updated_at": datetime.fromisoformat(row["updated_at"])
        }

    def update_relation_note(self, relation_id: int, note: Optional[str]) -> bool:
        """Update the note for a relation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE document_relations
            SET note = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (note, relation_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_relation(self, relation_id: int) -> bool:
        """Delete a single relation by ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM document_relations WHERE id = ?", (relation_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_child_document_ids(self, document_id: str) -> List[str]:
        """Get IDs of all child documents (where this document is the parent).

        A document is a parent when it has relations with relation_type='child',
        meaning it stores "related_document_id is my child".
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT related_document_id FROM document_relations
            WHERE document_id = ? AND relation_type = 'child'
        """, (document_id,))
        rows = cursor.fetchall()
        return [row["related_document_id"] for row in rows]

    def document_exists(self, document_id: str) -> bool:
        """Check if a document exists."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM documents WHERE id = ?", (document_id,))
        return cursor.fetchone() is not None
