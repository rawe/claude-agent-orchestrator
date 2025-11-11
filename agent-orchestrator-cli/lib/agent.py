"""
Agent Management

Handles agent discovery, loading, and validation.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class AgentDefinition:
    """Agent definition loaded from agent.json."""

    name: str
    description: str
    system_prompt: Optional[str]
    mcp_config: Optional[dict]
    agent_dir: Path


def load_agent(agent_name: str, agents_dir: Path) -> AgentDefinition:
    """
    Load agent definition from agents directory.

    Structure:
        agents/
          agent-name/
            agent.json              # Required
            agent.system-prompt.md  # Optional
            agent.mcp.json         # Optional

    TODO: Implement agent loading with validation
    """
    # TODO: Implement
    raise NotImplementedError("Agent loading not yet implemented")


def validate_agent_definition(agent_def: AgentDefinition) -> tuple[bool, str]:
    """
    Validate agent definition.

    Checks:
    - Required fields present
    - Name matches directory name
    - Files exist and are readable

    Returns:
        (is_valid, error_message)

    TODO: Implement validation
    """
    # TODO: Implement
    raise NotImplementedError("Agent validation not yet implemented")


def list_agents(agents_dir: Path) -> list[AgentDefinition]:
    """
    List all available agents.

    TODO: Implement agent discovery
    """
    # TODO: Implement
    raise NotImplementedError("Agent listing not yet implemented")


def get_system_prompt(agent_def: AgentDefinition) -> Optional[str]:
    """
    Load system prompt from agent.system-prompt.md if it exists.

    TODO: Implement system prompt loading
    """
    # TODO: Implement
    raise NotImplementedError("System prompt loading not yet implemented")


def get_mcp_config(agent_def: AgentDefinition) -> Optional[dict]:
    """
    Load MCP configuration from agent.mcp.json if it exists.

    TODO: Implement MCP config loading
    """
    # TODO: Implement
    raise NotImplementedError("MCP config loading not yet implemented")
