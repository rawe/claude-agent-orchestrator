#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.7.0",
#   "fastmcp>=2.0.0",
#   "pydantic>=2.0.0",
#   "httpx>=0.27.0",
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
    CONTEXT_STORE_HOST: Context Store server hostname (default: localhost)
    CONTEXT_STORE_PORT: Context Store server port (default: 8766)
    CONTEXT_STORE_SCHEME: URL scheme (default: http)
"""

import argparse
import sys
from typing import Literal

from fastmcp import FastMCP

# Add lib to path for imports when run as script
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from lib.config import Config
from lib.http_client import ContextStoreClient
from lib.tools import register_tools


# Create the MCP server
mcp = FastMCP(
    "context-store-mcp-server",
    instructions="""Context Store MCP Server - Document management system.

Use this server to:
- Create placeholder documents (doc_create) and write content later (doc_write)
- Store documents with metadata and tags (doc_push for files)
- Query documents by name or tags
- Semantic search for documents by meaning
- Read document content (full or partial)
- Download documents to local filesystem
- Manage document relations (parent-child, peer links)

Workflow for agent-generated content:
1. doc_create(filename="doc.md", tags="...") -> returns document ID
2. doc_write(document_id="doc_xxx", content="...") -> fills the content
""",
)

# Create client and register tools
config = Config()
client = ContextStoreClient(config)
register_tools(mcp, client)


def run_server(
    transport: Literal["stdio", "streamable-http"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 9501,
) -> None:
    """Run the MCP server with the specified transport.

    Args:
        transport: Transport type - "stdio" or "streamable-http"
        host: Host to bind to (for HTTP transport)
        port: Port to bind to (for HTTP transport)
    """
    print("Context Store MCP Server", file=sys.stderr)
    print(f"Context Store URL: {config.base_url}", file=sys.stderr)
    print(f"Transport: {transport}", file=sys.stderr)

    if transport == "stdio":
        print("Running via stdio", file=sys.stderr)
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        print(f"Running via HTTP at http://{host}:{port}/mcp", file=sys.stderr)
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        raise ValueError(f"Unknown transport: {transport}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
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

Environment:
  CONTEXT_STORE_HOST    Server hostname (default: localhost)
  CONTEXT_STORE_PORT    Server port (default: 8766)
  CONTEXT_STORE_SCHEME  URL scheme (default: http)
        """,
    )

    parser.add_argument(
        "--http-mode",
        action="store_true",
        help="Run as HTTP server using Streamable HTTP transport (for network access)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to in HTTP mode (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9501,
        help="Port to bind to in HTTP mode (default: 9501)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Determine transport mode
    transport: Literal["stdio", "streamable-http"] = (
        "streamable-http" if args.http_mode else "stdio"
    )

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
