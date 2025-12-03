#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.7.0",
#   "fastmcp>=2.0.0",
#   "pydantic>=2.0.0",
# ]
# ///
"""
Context Store MCP Server

Provides MCP tools to interact with the Context Store document management system.
Documents can be stored, queried, searched semantically, and retrieved.

Usage:
    # stdio mode (default, for Claude Desktop/CLI)
    uv run context-store-mcp.py

    # HTTP mode (for network access)
    uv run context-store-mcp.py --http-mode
    uv run context-store-mcp.py --http-mode --port 9501
    uv run context-store-mcp.py --http-mode --host 0.0.0.0 --port 9501

Environment Variables:
    CONTEXT_STORE_COMMAND_PATH - Optional: Path to commands directory (auto-discovered if not set)
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal, Optional

from fastmcp import FastMCP
from pydantic import Field, field_validator

# Auto-discover commands directory if not set
SCRIPT_DIR = Path(__file__).parent.resolve()
if "CONTEXT_STORE_COMMAND_PATH" not in os.environ:
    PROJECT_ROOT = SCRIPT_DIR.parent.parent
    COMMANDS_DIR = PROJECT_ROOT / "plugins" / "context-store" / "skills" / "context-store" / "commands"
    os.environ["CONTEXT_STORE_COMMAND_PATH"] = str(COMMANDS_DIR)

COMMAND_PATH = Path(os.environ["CONTEXT_STORE_COMMAND_PATH"])


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


def format_response(stdout: str, stderr: str, exit_code: int) -> str:
    """Format command output as response string."""
    if exit_code != 0:
        return f"Error: {stderr or stdout}"
    return stdout


# --- FastMCP Server ---

mcp = FastMCP(
    "context-store-mcp-server",
    instructions="""Context Store MCP Server - Document management system.

Use this server to:
- Store documents with metadata and tags
- Query documents by name or tags
- Semantic search for documents by meaning
- Read document content (full or partial)
- Download documents to local filesystem
- Manage document relations (parent-child, peer links)
""",
)


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
    if not Path(file_path).is_absolute():
        return "Error: file_path must be an absolute path"

    args = [file_path]
    if name:
        args.extend(["--name", name])
    if tags:
        args.extend(["--tags", tags])
    if description:
        args.extend(["--description", description])

    stdout, stderr, code = await run_command("doc-push", args)
    return format_response(stdout, stderr, code)


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
    args = []
    if name:
        args.extend(["--name", name])
    if tags:
        args.extend(["--tags", tags])
    if limit:
        args.extend(["--limit", str(limit)])
    if include_relations:
        args.append("--include-relations")

    stdout, stderr, code = await run_command("doc-query", args)
    return format_response(stdout, stderr, code)


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

    Uses AI embeddings to find documents by meaning, not just keywords. Returns
    relevant sections with character offsets for partial reading. Use this when
    you don't know exact tags/names but know what content you're looking for.

    Returns:
        JSON with search results including document_id, filename, sections with scores

    Example:
        doc_search(query="how to authenticate API requests")

    Note: Requires semantic search to be enabled on the Context Store server.
    """
    args = [query]
    if limit:
        args.extend(["--limit", str(limit)])
    if include_relations:
        args.append("--include-relations")

    stdout, stderr, code = await run_command("doc-search", args)
    return format_response(stdout, stderr, code)


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
    stdout, stderr, code = await run_command("doc-info", [document_id])
    return format_response(stdout, stderr, code)


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
) -> str:
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
    args = [document_id]
    if offset is not None:
        args.extend(["--offset", str(offset)])
    if limit is not None:
        args.extend(["--limit", str(limit)])

    stdout, stderr, code = await run_command("doc-read", args)
    return format_response(stdout, stderr, code)


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
    if not Path(output_path).is_absolute():
        return "Error: output_path must be an absolute path"

    args = [document_id, "-o", output_path]
    stdout, stderr, code = await run_command("doc-pull", args)
    return format_response(stdout, stderr, code)


