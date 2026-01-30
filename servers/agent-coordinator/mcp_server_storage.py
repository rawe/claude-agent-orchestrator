"""
MCP Server Storage - File I/O operations for MCP server registry.

MCP servers are stored as directories with the following structure:
    mcp-servers/{id}/
        mcp-server.json     # Server configuration (id, name, description, url, config_schema, default_config)
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from models import (
    MCPServerRegistryEntry,
    MCPServerRegistryCreate,
    MCPServerRegistryUpdate,
    ConfigSchemaField,
)

# Debug logging toggle - matches main.py
DEBUG = os.getenv("DEBUG_LOGGING", "").lower() in ("true", "1", "yes")


def get_mcp_servers_dir() -> Path:
    """
    Get MCP servers directory.

    MCP servers are stored as a sibling to the agents directory:
    - If AGENT_ORCHESTRATOR_AGENTS_DIR is set: {AGENTS_DIR}/../mcp-servers/
    - Otherwise: {PROJECT_DIR}/.agent-orchestrator/mcp-servers/
    """
    agents_dir = os.environ.get("AGENT_ORCHESTRATOR_AGENTS_DIR")
    if agents_dir:
        # MCP servers are sibling to agents dir
        path = Path(agents_dir).parent / "mcp-servers"
        if DEBUG:
            print(f"[DEBUG] mcp_server_storage: Using {path}", flush=True)
        return path

    # Fall back to project_dir/.agent-orchestrator/mcp-servers
    project_dir = os.environ.get("AGENT_ORCHESTRATOR_PROJECT_DIR", os.getcwd())
    path = Path(project_dir) / ".agent-orchestrator" / "mcp-servers"
    if DEBUG:
        print(
            f"[DEBUG] mcp_server_storage: Using {path} (project_dir={project_dir})",
            flush=True,
        )
    return path


def _get_file_times(server_dir: Path) -> tuple[str, str]:
    """Get created_at and updated_at times for MCP server directory."""
    server_json = server_dir / "mcp-server.json"
    if server_json.exists():
        stat = server_json.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
        updated_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        return created_at, updated_at
    now = datetime.now().isoformat()
    return now, now


def _read_mcp_server_from_dir(server_dir: Path) -> Optional[MCPServerRegistryEntry]:
    """Read MCP server data from directory. Returns None if invalid."""
    server_json = server_dir / "mcp-server.json"
    if not server_json.exists():
        return None

    try:
        with open(server_json, encoding="utf-8") as f:
            data = json.load(f)

        server_id = data.get("id")
        name = data.get("name")
        url = data.get("url")
        if not server_id or not name or not url:
            return None

        # Parse config_schema if present
        config_schema = None
        if data.get("config_schema"):
            config_schema = {
                k: ConfigSchemaField(**v)
                for k, v in data["config_schema"].items()
            }

        # Get timestamps
        created_at, updated_at = _get_file_times(server_dir)

        return MCPServerRegistryEntry(
            id=server_id,
            name=name,
            description=data.get("description"),
            url=url,
            config_schema=config_schema,
            default_config=data.get("default_config"),
            created_at=created_at,
            updated_at=updated_at,
        )
    except (json.JSONDecodeError, IOError, TypeError):
        return None


def list_mcp_servers() -> list[MCPServerRegistryEntry]:
    """List all valid MCP servers, sorted by name."""
    servers_dir = get_mcp_servers_dir()
    if not servers_dir.exists():
        return []

    servers = []
    for subdir in servers_dir.iterdir():
        if not subdir.is_dir():
            continue
        server = _read_mcp_server_from_dir(subdir)
        if server:
            servers.append(server)

    servers.sort(key=lambda s: s.name)
    return servers


def get_mcp_server(server_id: str) -> Optional[MCPServerRegistryEntry]:
    """Get MCP server by ID. Returns None if not found."""
    server_dir = get_mcp_servers_dir() / server_id
    if not server_dir.is_dir():
        return None
    return _read_mcp_server_from_dir(server_dir)


def create_mcp_server(data: MCPServerRegistryCreate) -> MCPServerRegistryEntry:
    """
    Create a new MCP server.

    Raises:
        ValueError: If MCP server already exists
    """
    servers_dir = get_mcp_servers_dir()
    server_dir = servers_dir / data.id

    if server_dir.exists():
        raise ValueError(f"MCP server already exists: {data.id}")

    # Create directory
    servers_dir.mkdir(parents=True, exist_ok=True)
    server_dir.mkdir()

    # Build server data
    server_data: dict[str, Any] = {
        "id": data.id,
        "name": data.name,
        "url": data.url,
    }
    if data.description:
        server_data["description"] = data.description
    if data.config_schema:
        server_data["config_schema"] = {
            k: v.model_dump(exclude_none=True)
            for k, v in data.config_schema.items()
        }
    if data.default_config:
        server_data["default_config"] = data.default_config

    # Write mcp-server.json
    with open(server_dir / "mcp-server.json", "w", encoding="utf-8") as f:
        json.dump(server_data, f, indent=2)
        f.write("\n")

    return get_mcp_server(data.id)


def update_mcp_server(
    server_id: str, updates: MCPServerRegistryUpdate
) -> Optional[MCPServerRegistryEntry]:
    """
    Update an existing MCP server.

    Returns None if MCP server not found.
    """
    server_dir = get_mcp_servers_dir() / server_id
    if not server_dir.is_dir():
        return None

    # Read existing mcp-server.json
    server_json_path = server_dir / "mcp-server.json"
    with open(server_json_path, encoding="utf-8") as f:
        server_data = json.load(f)

    # Apply updates
    if updates.name is not None:
        server_data["name"] = updates.name
    if updates.description is not None:
        server_data["description"] = updates.description
    if updates.url is not None:
        server_data["url"] = updates.url
    if updates.config_schema is not None:
        server_data["config_schema"] = {
            k: v.model_dump(exclude_none=True)
            for k, v in updates.config_schema.items()
        }
    if updates.default_config is not None:
        server_data["default_config"] = updates.default_config

    # Write updated mcp-server.json
    with open(server_json_path, "w", encoding="utf-8") as f:
        json.dump(server_data, f, indent=2)
        f.write("\n")

    return get_mcp_server(server_id)


def delete_mcp_server(server_id: str) -> bool:
    """Delete an MCP server. Returns True if deleted, False if not found."""
    server_dir = get_mcp_servers_dir() / server_id
    if not server_dir.is_dir():
        return False

    shutil.rmtree(server_dir)
    return True
