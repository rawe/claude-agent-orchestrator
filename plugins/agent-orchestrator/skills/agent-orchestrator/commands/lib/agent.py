"""
Agent Management

Handles agent discovery, loading, and validation.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Agent configuration loaded from agent directory."""
    name: str
    description: str
    system_prompt: Optional[str]  # Content of agent.system-prompt.md
    mcp_config: Optional[dict]    # Parsed agent.mcp.json


def load_agent_config(agent_name: str, agents_dir: Path) -> AgentConfig:
    """
    Load agent configuration from directory.

    Args:
        agent_name: Name of the agent to load
        agents_dir: Directory containing agent subdirectories

    Returns:
        AgentConfig with loaded configuration

    Raises:
        FileNotFoundError: If agent directory or agent.json not found
        json.JSONDecodeError: If agent.json or agent.mcp.json is invalid
        KeyError: If required fields missing from agent.json
        ValueError: If name in agent.json doesn't match directory name

    Structure:
        agents/
          agent-name/
            agent.json              # Required: name, description
            agent.system-prompt.md  # Optional: system prompt text
            agent.mcp.json         # Optional: MCP servers config
    """
    # 1. Build paths
    agent_dir = agents_dir / agent_name
    agent_file = agent_dir / "agent.json"
    prompt_file = agent_dir / "agent.system-prompt.md"
    mcp_file = agent_dir / "agent.mcp.json"

    # 2. Validate agent directory exists
    if not agent_dir.is_dir():
        raise FileNotFoundError(
            f"Agent not found: {agent_name} (expected: {agent_dir})"
        )

    # 3. Validate agent.json exists
    if not agent_file.exists():
        raise FileNotFoundError(
            f"Agent config not found: {agent_file}"
        )

    # 4. Parse agent.json
    with open(agent_file, encoding='utf-8') as f:
        data = json.load(f)  # Raises JSONDecodeError if invalid

    name = data["name"]  # Raises KeyError if missing
    description = data["description"]  # Raises KeyError if missing

    # 5. Validate name matches directory
    if name != agent_name:
        raise ValueError(
            f"Name mismatch: folder={agent_name}, config={name}"
        )

    # 6. Load system prompt (optional)
    system_prompt = None
    if prompt_file.exists():
        system_prompt = prompt_file.read_text(encoding='utf-8')

    # 7. Load MCP config (optional)
    mcp_config = None
    if mcp_file.exists():
        with open(mcp_file, encoding='utf-8') as f:
            mcp_config = json.load(f)  # Raises JSONDecodeError if invalid

    # 8. Return AgentConfig
    return AgentConfig(
        name=name,
        description=description,
        system_prompt=system_prompt,
        mcp_config=mcp_config
    )


def list_all_agents(agents_dir: Path) -> list[tuple[str, str]]:
    """
    List all available agent definitions.

    Args:
        agents_dir: Directory containing agent subdirectories

    Returns:
        List of (name, description) tuples, sorted by name
        Empty list if agents_dir doesn't exist or contains no valid agents

    Note:
        Invalid agent directories (missing agent.json, malformed JSON, etc.)
        are silently skipped to match bash script behavior.
    """
    # 1. Check if agents_dir exists
    if not agents_dir.exists():
        return []

    # 2. Initialize results list
    agents = []

    # 3. Iterate through subdirectories
    for subdir in agents_dir.iterdir():
        if not subdir.is_dir():
            continue  # Skip files

        # Try to load agent.json from this directory
        agent_file = subdir / "agent.json"
        if not agent_file.exists():
            continue  # Skip directories without agent.json

        try:
            # Parse JSON
            with open(agent_file, encoding='utf-8') as f:
                data = json.load(f)

            name = data.get("name", "")
            description = data.get("description", "")

            # Add to results if valid (both fields present)
            if name and description:
                agents.append((name, description))

        except (json.JSONDecodeError, KeyError, IOError):
            # Skip invalid agents (silent skip like bash script)
            continue

    # 4. Sort by name
    agents.sort(key=lambda x: x[0])

    # 5. Return sorted list
    return agents


def build_mcp_servers_dict(mcp_config: Optional[dict]) -> dict:
    """
    Convert agent MCP config to Claude SDK format.

    Args:
        mcp_config: Parsed agent.mcp.json content (or None)

    Returns:
        Dictionary suitable for Claude SDK's mcp_servers parameter
        Empty dict if mcp_config is None or doesn't contain mcpServers

    Example:
        mcp_config = {"mcpServers": {"server1": {...}}}
        -> returns {"server1": {...}}
    """
    # 1. Handle None case
    if mcp_config is None:
        return {}

    # 2. Extract mcpServers dict
    # Use .get() with default {} to handle missing key
    mcp_servers = mcp_config.get("mcpServers", {})

    # 3. Return dict as-is (SDK expects same format)
    return mcp_servers
