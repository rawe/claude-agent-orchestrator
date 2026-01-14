"""MCP tool definitions for the Context Store server.

Design Decision: Raw Content vs JSON Responses
----------------------------------------------
FastMCP automatically wraps non-object returns (like strings) in {"result": value}.
This is problematic for document content because:

1. Token overhead - JSON wrapper adds tokens for large documents
2. Readability - LLMs see escaped content (\\n instead of newlines)
3. Usability - Content requires mental extraction from JSON structure

Solution: For READ operations (doc_read), we use ToolResult with TextContent
to return raw text without JSON wrapping. For WRITE/MODIFY operations, we
return JSON because the metadata (document ID, size, checksum) is valuable
for verification and follow-up operations.

References:
- FastMCP Tool Operations: https://gofastmcp.com/clients/tools
- ToolResult allows full control over content vs structured_content
"""

import json
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent
from pydantic import Field

from .http_client import ContextStoreClient
from .exceptions import ContextStoreError


def register_tools(mcp: FastMCP, client: ContextStoreClient) -> None:
    """Register all Context Store tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: ContextStoreClient instance for HTTP operations
    """

    @mcp.tool()
    async def doc_push(
        file_path: str = Field(
            description="Absolute path to the file to upload",
        ),
        name: Optional[str] = Field(
            default=None,
            description="Custom document name (optional, defaults to filename)",
        ),
        tags: Optional[str] = Field(
            default=None,
            description="Comma-separated tags for categorization",
        ),
        description: Optional[str] = Field(
            default=None,
            description="Human-readable description of the document",
        ),
    ) -> str:
        """Upload a document to the Context Store.

        Stores a file with optional metadata (name, tags, description) for later retrieval.
        Tags enable filtering documents by category. Use comma-separated values for multiple tags.

        Returns:
            JSON with document metadata including id, filename, tags, url

        Example:
            doc_push(file_path="/home/user/api-spec.yaml", tags="api,openapi", description="API specification v2")
        """
        # LIMITATION: This tool reads from the MCP server's filesystem.
        # Works in stdio mode (shared filesystem) and HTTP mode on localhost.
        # Does NOT work when HTTP server runs on a remote host.
        # See ../README.md "Known Limitations" for details and workarounds.
        if not Path(file_path).is_absolute():
            return "Error: file_path must be an absolute path"

        try:
            tags_list = [t.strip() for t in tags.split(",")] if tags else None
            result = await client.push_document(
                file_path=file_path,
                name=name,
                tags=tags_list,
                description=description,
            )
            return json.dumps(result)
        except FileNotFoundError as e:
            return f"Error: {e}"
        except ContextStoreError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def doc_create(
        filename: str = Field(
            description="Document filename (e.g., 'notes.md'). Used to infer content type.",
        ),
        tags: Optional[str] = Field(
            default=None,
            description="Comma-separated tags for categorization",
        ),
        description: Optional[str] = Field(
            default=None,
            description="Human-readable description of the document",
        ),
    ) -> str:
        """Create a placeholder document in the Context Store.

        Creates an empty document with metadata. Use doc_write to add content later.
        This two-phase approach lets you reserve document IDs before generating content.

        Returns:
            JSON with document metadata: id, filename, content_type, size_bytes (0), url

        Example:
            doc_create(filename="architecture.md", tags="design,mvp", description="System overview")
        """
        try:
            tags_list = [t.strip() for t in tags.split(",")] if tags else None
            result = await client.create_document(
                filename=filename,
                tags=tags_list,
                description=description,
            )
            return json.dumps(result)
        except ContextStoreError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def doc_write(
        document_id: str = Field(
            description="The document ID to write to",
        ),
        content: str = Field(
            description="The full content to write (replaces existing content)",
        ),
    ) -> str:
        """Write content to an existing document (full replacement).

        Replaces the entire content of a document. Use after doc_create to fill
        placeholder documents, or to update existing document content.

        Returns:
            JSON with updated document metadata: id, filename, size_bytes, checksum

        Example:
            doc_write(document_id="doc_abc123", content="# My Document\\n\\nContent here...")
        """
        try:
            result = await client.write_document_content(
                document_id=document_id,
                content=content,
            )
            return json.dumps(result)
        except ContextStoreError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def doc_edit(
        document_id: str = Field(
            description="The document ID to edit",
        ),
        new_string: str = Field(
            description="Replacement text, or text to insert (offset mode)",
        ),
        old_string: Optional[str] = Field(
            default=None,
            description="Text to find and replace (string replacement mode)",
        ),
        replace_all: bool = Field(
            default=False,
            description="Replace all occurrences (only for string replacement mode)",
        ),
        offset: Optional[int] = Field(
            default=None,
            description="Character position for offset-based edit",
        ),
        length: Optional[int] = Field(
            default=None,
            description="Characters to replace at offset (0 = insert)",
        ),
    ) -> str:
        """Edit document content surgically without full replacement.

        Two modes:
        1. String replacement: Provide old_string + new_string (like Claude's Edit tool)
        2. Offset-based: Provide offset + new_string (+ optional length)

        String replacement follows Claude Edit semantics:
        - old_string must be found in document (error if not)
        - old_string must be unique unless replace_all=true (error if ambiguous)

        Returns:
            JSON with updated document metadata and edit details (replacements_made or edit_range)

        Examples:
            # String replacement (unique match required)
            doc_edit(document_id="doc_abc", old_string="old text", new_string="new text")

            # Replace all occurrences
            doc_edit(document_id="doc_abc", old_string="TODO", new_string="DONE", replace_all=True)

            # Insert at position
            doc_edit(document_id="doc_abc", offset=100, new_string="inserted text")

            # Replace range
            doc_edit(document_id="doc_abc", offset=100, length=50, new_string="replacement")

            # Delete range
            doc_edit(document_id="doc_abc", offset=100, length=50, new_string="")
        """
        try:
            result = await client.edit_document_content(
                document_id=document_id,
                new_string=new_string,
                old_string=old_string,
                replace_all=replace_all,
                offset=offset,
                length=length,
            )
            return json.dumps(result)
        except ContextStoreError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def doc_query(
        name: Optional[str] = Field(
            default=None,
            description="Filename pattern to filter by",
        ),
        tags: Optional[str] = Field(
            default=None,
            description="Comma-separated tags (AND logic)",
        ),
        limit: Optional[int] = Field(
            default=None,
            description="Maximum number of results",
        ),
        include_relations: bool = Field(
            default=False,
            description="Include document relations in response",
        ),
    ) -> str:
        """Query documents in the Context Store by name pattern and/or tags.

        Searches for documents matching the specified criteria. Multiple tags use AND logic
        (all tags must match). Use this for structured filtering when you know the document
        metadata.

        Returns:
            JSON array of matching documents with metadata (id, filename, tags, size, dates)

        Examples:
            doc_query(tags="api,v2")           # Find docs with BOTH tags
            doc_query(name="spec")             # Find docs with "spec" in filename
            doc_query(include_relations=True)  # List all with relations
        """
        try:
            tags_list = [t.strip() for t in tags.split(",")] if tags else None
            result = await client.query_documents(
                name=name,
                tags=tags_list,
                limit=limit,
                include_relations=include_relations,
            )
            return json.dumps(result)
        except ContextStoreError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def doc_search(
        query: str = Field(
            description="Natural language search query",
        ),
        limit: Optional[int] = Field(
            default=None,
            description="Maximum number of results",
        ),
        include_relations: bool = Field(
            default=False,
            description="Include document relations in response",
        ),
    ) -> str:
        """Semantic search for documents by natural language query.

        Finds documents by meaning, not just keywords. Returns relevant sections
        with character offsets for partial reading. Use this when you don't know
        exact tags/names but know what content you're looking for.

        Returns:
            JSON with search results including document_id, filename, sections with scores

        Example:
            doc_search(query="how to authenticate API requests")

        Note: Requires semantic search to be enabled on the server.
        """
        try:
            result = await client.search_documents(
                query=query,
                limit=limit,
                include_relations=include_relations,
            )
            return json.dumps(result)
        except ContextStoreError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def doc_info(
        document_id: str = Field(
            description="The document ID",
        ),
    ) -> str:
        """Get metadata and relations for a specific document without downloading content.

        Retrieves document metadata (size, type, tags, dates) and relations without transferring
        the file content. Use this to check document details and see linked documents.

        Returns:
            JSON with document metadata: id, filename, content_type, size_bytes, tags, created_at, updated_at
            Plus relations object with parent/child/related document links
        """
        try:
            result = await client.get_document_info(document_id=document_id)
            return json.dumps(result)
        except ContextStoreError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def doc_read(
        document_id: str = Field(
            description="The document ID",
        ),
        offset: Optional[int] = Field(
            default=None,
            description="Starting character position",
        ),
        limit: Optional[int] = Field(
            default=None,
            description="Number of characters to read",
        ),
    ) -> ToolResult:
        """Read text content of a document directly to output.

        Streams document content for text-based files. Supports partial reads using
        offset and limit parameters - useful for large documents or when you only need
        a specific section (e.g., from semantic search results).

        Returns:
            Raw text content of the document (or partial content if offset/limit specified)

        Examples:
            doc_read(document_id="doc_abc123")                         # Full document
            doc_read(document_id="doc_abc123", offset=2000, limit=500) # Characters 2000-2500

        Note: Only works with text-based files (text/*, application/json, etc.)
        """
        # Implementation: Returns ToolResult with TextContent to avoid FastMCP's
        # automatic JSON wrapping ({"result": "..."}). See module docstring for
        # full rationale on raw content vs JSON responses.
        try:
            content, _, _ = await client.read_document(
                document_id=document_id,
                offset=offset,
                limit=limit,
            )
            return ToolResult(content=[TextContent(type="text", text=content)])
        except ContextStoreError as e:
            return ToolResult(content=[TextContent(type="text", text=f"Error: {e}")])

    @mcp.tool()
    async def doc_pull(
        document_id: str = Field(
            description="The document ID",
        ),
        output_path: str = Field(
            description="Absolute path where to save the file",
        ),
    ) -> str:
        """Download a document to the local filesystem.

        Saves the document to the specified path. Use this when you need the actual
        file on disk (e.g., for processing, editing, or binary files).

        Returns:
            JSON with download result: file_path, size_bytes

        Example:
            doc_pull(document_id="doc_abc123", output_path="/home/user/downloads/spec.yaml")
        """
        # LIMITATION: This tool writes to the MCP server's filesystem.
        # Works in stdio mode (shared filesystem) and HTTP mode on localhost.
        # Does NOT work when HTTP server runs on a remote host.
        # See ../README.md "Known Limitations" for details and workarounds.
        if not Path(output_path).is_absolute():
            return "Error: output_path must be an absolute path"

        try:
            content, filename = await client.pull_document(document_id=document_id)

            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(content)

            result = {
                "file_path": str(output_file),
                "size_bytes": len(content),
                "filename": filename,
            }
            return json.dumps(result)
        except ContextStoreError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def doc_delete(
        document_id: str = Field(
            description="The document ID to delete",
        ),
    ) -> str:
        """Delete a document from the Context Store.

        Permanently removes the document and its metadata. This action cannot be undone.
        Deleting a parent document cascades to delete all child documents.

        Returns:
            JSON confirmation with success status and deleted document ID
        """
        # Implementation note: Server also removes document from semantic search
        # index if enabled. This is transparent to the caller.
        try:
            result = await client.delete_document(document_id=document_id)
            return json.dumps(result)
        except ContextStoreError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def doc_link(
        types: bool = Field(
            default=False,
            description="List available relation types",
        ),
        create_from: Optional[str] = Field(
            default=None,
            description="Source document ID for creating relation",
        ),
        create_to: Optional[str] = Field(
            default=None,
            description="Target document ID for creating relation",
        ),
        relation_type: Optional[str] = Field(
            default=None,
            description="Relation type from types list (required for create)",
        ),
        from_to_note: Optional[str] = Field(
            default=None,
            description="Note on edge from source to target (source's note about target)",
        ),
        to_from_note: Optional[str] = Field(
            default=None,
            description="Note on edge from target to source (target's note about source)",
        ),
        update_id: Optional[str] = Field(
            default=None,
            description="Relation ID to update",
        ),
        remove_id: Optional[str] = Field(
            default=None,
            description="Relation ID to remove",
        ),
        note: Optional[str] = Field(
            default=None,
            description="New note text (for update)",
        ),
    ) -> str:
        """Manage document relations (parent-child or peer links).

        Create, update, or remove bidirectional relations between documents.
        Use types=True first to discover available relation types.

        Actions (mutually exclusive):
            types=True: List available relation types
            create_from + create_to + relation_type: Create a relation
            update_id + note: Update a relation's note
            remove_id: Remove a relation (both directions)

        Returns:
            JSON with operation result
        """
        try:
            if types:
                result = await client.get_relation_definitions()
                return json.dumps(result)

            elif create_from and create_to:
                if not relation_type:
                    return "Error: relation_type is required when creating a relation"
                result = await client.create_relation(
                    from_document_id=create_from,
                    to_document_id=create_to,
                    definition=relation_type,
                    from_to_note=from_to_note,
                    to_from_note=to_from_note,
                )
                return json.dumps(result)

            elif update_id:
                result = await client.update_relation(
                    relation_id=update_id,
                    note=note,
                )
                return json.dumps(result)

            elif remove_id:
                result = await client.delete_relation(relation_id=remove_id)
                return json.dumps(result)

            else:
                return "Error: No action specified. Use types=True, create_from+create_to, update_id, or remove_id"

        except ContextStoreError as e:
            return f"Error: {e}"