@mcp.tool()
async def doc_delete(
    document_id: str = Field(
        description="The document ID to delete",
    ),
) -> str:
    """Delete a document from the Context Store.

    Permanently removes the document and its metadata. This action cannot be undone.
    Also removes the document from semantic search index if enabled.
    Note: Deleting a parent document cascades to delete all child documents.

    Returns:
        JSON confirmation with success status and deleted document ID
    """
    stdout, stderr, code = await run_command("doc-delete", [document_id])
    return format_response(stdout, stderr, code)


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
    from_note: Optional[str] = Field(
        default=None,
        description="Note from source document's perspective",
    ),
    to_note: Optional[str] = Field(
        default=None,
        description="Note from target document's perspective",
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
    args = []
    if types:
        args.append("--types")
    elif create_from and create_to:
        args.extend(["--create", create_from, create_to])
        if relation_type:
            args.extend(["--type", relation_type])
        if from_note:
            args.extend(["--from-note", from_note])
        if to_note:
            args.extend(["--to-note", to_note])
    elif update_id:
        args.extend(["--update", update_id])
        if note:
            args.extend(["--note", note])
    elif remove_id:
        args.extend(["--remove", remove_id])

    stdout, stderr, code = await run_command("doc-link", args)
    return format_response(stdout, stderr, code)


# --- Server Runner ---

def run_server(
    transport: Literal["stdio", "streamable-http", "sse"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 9501,
):
    """Run the MCP server with the specified transport.

    Args:
        transport: Transport type - "stdio", "streamable-http", or "sse"
        host: Host to bind to (for HTTP transports)
        port: Port to bind to (for HTTP transports)
    """
    print("Context Store MCP Server", file=sys.stderr)
    print(f"Commands path: {COMMAND_PATH}", file=sys.stderr)
    print(f"Transport: {transport}", file=sys.stderr)

    if transport == "stdio":
        print("Running via stdio", file=sys.stderr)
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        print(f"Running via HTTP at http://{host}:{port}/mcp", file=sys.stderr)
        mcp.run(transport="streamable-http", host=host, port=port)
    elif transport == "sse":
        print(f"Running via SSE at http://{host}:{port}/sse", file=sys.stderr)
        mcp.run(transport="sse", host=host, port=port)
    else:
        raise ValueError(f"Unknown transport: {transport}")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Context Store MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in stdio mode (default, for Claude Desktop/CLI)
  uv run context-store-mcp.py

  # Run in HTTP mode on default port 9501
  uv run context-store-mcp.py --http-mode

  # Run in HTTP mode on custom port
  uv run context-store-mcp.py --http-mode --port 9502

  # Run in HTTP mode, accessible from network
  uv run context-store-mcp.py --http-mode --host 0.0.0.0 --port 9501

  # Run in SSE mode (legacy, for backward compatibility)
  uv run context-store-mcp.py --sse-mode --port 9501
        """,
    )

    parser.add_argument(
        "--http-mode",
        action="store_true",
        help="Run as HTTP server using Streamable HTTP transport (recommended for network access)",
    )

    parser.add_argument(
        "--sse-mode",
        action="store_true",
        help="Run as HTTP server using SSE transport (legacy, for backward compatibility)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to in HTTP/SSE mode (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9501,
        help="Port to bind to in HTTP/SSE mode (default: 9501)",
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    # Determine transport mode
    if args.http_mode and args.sse_mode:
        print("Error: Cannot use both --http-mode and --sse-mode", file=sys.stderr)
        sys.exit(1)

    if args.http_mode:
        transport = "streamable-http"
    elif args.sse_mode:
        transport = "sse"
    else:
        transport = "stdio"

    # Run the server
    try:
        run_server(
            transport=transport,
            host=args.host,
            port=args.port,
        )
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)
    except Exception as error:
        print(f"Server error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
