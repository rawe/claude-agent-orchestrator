"""
Agent Orchestrator MCP Server Library.

Provides an embedded MCP server that acts as a facade to the Agent Coordinator.
The server runs within the Agent Runner and forwards MCP tool calls to the
Coordinator API with proper authentication.

Usage:
    from agent_orchestrator_mcp import MCPServer

    mcp_server = MCPServer(coordinator_url, auth0_client)
    mcp_server.start()
    print(f"MCP server running at: {mcp_server.url}")
    # ...
    mcp_server.stop()
"""

from .server import MCPServer

__all__ = ["MCPServer"]
