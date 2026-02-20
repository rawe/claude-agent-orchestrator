"""
MCP Server Format Transformation

Transforms MCP server configurations from coordinator format to Claude Code format.
"""


def transform_mcp_servers_for_claude_code(mcp_servers: dict) -> dict:
    """Transform MCP servers from coordinator format to Claude Code format.

    The coordinator resolves MCP server refs and produces:
        {"server_name": {"url": "...", "config": {...}}}

    Claude Code expects:
        {"server_name": {"type": "http", "url": "...", "headers": {...}}}

    This transformation:
    - Renames 'config' to 'headers' (config values become HTTP headers)
    - Adds 'type': 'http' (only HTTP MCP servers are supported via registry)

    Args:
        mcp_servers: Dict of server_name -> {url, config} from coordinator

    Returns:
        Dict of server_name -> {type, url, headers} for Claude Code SDK
    """
    if not mcp_servers:
        return {}

    transformed = {}
    for server_name, server_config in mcp_servers.items():
        transformed[server_name] = {
            "type": "http",
            "url": server_config.get("url", ""),
            "headers": server_config.get("config", {}),
        }

    return transformed
