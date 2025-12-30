"""
Validation functions for agent and capability data.
"""

import re
from pathlib import Path


def validate_agent_name(name: str) -> None:
    """
    Validate agent name format.

    Rules:
        - 1-60 characters
        - Alphanumeric, hyphens, underscores only
        - Must start with letter or number

    Raises:
        ValueError: If name is invalid
    """
    if not name:
        raise ValueError("Agent name is required")

    if len(name) > 60:
        raise ValueError("Agent name must be 60 characters or less")

    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", name):
        raise ValueError(
            "Agent name must start with letter/number and contain only "
            "alphanumeric characters, hyphens, and underscores"
        )


def validate_unique_name(name: str, agents_dir: Path) -> None:
    """
    Validate that agent name doesn't already exist.

    Raises:
        ValueError: If agent directory already exists
    """
    if (agents_dir / name).exists():
        raise ValueError(f"Agent already exists: {name}")


def validate_capability_name(name: str) -> None:
    """
    Validate capability name format.

    Rules:
        - 1-60 characters
        - Alphanumeric, hyphens, underscores only
        - Must start with letter or number

    Same rules as agent names for consistency.

    Raises:
        ValueError: If name is invalid
    """
    if not name:
        raise ValueError("Capability name is required")

    if len(name) > 60:
        raise ValueError("Capability name must be 60 characters or less")

    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", name):
        raise ValueError(
            "Capability name must start with letter/number and contain only "
            "alphanumeric characters, hyphens, and underscores"
        )


def validate_unique_capability_name(name: str, capabilities_dir: Path) -> None:
    """
    Validate that capability name doesn't already exist.

    Raises:
        ValueError: If capability directory already exists
    """
    if (capabilities_dir / name).exists():
        raise ValueError(f"Capability already exists: {name}")
