#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.7.0",
#   "pydantic>=2.0.0",
# ]
# ///
"""
Context Store MCP Server

Provides MCP tools to interact with the Context Store document management system.
Documents can be stored, queried, searched semantically, and retrieved.

Usage:
    uv run context-store-mcp.py

Environment Variables:
    CONTEXT_STORE_COMMAND_PATH - Optional: Path to commands directory (auto-discovered if not set)
"""

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import Server
from pydantic import BaseModel, field_validator

# Auto-discover commands directory if not set
SCRIPT_DIR = Path(__file__).parent.resolve()
if "CONTEXT_STORE_COMMAND_PATH" not in os.environ:
    PROJECT_ROOT = SCRIPT_DIR.parent.parent
    COMMANDS_DIR = PROJECT_ROOT / "plugins" / "context-store" / "skills" / "context-store" / "commands"
    os.environ["CONTEXT_STORE_COMMAND_PATH"] = str(COMMANDS_DIR)

COMMAND_PATH = Path(os.environ["CONTEXT_STORE_COMMAND_PATH"])


# --- Pydantic Schemas ---

class DocPushInput(BaseModel):
    file_path: str
    name: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None

    @field_validator("file_path")
    @classmethod
    def validate_absolute_path(cls, v: str) -> str:
        if not Path(v).is_absolute():
            raise ValueError("file_path must be an absolute path")
        return v


class DocQueryInput(BaseModel):
    name: Optional[str] = None
    tags: Optional[str] = None
    limit: Optional[int] = None
    include_relations: bool = False


class DocSearchInput(BaseModel):
    query: str
    limit: Optional[int] = None
    include_relations: bool = False


class DocInfoInput(BaseModel):
    document_id: str


class DocReadInput(BaseModel):
    document_id: str
    offset: Optional[int] = None
    limit: Optional[int] = None


class DocPullInput(BaseModel):
    document_id: str
    output_path: str

    @field_validator("output_path")
    @classmethod
    def validate_absolute_path(cls, v: str) -> str:
        if not Path(v).is_absolute():
            raise ValueError("output_path must be an absolute path")
        return v


class DocDeleteInput(BaseModel):
    document_id: str


class DocLinkInput(BaseModel):
    types: bool = False
    create_from: Optional[str] = None
    create_to: Optional[str] = None
    update_id: Optional[str] = None
    remove_id: Optional[str] = None
    relation_type: Optional[str] = None
    from_note: Optional[str] = None
    to_note: Optional[str] = None
    note: Optional[str] = None


# --- Command Execution ---

