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
    AGENT_ORCHESTRATOR_COMMAND_PATH - Optional: Path to commands directory (auto-discovered if not set)
    AGENT_ORCHESTRATOR_PROJECT_DIR  - Optional: Default project directory
    MCP_SERVER_DEBUG                - Optional: Enable debug logging (true/false)
"""

import os
import sys
from pathlib import Path

# Add libs directory to Python path
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR / "libs"))

# Auto-discover commands directory if not set
# Structure: mcp-server/ -> agent-orchestrator/ -> skills/agent-orchestrator/commands/
if "AGENT_ORCHESTRATOR_COMMAND_PATH" not in os.environ:
    COMMANDS_DIR = SCRIPT_DIR.parent / "skills" / "agent-orchestrator" / "commands"
    os.environ["AGENT_ORCHESTRATOR_COMMAND_PATH"] = str(COMMANDS_DIR)

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
