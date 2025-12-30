"""
Agent Storage - File I/O operations for agent management.

Agents are stored as directories with the following structure:
    agents/{name}/
        agent.json              # Required: name, description
        agent.system-prompt.md  # Optional: system prompt
        agent.mcp.json          # Optional: {"mcpServers": {...}}
        .disabled               # Optional: presence indicates inactive

Capability Resolution:
    When an agent references capabilities, the system resolves and merges:
    - System prompts: agent prompt + capability texts (separator: \\n\\n---\\n\\n)
    - MCP servers: capabilities MCP + agent-level MCP
    See docs/features/capabilities-system.md for details.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from models import Agent, AgentCreate, AgentUpdate, MCPServerStdio, MCPServerHttp, MCPServerConfig, RunnerDemands

# Debug logging toggle - matches main.py
DEBUG = os.getenv("DEBUG_LOGGING", "").lower() in ("true", "1", "yes")


def get_agents_dir() -> Path:
    """Get agents directory from environment or default."""
    # Check explicit agents dir override first
    agents_dir = os.environ.get("AGENT_ORCHESTRATOR_AGENTS_DIR")
    if agents_dir:
        path = Path(agents_dir)
        if DEBUG:
            print(f"[DEBUG] agent_storage: Using AGENT_ORCHESTRATOR_AGENTS_DIR={path}", flush=True)
        return path

    # Fall back to project_dir/.agent-orchestrator/agents
    project_dir = os.environ.get("AGENT_ORCHESTRATOR_PROJECT_DIR", os.getcwd())
    path = Path(project_dir) / ".agent-orchestrator" / "agents"
    if DEBUG:
        print(f"[DEBUG] agent_storage: Using agents_dir={path} (project_dir={project_dir})", flush=True)
    return path


def _get_file_times(agent_dir: Path) -> tuple[str, str]:
    """Get created_at and modified_at times for agent directory."""
    agent_json = agent_dir / "agent.json"
    if agent_json.exists():
        stat = agent_json.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        return created_at, modified_at
    now = datetime.now().isoformat()
    return now, now


def _read_agent_from_dir(agent_dir: Path) -> Optional[Agent]:
    """Read agent data from directory. Returns None if invalid."""
    agent_json = agent_dir / "agent.json"
    if not agent_json.exists():
        return None

    try:
        with open(agent_json, encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("name")
        description = data.get("description")
        if not name or not description:
            return None

        # Read optional system prompt
        system_prompt = None
        prompt_file = agent_dir / "agent.system-prompt.md"
        if prompt_file.exists():
            system_prompt = prompt_file.read_text(encoding="utf-8")

        # Read optional MCP config
        mcp_servers = None
        mcp_file = agent_dir / "agent.mcp.json"
        if mcp_file.exists():
            with open(mcp_file, encoding="utf-8") as f:
                mcp_data = json.load(f)
                # Extract mcpServers dict, convert to appropriate type
                raw_servers = mcp_data.get("mcpServers", {})
                if raw_servers:
                    mcp_servers = {}
                    for k, v in raw_servers.items():
                        if v.get("type") == "http":
                            mcp_servers[k] = MCPServerHttp(**v)
                        else:
                            # Default to stdio (command-based)
                            mcp_servers[k] = MCPServerStdio(**v)

        # Read optional skills from agent.json
        skills = data.get("skills")

        # Read tags from agent.json (default: empty list)
        tags = data.get("tags", [])

        # Read capabilities from agent.json (default: empty list)
        capabilities = data.get("capabilities", [])

        # Read demands from agent.json (ADR-011)
        demands = None
        demands_data = data.get("demands")
        if demands_data:
            demands = RunnerDemands(**demands_data)

        # Check status via .disabled file
        status = "inactive" if (agent_dir / ".disabled").exists() else "active"

        # Get timestamps
        created_at, modified_at = _get_file_times(agent_dir)

        return Agent(
            name=name,
            description=description,
            system_prompt=system_prompt,
            mcp_servers=mcp_servers,
            skills=skills,
            tags=tags,
            capabilities=capabilities,
            demands=demands,
            status=status,
            created_at=created_at,
            modified_at=modified_at,
        )
    except (json.JSONDecodeError, IOError, TypeError):
        return None


# ==============================================================================
# Capability Resolution
# ==============================================================================

# Separator between system prompt sections when merging capabilities
CAPABILITY_SEPARATOR = "\n\n---\n\n"


class CapabilityResolutionError(Exception):
    """Base exception for capability resolution errors."""
    pass


class MissingCapabilityError(CapabilityResolutionError):
    """Raised when a referenced capability doesn't exist."""
    def __init__(self, agent_name: str, capability_name: str):
        self.agent_name = agent_name
        self.capability_name = capability_name
        super().__init__(
            f"Agent '{agent_name}' references missing capability: '{capability_name}'"
        )


