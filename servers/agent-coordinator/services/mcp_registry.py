"""
MCP Server Registry Service.

Part of MCP Server Registry Phase 2 (mcp-server-registry.md).

Provides access to the centralized MCP server registry stored in the database.
The registry holds server definitions (URL, config schema, defaults) that are
referenced by agents and capabilities using the ref-based format.
"""

import json
from typing import Optional

from database import (
    create_mcp_server as db_create_mcp_server,
    get_mcp_server as db_get_mcp_server,
    list_mcp_servers as db_list_mcp_servers,
    update_mcp_server as db_update_mcp_server,
    delete_mcp_server as db_delete_mcp_server,
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
    rows = db_list_mcp_servers()
    return [_dict_to_entry(row) for row in rows]


def get_mcp_server(server_id: str) -> Optional[MCPServerRegistryEntry]:
    """Get an MCP server by ID. Returns None if not found."""
    row = db_get_mcp_server(server_id)
    if not row:
        return None
    return _dict_to_entry(row)


def create_mcp_server(data: MCPServerRegistryCreate) -> MCPServerRegistryEntry:
    """Create a new MCP server registry entry.

    Raises:
        MCPServerAlreadyExistsError: If server with this ID already exists
    """
    # Check if already exists
    if db_get_mcp_server(data.id):
        raise MCPServerAlreadyExistsError(data.id)

    # Serialize JSON fields
    config_schema_json = None
    if data.config_schema:
        config_schema_json = data.config_schema.model_dump_json()

    default_config_json = None
    if data.default_config:
        default_config_json = json.dumps(data.default_config)

    row = db_create_mcp_server(
        server_id=data.id,
        name=data.name,
        url=data.url,
        description=data.description,
        config_schema=config_schema_json,
        default_config=default_config_json,
    )
    if not row:
        raise RuntimeError(f"Failed to create MCP server '{data.id}'")
    return _dict_to_entry(row)


def update_mcp_server(
    server_id: str, updates: MCPServerRegistryUpdate
) -> Optional[MCPServerRegistryEntry]:
    """Update an MCP server. Returns updated entry or None if not found."""
    # Serialize JSON fields if provided
    config_schema_json = None
    if updates.config_schema is not None:
        config_schema_json = updates.config_schema.model_dump_json()

    default_config_json = None
    if updates.default_config is not None:
        default_config_json = json.dumps(updates.default_config)

    row = db_update_mcp_server(
        server_id=server_id,
        name=updates.name,
        description=updates.description,
        url=updates.url,
        config_schema=config_schema_json,
        default_config=default_config_json,
    )
    if not row:
        return None
    return _dict_to_entry(row)


def delete_mcp_server(server_id: str) -> bool:
    """Delete an MCP server. Returns True if deleted, False if not found."""
    return db_delete_mcp_server(server_id)


def _dict_to_entry(row: dict) -> MCPServerRegistryEntry:
    """Convert database row dict to MCPServerRegistryEntry model."""
    config_schema = None
    if row.get("config_schema"):
        config_schema = MCPServerConfigSchema(**row["config_schema"])

    return MCPServerRegistryEntry(
        id=row["id"],
        name=row["name"],
        description=row.get("description"),
        url=row["url"],
        config_schema=config_schema,
        default_config=row.get("default_config"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


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
    if not config_schema or not config_schema.fields:
        return []

    missing = []
    for field_name, field_def in config_schema.fields.items():
        if field_def.required:
            value = resolved_config.get(field_name)
            # Check if value is missing or still has unresolved placeholder
            if value is None or (isinstance(value, str) and value.startswith("${")):
                missing.append(field_name)

    return missing
