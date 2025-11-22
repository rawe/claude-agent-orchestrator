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
                checksum TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
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

        self.conn.commit()

    def insert_document(self, metadata: DocumentMetadata):
        """Insert document metadata and tags into database."""
        cursor = self.conn.cursor()

        # Insert into documents table
        cursor.execute("""
            INSERT INTO documents (
                id, filename, content_type, size_bytes, checksum,
                storage_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.id,
            metadata.filename,
            metadata.content_type,
            metadata.size_bytes,
            metadata.checksum,
            metadata.storage_path,
            metadata.created_at.isoformat(),
            metadata.updated_at.isoformat()
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
        cursor = self.conn.cursor()

        # Get document metadata
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Get associated tags
        cursor.execute("SELECT tag FROM document_tags WHERE document_id = ?", (doc_id,))
        tags = [tag_row['tag'] for tag_row in cursor.fetchall()]

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
            tags=tags
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
        results = []
        for row in rows:
            # Get tags for this document
            cursor.execute("SELECT tag FROM document_tags WHERE document_id = ?", (row['id'],))
            tags_list = [tag_row['tag'] for tag_row in cursor.fetchall()]

            results.append(DocumentMetadata(
                id=row['id'],
                filename=row['filename'],
                content_type=row['content_type'],
                size_bytes=row['size_bytes'],
                checksum=row['checksum'],
                storage_path=row['storage_path'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                tags=tags_list
            ))

        return results

    def delete_document(self, doc_id: str) -> bool:
        """Delete document metadata. CASCADE automatically deletes tags."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.commit()

        return cursor.rowcount > 0