class MCPServerConflictError(CapabilityResolutionError):
    """Raised when multiple sources define the same MCP server name."""
    def __init__(self, agent_name: str, server_name: str, sources: list[str]):
        self.agent_name = agent_name
        self.server_name = server_name
        self.sources = sources
        super().__init__(
            f"Agent '{agent_name}' has MCP server name conflict: '{server_name}' "
            f"defined in: {', '.join(sources)}"
        )


def _resolve_agent_capabilities(agent: Agent) -> Agent:
    """
    Resolve and merge capabilities into agent.

    This function:
    1. Loads each referenced capability
    2. Merges system prompts (agent + capabilities in declaration order)
    3. Merges MCP servers (capabilities + agent-level)
    4. Raises errors for missing capabilities or MCP server conflicts

    Args:
        agent: Raw agent with unresolved capabilities

    Returns:
        Agent with merged system_prompt and mcp_servers

    Raises:
        MissingCapabilityError: If a referenced capability doesn't exist
        MCPServerConflictError: If same MCP server name appears in multiple sources
    """
    # Import here to avoid circular imports
    from capability_storage import get_capability

    # No capabilities? Return as-is
    if not agent.capabilities:
        return agent

    # Collect parts for merging
    system_prompt_parts: list[str] = []
    merged_mcp_servers: dict[str, MCPServerConfig] = {}
    mcp_server_sources: dict[str, str] = {}  # Track where each server came from

    # Start with agent's own system prompt if present
    if agent.system_prompt:
        system_prompt_parts.append(agent.system_prompt)

    # Process each capability in declaration order
    for cap_name in agent.capabilities:
        capability = get_capability(cap_name)

        # Error if capability doesn't exist
        if capability is None:
            raise MissingCapabilityError(agent.name, cap_name)

        # Merge capability text into system prompt
        if capability.text:
            system_prompt_parts.append(capability.text)

        # Merge capability MCP servers
        if capability.mcp_servers:
            for server_name, server_config in capability.mcp_servers.items():
                # Check for conflict
                if server_name in merged_mcp_servers:
                    existing_source = mcp_server_sources[server_name]
                    raise MCPServerConflictError(
                        agent.name,
                        server_name,
                        [existing_source, f"capability:{cap_name}"]
                    )
                merged_mcp_servers[server_name] = server_config
                mcp_server_sources[server_name] = f"capability:{cap_name}"

    # Add agent-level MCP servers last
    if agent.mcp_servers:
        for server_name, server_config in agent.mcp_servers.items():
            # Check for conflict with capability servers
            if server_name in merged_mcp_servers:
                existing_source = mcp_server_sources[server_name]
                raise MCPServerConflictError(
                    agent.name,
                    server_name,
                    [existing_source, "agent"]
                )
            merged_mcp_servers[server_name] = server_config
            mcp_server_sources[server_name] = "agent"

    # Build merged system prompt
    merged_system_prompt = CAPABILITY_SEPARATOR.join(system_prompt_parts) if system_prompt_parts else None

    # Return new Agent with merged values
    return Agent(
        name=agent.name,
        description=agent.description,
        system_prompt=merged_system_prompt,
        mcp_servers=merged_mcp_servers if merged_mcp_servers else None,
        skills=agent.skills,
        tags=agent.tags,
        capabilities=agent.capabilities,  # Keep original list for reference
        demands=agent.demands,
        status=agent.status,
        created_at=agent.created_at,
        modified_at=agent.modified_at,
    )


def list_agents() -> list[Agent]:
    """List all valid agents, sorted by name."""
    agents_dir = get_agents_dir()
    if not agents_dir.exists():
        return []

    agents = []
    for subdir in agents_dir.iterdir():
        if not subdir.is_dir():
            continue
        agent = _read_agent_from_dir(subdir)
        if agent:
            agents.append(agent)

    agents.sort(key=lambda a: a.name)
    return agents


def get_agent(name: str, resolve: bool = True) -> Optional[Agent]:
    """
    Get agent by name.

    Args:
        name: Agent name
        resolve: If True (default), resolve and merge capabilities.
                 If False, return raw agent with unresolved capabilities.

    Returns:
        Agent or None if not found

    Raises:
        MissingCapabilityError: If resolve=True and a capability doesn't exist
        MCPServerConflictError: If resolve=True and MCP server names conflict
    """
    agent_dir = get_agents_dir() / name
    if not agent_dir.is_dir():
        return None

    agent = _read_agent_from_dir(agent_dir)
    if agent is None:
        return None

    if resolve:
        return _resolve_agent_capabilities(agent)
    return agent


