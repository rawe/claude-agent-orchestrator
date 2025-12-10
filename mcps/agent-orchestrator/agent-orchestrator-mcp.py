#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.7.0",
#   "fastmcp>=2.0.0",
#   "pydantic>=2.0.0",
#   "fastapi>=0.115.0",
#   "uvicorn>=0.32.0",
#   "httpx>=0.28.0",
# ]
# ///
"""
Agent Orchestrator MCP Server

Standalone entry point for the Agent Orchestrator MCP server.
Uses UV for dependency management with inline dependency declarations.

This server communicates with the Agent Runtime API to orchestrate Claude Code agents.
It no longer spawns subprocess commands directly - all operations go through the Jobs API.

Usage:
    # stdio mode (default, for Claude Desktop/CLI)
    uv run agent-orchestrator-mcp.py

    # HTTP mode (for network access)
    uv run agent-orchestrator-mcp.py --http-mode
    uv run agent-orchestrator-mcp.py --http-mode --port 9000
    uv run agent-orchestrator-mcp.py --http-mode --host 0.0.0.0 --port 8080

Environment Variables:
    AGENT_ORCHESTRATOR_API_URL  - Optional: Agent Runtime API URL (default: http://127.0.0.1:8765)
    AGENT_SESSION_NAME          - Optional: Parent session name for callback support (stdio mode)
    MCP_SERVER_DEBUG            - Optional: Enable debug logging (true/false)
"""

import argparse
import sys
import warnings
from pathlib import Path

# Suppress websockets deprecation warnings from uvicorn
warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")

# Add libs directory to Python path
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR / "libs"))


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Agent Orchestrator MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in stdio mode (default, for Claude Desktop/CLI)
  uv run agent-orchestrator-mcp.py

  # Run in HTTP mode on default port 8080
  uv run agent-orchestrator-mcp.py --http-mode

  # Run in HTTP mode on custom port
  uv run agent-orchestrator-mcp.py --http-mode --port 9000

  # Run in HTTP mode, accessible from network
  uv run agent-orchestrator-mcp.py --http-mode --host 0.0.0.0 --port 8080
        """,
    )

    parser.add_argument(
        "--http-mode",
        action="store_true",
        help="Run as HTTP server using Streamable HTTP transport (recommended for network access)",
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
        default=8080,
        help="Port to bind to in HTTP/SSE mode (default: 8080)",
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    # Import server module (after path setup)
    from server import run_server

    # Determine transport mode
    if args.http_mode:
        transport = "streamable-http"
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
