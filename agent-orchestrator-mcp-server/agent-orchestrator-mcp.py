#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.7.0",
#   "pydantic>=2.0.0",
# ]
# ///
"""
Agent Orchestrator MCP Server

Standalone entry point for the Agent Orchestrator MCP server.
Uses UV for dependency management with inline dependency declarations.

Usage:
    uv run agent-orchestrator-mcp.py

Environment Variables:
    AGENT_ORCHESTRATOR_COMMAND_PATH - Required: Path to commands directory
    AGENT_ORCHESTRATOR_PROJECT_DIR  - Optional: Default project directory
    MCP_SERVER_DEBUG                - Optional: Enable debug logging (true/false)
"""

import sys
from pathlib import Path

# Add libs directory to Python path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "libs"))

# Import and run the server
from server import main
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)
    except Exception as error:
        print(f"Server error: {error}", file=sys.stderr)
        sys.exit(1)