def create_agent(data: AgentCreate) -> Agent:
    """
    Create a new agent.

    Raises:
        ValueError: If agent already exists
    """
    agents_dir = get_agents_dir()
    agent_dir = agents_dir / data.name

    if agent_dir.exists():
        raise ValueError(f"Agent already exists: {data.name}")

    # Create directory
    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_dir.mkdir()

    # Write agent.json
    agent_data = {"name": data.name, "description": data.description}
    if data.skills:
        agent_data["skills"] = data.skills
    if data.tags:
        agent_data["tags"] = data.tags
    if data.capabilities:
        agent_data["capabilities"] = data.capabilities
    if data.demands:
        agent_data["demands"] = data.demands.model_dump(exclude_none=True)

    with open(agent_dir / "agent.json", "w", encoding="utf-8") as f:
        json.dump(agent_data, f, indent=2)
        f.write("\n")

    # Write system prompt if provided
    if data.system_prompt:
        (agent_dir / "agent.system-prompt.md").write_text(
            data.system_prompt, encoding="utf-8"
        )

    # Write MCP config if provided
    if data.mcp_servers:
        mcp_data = {
            "mcpServers": {k: v.model_dump(exclude_none=True) for k, v in data.mcp_servers.items()}
        }
        with open(agent_dir / "agent.mcp.json", "w", encoding="utf-8") as f:
            json.dump(mcp_data, f, indent=2)
            f.write("\n")

    # Return raw agent (without capability resolution) for management UI
    return get_agent(data.name, resolve=False)


def update_agent(name: str, updates: AgentUpdate) -> Optional[Agent]:
    """
    Update an existing agent.

    Returns None if agent not found.
    """
    agent_dir = get_agents_dir() / name
    if not agent_dir.is_dir():
        return None

    # Read existing agent.json
    agent_json_path = agent_dir / "agent.json"
    with open(agent_json_path, encoding="utf-8") as f:
        agent_data = json.load(f)

    # Apply updates
    if updates.description is not None:
        agent_data["description"] = updates.description

    if updates.skills is not None:
        if updates.skills:
            agent_data["skills"] = updates.skills
        else:
            agent_data.pop("skills", None)

    if updates.tags is not None:
        if updates.tags:
            agent_data["tags"] = updates.tags
        else:
            agent_data.pop("tags", None)

    if updates.capabilities is not None:
        if updates.capabilities:
            agent_data["capabilities"] = updates.capabilities
        else:
            agent_data.pop("capabilities", None)

    if updates.demands is not None:
        if not updates.demands.is_empty():
            agent_data["demands"] = updates.demands.model_dump(exclude_none=True)
        else:
            agent_data.pop("demands", None)

    # Write updated agent.json
    with open(agent_json_path, "w", encoding="utf-8") as f:
        json.dump(agent_data, f, indent=2)
        f.write("\n")

    # Update system prompt
    prompt_file = agent_dir / "agent.system-prompt.md"
    if updates.system_prompt is not None:
        if updates.system_prompt:
            prompt_file.write_text(updates.system_prompt, encoding="utf-8")
        elif prompt_file.exists():
            prompt_file.unlink()

    # Update MCP config
    # mcp_servers={} (empty dict) means clear/delete, None means don't update
    mcp_file = agent_dir / "agent.mcp.json"
    if updates.mcp_servers is not None:
        if updates.mcp_servers:
            mcp_data = {
                "mcpServers": {k: v.model_dump(exclude_none=True) for k, v in updates.mcp_servers.items()}
            }
            with open(mcp_file, "w", encoding="utf-8") as f:
                json.dump(mcp_data, f, indent=2)
                f.write("\n")
        elif mcp_file.exists():
            # Empty dict {} means delete the file
            mcp_file.unlink()

    # Return raw agent (without capability resolution) for management UI
    return get_agent(name, resolve=False)


def delete_agent(name: str) -> bool:
    """Delete an agent. Returns True if deleted, False if not found."""
    import shutil

    agent_dir = get_agents_dir() / name
    if not agent_dir.is_dir():
        return False

    shutil.rmtree(agent_dir)
    return True


def set_agent_status(name: str, status: str) -> Optional[Agent]:
    """
    Set agent status via .disabled file.

    Returns None if agent not found.
    """
    agent_dir = get_agents_dir() / name
    if not agent_dir.is_dir():
        return None

    disabled_file = agent_dir / ".disabled"

    if status == "inactive":
        disabled_file.touch()
    elif status == "active" and disabled_file.exists():
        disabled_file.unlink()

    # Return raw agent (without capability resolution) for management UI
    return get_agent(name, resolve=False)
