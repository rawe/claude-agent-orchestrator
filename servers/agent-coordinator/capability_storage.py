"""
Capability Storage - File I/O operations for capability management.

Capabilities are stored as directories with the following structure:
    capabilities/{name}/
        capability.json         # Required: name, description
        capability.text.md      # Optional: instructions for system prompt
        capability.mcp.json     # Optional: {"mcpServers": {...}}
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from models import (
    Capability,
    CapabilityCreate,
    CapabilitySummary,
    CapabilityType,
    CapabilityUpdate,
    MCPServerHttp,
    MCPServerStdio,
)

# Debug logging toggle - matches main.py
DEBUG = os.getenv("DEBUG_LOGGING", "").lower() in ("true", "1", "yes")


def get_capabilities_dir() -> Path:
    """
    Get capabilities directory.

    Capabilities are stored as a sibling to the agents directory:
    - If AGENT_ORCHESTRATOR_AGENTS_DIR is set: {AGENTS_DIR}/../capabilities/
    - Otherwise: {PROJECT_DIR}/.agent-orchestrator/capabilities/
    """
    agents_dir = os.environ.get("AGENT_ORCHESTRATOR_AGENTS_DIR")
    if agents_dir:
        # Capabilities are sibling to agents dir
        path = Path(agents_dir).parent / "capabilities"
        if DEBUG:
            print(f"[DEBUG] capability_storage: Using {path}", flush=True)
        return path

    # Fall back to project_dir/.agent-orchestrator/capabilities
    project_dir = os.environ.get("AGENT_ORCHESTRATOR_PROJECT_DIR", os.getcwd())
    path = Path(project_dir) / ".agent-orchestrator" / "capabilities"
    if DEBUG:
        print(
            f"[DEBUG] capability_storage: Using {path} (project_dir={project_dir})",
            flush=True,
        )
    return path


def _get_file_times(capability_dir: Path) -> tuple[str, str]:
    """Get created_at and modified_at times for capability directory."""
    capability_json = capability_dir / "capability.json"
    if capability_json.exists():
        stat = capability_json.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        return created_at, modified_at
    now = datetime.now().isoformat()
    return now, now


def _detect_capability_type(
    data: dict,
    has_mcp: bool,
) -> CapabilityType:
    """
    Detect capability type from data.

    Used for auto-migration of existing capabilities without explicit type.
    Priority: explicit type > has script > has mcp > text (default)
    """
    # If type is explicitly set, use it
    if "type" in data:
        return CapabilityType(data["type"])

    # Auto-detect based on fields present
    if data.get("script"):
        return CapabilityType.SCRIPT
    if has_mcp:
        return CapabilityType.MCP
    return CapabilityType.TEXT


def _read_mcp_servers(
    mcp_file: Path,
) -> Optional[dict]:
    """Read MCP servers from capability.mcp.json file."""
    if not mcp_file.exists():
        return None

    with open(mcp_file, encoding="utf-8") as f:
        mcp_data = json.load(f)
        raw_servers = mcp_data.get("mcpServers", {})
        if not raw_servers:
            return None

        mcp_servers = {}
        for k, v in raw_servers.items():
            if v.get("type") == "http":
                mcp_servers[k] = MCPServerHttp(**v)
            else:
                # Default to stdio (command-based)
                mcp_servers[k] = MCPServerStdio(**v)
        return mcp_servers


def _read_capability_from_dir(capability_dir: Path) -> Optional[Capability]:
    """Read capability data from directory. Returns None if invalid."""
    capability_json = capability_dir / "capability.json"
    if not capability_json.exists():
        return None

    try:
        with open(capability_json, encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("name")
        description = data.get("description")
        if not name or not description:
            return None

        # Read optional script reference
        script = data.get("script")

        # Read optional text content
        text = None
        text_file = capability_dir / "capability.text.md"
        if text_file.exists():
            text = text_file.read_text(encoding="utf-8")

        # Read optional MCP config
        mcp_file = capability_dir / "capability.mcp.json"
        mcp_servers = _read_mcp_servers(mcp_file)

        # Detect type (auto-migrate existing capabilities without type)
        capability_type = _detect_capability_type(data, mcp_file.exists())

        # Get timestamps
        created_at, modified_at = _get_file_times(capability_dir)

        return Capability(
            name=name,
            description=description,
            type=capability_type,
            script=script,
            text=text,
            mcp_servers=mcp_servers,
            created_at=created_at,
            modified_at=modified_at,
        )
    except (json.JSONDecodeError, IOError, TypeError):
        return None


def _read_capability_summary_from_dir(
    capability_dir: Path,
) -> Optional[CapabilitySummary]:
    """Read capability summary from directory. Returns None if invalid."""
    capability_json = capability_dir / "capability.json"
    if not capability_json.exists():
        return None

    try:
        with open(capability_json, encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("name")
        description = data.get("description")
        if not name or not description:
            return None

        # Check for script reference
        script_name = data.get("script")
        has_script = script_name is not None

        # Check for optional files
        text_file = capability_dir / "capability.text.md"
        mcp_file = capability_dir / "capability.mcp.json"

        has_text = text_file.exists()
        has_mcp = mcp_file.exists()

        # Detect type (auto-migrate existing capabilities without type)
        capability_type = _detect_capability_type(data, has_mcp)

        # Get MCP server names if present
        mcp_server_names = []
        if has_mcp:
            with open(mcp_file, encoding="utf-8") as f:
                mcp_data = json.load(f)
                mcp_server_names = list(mcp_data.get("mcpServers", {}).keys())

        # Get timestamps
        created_at, modified_at = _get_file_times(capability_dir)

        return CapabilitySummary(
            name=name,
            description=description,
            type=capability_type,
            has_script=has_script,
            script_name=script_name,
            has_text=has_text,
            has_mcp=has_mcp,
            mcp_server_names=mcp_server_names,
            created_at=created_at,
            modified_at=modified_at,
        )
    except (json.JSONDecodeError, IOError, TypeError):
        return None


def list_capabilities() -> list[CapabilitySummary]:
    """List all valid capabilities, sorted by name."""
    capabilities_dir = get_capabilities_dir()
    if not capabilities_dir.exists():
        return []

    capabilities = []
    for subdir in capabilities_dir.iterdir():
        if not subdir.is_dir():
            continue
        capability = _read_capability_summary_from_dir(subdir)
        if capability:
            capabilities.append(capability)

    capabilities.sort(key=lambda c: c.name)
    return capabilities


def get_capability(name: str) -> Optional[Capability]:
    """Get capability by name. Returns None if not found."""
    capability_dir = get_capabilities_dir() / name
    if not capability_dir.is_dir():
        return None
    return _read_capability_from_dir(capability_dir)


def create_capability(data: CapabilityCreate) -> Capability:
    """
    Create a new capability.

    Raises:
        ValueError: If capability already exists
    """
    capabilities_dir = get_capabilities_dir()
    capability_dir = capabilities_dir / data.name

    if capability_dir.exists():
        raise ValueError(f"Capability already exists: {data.name}")

    # Create directory
    capabilities_dir.mkdir(parents=True, exist_ok=True)
    capability_dir.mkdir()

    # Write capability.json
    capability_data = {
        "name": data.name,
        "description": data.description,
        "type": data.type.value,
    }
    if data.script:
        capability_data["script"] = data.script
    with open(capability_dir / "capability.json", "w", encoding="utf-8") as f:
        json.dump(capability_data, f, indent=2)
        f.write("\n")

    # Write text if provided
    if data.text:
        (capability_dir / "capability.text.md").write_text(data.text, encoding="utf-8")

    # Write MCP config if provided
    if data.mcp_servers:
        mcp_data = {
            "mcpServers": {
                k: v.model_dump(exclude_none=True) for k, v in data.mcp_servers.items()
            }
        }
        with open(capability_dir / "capability.mcp.json", "w", encoding="utf-8") as f:
            json.dump(mcp_data, f, indent=2)
            f.write("\n")

    return get_capability(data.name)


def update_capability(name: str, updates: CapabilityUpdate) -> Optional[Capability]:
    """
    Update an existing capability.

    Returns None if capability not found.
    """
    capability_dir = get_capabilities_dir() / name
    if not capability_dir.is_dir():
        return None

    # Read existing capability.json
    capability_json_path = capability_dir / "capability.json"
    with open(capability_json_path, encoding="utf-8") as f:
        capability_data = json.load(f)

    # Apply updates
    if updates.description is not None:
        capability_data["description"] = updates.description

    # Update type
    if updates.type is not None:
        capability_data["type"] = updates.type.value

    # Update script reference
    # script="" (empty string) means clear, None means don't update
    if updates.script is not None:
        if updates.script:
            capability_data["script"] = updates.script
        else:
            # Empty string means remove script reference
            capability_data.pop("script", None)

    # Write updated capability.json
    with open(capability_json_path, "w", encoding="utf-8") as f:
        json.dump(capability_data, f, indent=2)
        f.write("\n")

    # Update text
    text_file = capability_dir / "capability.text.md"
    if updates.text is not None:
        if updates.text:
            text_file.write_text(updates.text, encoding="utf-8")
        elif text_file.exists():
            text_file.unlink()

    # Update MCP config
    # mcp_servers={} (empty dict) means clear/delete, None means don't update
    mcp_file = capability_dir / "capability.mcp.json"
    if updates.mcp_servers is not None:
        if updates.mcp_servers:
            mcp_data = {
                "mcpServers": {
                    k: v.model_dump(exclude_none=True)
                    for k, v in updates.mcp_servers.items()
                }
            }
            with open(mcp_file, "w", encoding="utf-8") as f:
                json.dump(mcp_data, f, indent=2)
                f.write("\n")
        elif mcp_file.exists():
            # Empty dict {} means delete the file
            mcp_file.unlink()

    return get_capability(name)


def delete_capability(name: str) -> bool:
    """Delete a capability. Returns True if deleted, False if not found."""
    import shutil

    capability_dir = get_capabilities_dir() / name
    if not capability_dir.is_dir():
        return False

    shutil.rmtree(capability_dir)
    return True