async def run_command(command: str, args: list[str]) -> tuple[str, str, int]:
    """Execute a doc-* command and return stdout, stderr, exit_code."""
    cmd_path = COMMAND_PATH / command
    full_args = ["uv", "run", str(cmd_path)] + args

    process = await asyncio.create_subprocess_exec(
        *full_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return stdout.decode(), stderr.decode(), process.returncode or 0


def make_response(stdout: str, stderr: str, exit_code: int) -> list[types.TextContent]:
    """Create MCP response from command output."""
    if exit_code != 0:
        return [types.TextContent(type="text", text=f"Error: {stderr or stdout}")]
    return [types.TextContent(type="text", text=stdout)]


# --- MCP Server ---

server = Server("context-store-mcp-server")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="doc_push",
            description="""Upload a document to the Context Store.

Stores a file with optional metadata (name, tags, description) for later retrieval.
Tags enable filtering documents by category. Use comma-separated values for multiple tags.

Args:
    file_path (required): Absolute path to the file to upload
    name: Custom document name (defaults to filename)
    tags: Comma-separated tags for categorization (e.g., "api,v2,internal")
    description: Human-readable description of the document

Returns:
    JSON with document metadata including:
    - id: Unique document identifier for retrieval
    - filename: Stored document name
    - tags: Array of assigned tags
    - url: Direct URL to access the document

Example:
    doc_push(file_path="/home/user/api-spec.yaml", tags="api,openapi", description="API specification v2")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file to upload",
                    },
                    "name": {
                        "type": "string",
                        "description": "Custom document name (optional, defaults to filename)",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags for categorization",
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description of the document",
                    },
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="doc_query",
            description="""Query documents in the Context Store by name pattern and/or tags.

Searches for documents matching the specified criteria. Multiple tags use AND logic
(all tags must match). Use this for structured filtering when you know the document
metadata.

Args:
    name: Filename pattern to filter by (partial match supported)
    tags: Comma-separated tags to filter by (AND logic - all must match)
    limit: Maximum number of results to return
    include_relations: Include document relations in response

Returns:
    JSON array of matching documents with metadata (id, filename, tags, size, dates)
    When include_relations=True, each document includes a relations object

Examples:
    doc_query(tags="api,v2")           # Find docs with BOTH tags
    doc_query(name="spec")             # Find docs with "spec" in filename
    doc_query(include_relations=True)  # List all with relations""",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Filename pattern to filter by",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags (AND logic)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                    },
                    "include_relations": {
                        "type": "boolean",
                        "description": "Include document relations in response",
                    },
                },
            },
        ),
        types.Tool(
            name="doc_search",
            description="""Semantic search for documents by natural language query.

Uses AI embeddings to find documents by meaning, not just keywords. Returns
relevant sections with character offsets for partial reading. Use this when
you don't know exact tags/names but know what content you're looking for.

Args:
    query (required): Natural language search query
    limit: Maximum number of documents to return (default 10)
    include_relations: Include document relations in response

Returns:
    JSON with search results including:
    - document_id: ID for retrieval
    - filename: Document name
    - sections: Array of relevant sections with scores and character offsets
    - relations: (when include_relations=True) Document relations by type

Example:
    doc_search(query="how to authenticate API requests")
    doc_search(query="database config", include_relations=True)

Note: Requires semantic search to be enabled on the Context Store server.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                    },
                    "include_relations": {
                        "type": "boolean",
                        "description": "Include document relations in response",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="doc_info",
            description="""Get metadata and relations for a specific document without downloading content.

Retrieves document metadata (size, type, tags, dates) and relations without transferring
the file content. Use this to check document details and see linked documents.

Args:
    document_id (required): The document ID (e.g., "doc_abc123...")

Returns:
    JSON with document metadata: id, filename, content_type, size_bytes, tags, created_at, updated_at
    Plus relations object with parent/child/related document links""",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID",
                    },
                },
                "required": ["document_id"],
            },
        ),
        types.Tool(
            name="doc_read",
            description="""Read text content of a document directly to output.

Streams document content for text-based files. Supports partial reads using
offset and limit parameters - useful for large documents or when you only need
a specific section (e.g., from semantic search results).

Args:
    document_id (required): The document ID
    offset: Starting character position (0-indexed)
    limit: Number of characters to read from offset

Returns:
    Raw text content of the document (or partial content if offset/limit specified)

Examples:
    doc_read(document_id="doc_abc123")                    # Full document
    doc_read(document_id="doc_abc123", offset=2000, limit=500)  # Characters 2000-2500

Note: Only works with text-based files (text/*, application/json, etc.)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting character position",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of characters to read",
                    },
                },
                "required": ["document_id"],
            },
        ),
        types.Tool(
            name="doc_pull",
            description="""Download a document to the local filesystem.

Saves the document to the specified path. Use this when you need the actual
file on disk (e.g., for processing, editing, or binary files).

Args:
    document_id (required): The document ID
    output_path (required): Absolute path where to save the file

Returns:
    JSON with download result: file_path, size_bytes

Example:
    doc_pull(document_id="doc_abc123", output_path="/home/user/downloads/spec.yaml")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Absolute path where to save the file",
                    },
                },
                "required": ["document_id", "output_path"],
            },
        ),
        types.Tool(
            name="doc_delete",
            description="""Delete a document from the Context Store.

Permanently removes the document and its metadata. This action cannot be undone.
Also removes the document from semantic search index if enabled.
Note: Deleting a parent document cascades to delete all child documents.

Args:
    document_id (required): The document ID to delete

Returns:
    JSON confirmation with success status and deleted document ID""",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID to delete",
                    },
                },
                "required": ["document_id"],
            },
        ),
        types.Tool(
            name="doc_link",
            description="""Manage document relations (parent-child or peer links).

Create, update, or remove bidirectional relations between documents.
Use --types first to discover available relation types.

Actions (mutually exclusive):
    types=True: List available relation types
    create_from + create_to + relation_type: Create a relation
    update_id + note: Update a relation's note
    remove_id: Remove a relation (both directions)

Args:
    types: Set True to list available relation types
    create_from: Source document ID for creating relation
    create_to: Target document ID for creating relation
    relation_type: Type from --types (required for create)
    from_note: Note from source document's perspective
    to_note: Note from target document's perspective
    update_id: Relation ID to update
    remove_id: Relation ID to remove
    note: New note text (for update)

Returns:
    JSON with operation result""",
            inputSchema={
                "type": "object",
                "properties": {
                    "types": {
                        "type": "boolean",
                        "description": "List available relation types",
                    },
                    "create_from": {
                        "type": "string",
                        "description": "Source document ID for creating relation",
                    },
                    "create_to": {
                        "type": "string",
                        "description": "Target document ID for creating relation",
                    },
                    "relation_type": {
                        "type": "string",
                        "description": "Relation type from types list (required for create)",
                    },
                    "from_note": {
                        "type": "string",
                        "description": "Note from source document's perspective",
                    },
                    "to_note": {
                        "type": "string",
                        "description": "Note from target document's perspective",
                    },
                    "update_id": {
                        "type": "string",
                        "description": "Relation ID to update",
                    },
                    "remove_id": {
                        "type": "string",
                        "description": "Relation ID to remove",
                    },
                    "note": {
                        "type": "string",
                        "description": "New note text (for update)",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "doc_push":
            params = DocPushInput(**arguments)
            args = [params.file_path]
            if params.name:
                args.extend(["--name", params.name])
            if params.tags:
                args.extend(["--tags", params.tags])
            if params.description:
                args.extend(["--description", params.description])
            stdout, stderr, code = await run_command("doc-push", args)
            return make_response(stdout, stderr, code)

        elif name == "doc_query":
            params = DocQueryInput(**arguments)
            args = []
            if params.name:
                args.extend(["--name", params.name])
            if params.tags:
                args.extend(["--tags", params.tags])
            if params.limit:
                args.extend(["--limit", str(params.limit)])
            if params.include_relations:
                args.append("--include-relations")
            stdout, stderr, code = await run_command("doc-query", args)
            return make_response(stdout, stderr, code)

        elif name == "doc_search":
            params = DocSearchInput(**arguments)
            args = [params.query]
            if params.limit:
                args.extend(["--limit", str(params.limit)])
            if params.include_relations:
                args.append("--include-relations")
            stdout, stderr, code = await run_command("doc-search", args)
            return make_response(stdout, stderr, code)

        elif name == "doc_info":
            params = DocInfoInput(**arguments)
            stdout, stderr, code = await run_command("doc-info", [params.document_id])
            return make_response(stdout, stderr, code)

        elif name == "doc_read":
            params = DocReadInput(**arguments)
            args = [params.document_id]
            if params.offset is not None:
                args.extend(["--offset", str(params.offset)])
            if params.limit is not None:
                args.extend(["--limit", str(params.limit)])
            stdout, stderr, code = await run_command("doc-read", args)
            return make_response(stdout, stderr, code)

        elif name == "doc_pull":
            params = DocPullInput(**arguments)
            args = [params.document_id, "-o", params.output_path]
            stdout, stderr, code = await run_command("doc-pull", args)
            return make_response(stdout, stderr, code)

        elif name == "doc_delete":
            params = DocDeleteInput(**arguments)
            stdout, stderr, code = await run_command("doc-delete", [params.document_id])
            return make_response(stdout, stderr, code)

        elif name == "doc_link":
            params = DocLinkInput(**arguments)
            args = []
            if params.types:
                args.append("--types")
            elif params.create_from and params.create_to:
                args.extend(["--create", params.create_from, params.create_to])
                if params.relation_type:
                    args.extend(["--type", params.relation_type])
                if params.from_note:
                    args.extend(["--from-note", params.from_note])
                if params.to_note:
                    args.extend(["--to-note", params.to_note])
            elif params.update_id:
                args.extend(["--update", params.update_id])
                if params.note:
                    args.extend(["--note", params.note])
            elif params.remove_id:
                args.extend(["--remove", params.remove_id])
            stdout, stderr, code = await run_command("doc-link", args)
            return make_response(stdout, stderr, code)

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except ValueError as e:
        return [types.TextContent(type="text", text=f"Validation error: {e}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {e}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
