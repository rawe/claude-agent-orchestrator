"""
MCP Server Registry Service.

Part of MCP Server Registry Phase 2 (mcp-server-registry.md).

Provides access to the centralized MCP server registry stored as files.
The registry holds server definitions (URL, config schema, defaults) that are
referenced by agents and capabilities using the ref-based format.
"""

from typing import Optional

from mcp_server_storage import (
    list_mcp_servers as storage_list_mcp_servers,
    get_mcp_server as storage_get_mcp_server,
    create_mcp_server as storage_create_mcp_server,
    update_mcp_server as storage_update_mcp_server,
    delete_mcp_server as storage_delete_mcp_server,
)
from models import (
    MCPServerRegistryEntry,
    MCPServerRegistryCreate,
    MCPServerRegistryUpdate,
    MCPServerConfigSchema,
)


class MCPServerNotFoundError(Exception):
    """Raised when a referenced MCP server doesn't exist in the registry."""
    def __init__(self, server_id: str):
        self.server_id = server_id
        super().__init__(f"MCP server '{server_id}' not found in registry")


class MCPServerAlreadyExistsError(Exception):
    """Raised when attempting to create an MCP server that already exists."""
    def __init__(self, server_id: str):
        self.server_id = server_id
        super().__init__(f"MCP server '{server_id}' already exists")


def list_mcp_servers() -> list[MCPServerRegistryEntry]:
    """List all MCP servers in the registry."""
    return storage_list_mcp_servers()


def get_mcp_server(server_id: str) -> Optional[MCPServerRegistryEntry]:
    """Get an MCP server by ID. Returns None if not found."""
    return storage_get_mcp_server(server_id)


def create_mcp_server(data: MCPServerRegistryCreate) -> MCPServerRegistryEntry:
    """Create a new MCP server registry entry.

    Raises:
        MCPServerAlreadyExistsError: If server with this ID already exists
    """
    try:
        return storage_create_mcp_server(data)
    except ValueError as e:
        # Storage raises ValueError for duplicates, convert to service error
        if "already exists" in str(e):
            raise MCPServerAlreadyExistsError(data.id) from e
        raise


def update_mcp_server(
    server_id: str, updates: MCPServerRegistryUpdate
) -> Optional[MCPServerRegistryEntry]:
    """Update an MCP server. Returns updated entry or None if not found."""
    return storage_update_mcp_server(server_id, updates)


def delete_mcp_server(server_id: str) -> bool:
    """Delete an MCP server. Returns True if deleted, False if not found."""
    return storage_delete_mcp_server(server_id)


def resolve_mcp_server_ref(
    ref: str,
    config: Optional[dict] = None,
) -> dict:
    """Resolve an MCP server reference to its full configuration.

    Merges config in order: registry defaults → provided config

    Args:
        ref: Registry entry ID
        config: Optional config values to override defaults

    Returns:
        dict with 'url' and 'config' keys ready for placeholder resolution

    Raises:
        MCPServerNotFoundError: If server not found in registry
    """
    entry = get_mcp_server(ref)
    if not entry:
        raise MCPServerNotFoundError(ref)

    # Merge configs: registry defaults → provided config
    merged_config = {}
    if entry.default_config:
        merged_config.update(entry.default_config)
    if config:
        merged_config.update(config)

    return {
        "url": entry.url,
        "config": merged_config,
    }


def validate_required_config(
    resolved_config: dict,
    config_schema: Optional[MCPServerConfigSchema],
) -> list[str]:
    """Validate that all required config values are present.

    Args:
        resolved_config: Config dict after merging and placeholder resolution
        config_schema: Schema defining required fields

    Returns:
        List of missing required field names. Empty list means valid.
    """
    if not config_schema:
        return []

    missing = []
    for field_name, field_def in config_schema.items():
        if field_def.required:
            value = resolved_config.get(field_name)
            # Check if value is missing or still has unresolved placeholder
            if value is None or (isinstance(value, str) and value.startswith("${")):
                missing.append(field_name)

    return missing
