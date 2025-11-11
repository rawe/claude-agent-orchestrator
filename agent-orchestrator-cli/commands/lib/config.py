"""
Configuration Management

Handles configuration loading with precedence:
CLI Flags > Environment Variables > Defaults (PWD)
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


# Environment variable names (MUST match bash script exactly)
ENV_PROJECT_DIR = "AGENT_ORCHESTRATOR_PROJECT_DIR"
ENV_SESSIONS_DIR = "AGENT_ORCHESTRATOR_SESSIONS_DIR"
ENV_AGENTS_DIR = "AGENT_ORCHESTRATOR_AGENTS_DIR"
ENV_ENABLE_LOGGING = "AGENT_ORCHESTRATOR_ENABLE_LOGGING"


@dataclass
class Config:
    """Configuration for agent orchestrator."""

    project_dir: Path
    sessions_dir: Path
    agents_dir: Path
    enable_logging: bool


def resolve_absolute_path(path_str: str) -> Path:
    """
    Convert path string to absolute Path object.

    Args:
        path_str: Path string (can be relative or absolute)

    Returns:
        Absolute Path object with normalized path
    """
    path = Path(path_str)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def find_existing_parent(path: Path) -> Path:
    """
    Find the first existing parent directory by walking up the tree.

    Args:
        path: Directory path to check

    Returns:
        First existing parent directory (or root if none found)
    """
    current = path
    while current != current.parent:  # Not at root
        if current.exists() and current.is_dir():
            return current
        current = current.parent
    return Path("/")


def validate_can_create(path: Path, dir_name: str) -> None:
    """
    Validate that a directory can be created (parent exists and is writable).

    Args:
        path: The directory to validate
        dir_name: Human-readable name for error messages ("sessions", "agents")

    Raises:
        ValueError: If directory cannot be created (parent not writable)
    """
    # If directory already exists, it's valid
    if path.exists() and path.is_dir():
        return

    # Find first existing parent
    parent = find_existing_parent(path.parent)

    # Check if parent is writable
    if not os.access(parent, os.W_OK):
        raise ValueError(
            f"Cannot create {dir_name} directory (parent not writable): {path}\n"
            f"Existing parent: {parent}"
        )


def load_config(
    cli_project_dir: Optional[str] = None,
    cli_sessions_dir: Optional[str] = None,
    cli_agents_dir: Optional[str] = None,
) -> Config:
    """
    Load configuration with CLI > ENV > DEFAULT precedence.

    Args:
        cli_project_dir: Optional CLI override for project directory
        cli_sessions_dir: Optional CLI override for sessions directory
        cli_agents_dir: Optional CLI override for agents directory

    Returns:
        Config object with all paths resolved to absolute paths

    Raises:
        ValueError: If project_dir doesn't exist or directories can't be created
    """
    # Part A: Read environment variables
    env_project_dir = os.environ.get(ENV_PROJECT_DIR)
    env_sessions_dir = os.environ.get(ENV_SESSIONS_DIR)
    env_agents_dir = os.environ.get(ENV_AGENTS_DIR)
    env_logging = os.environ.get(ENV_ENABLE_LOGGING, "").lower()

    # Part B: Apply precedence for PROJECT_DIR
    # CLI > ENV > DEFAULT
    if cli_project_dir:
        project_dir_str = cli_project_dir
    elif env_project_dir:
        project_dir_str = env_project_dir
    else:
        project_dir_str = str(Path.cwd())

    # Resolve to absolute path
    project_dir = resolve_absolute_path(project_dir_str)

    # Part C: Validate PROJECT_DIR
    # Must exist and be readable
    if not project_dir.exists():
        raise ValueError(f"Project directory does not exist: {project_dir}")
    if not project_dir.is_dir():
        raise ValueError(f"Project directory is not a directory: {project_dir}")
    if not os.access(project_dir, os.R_OK):
        raise ValueError(f"Project directory is not readable: {project_dir}")

    # Part D: Apply precedence for SESSIONS_DIR
    # CLI > ENV > DEFAULT
    if cli_sessions_dir:
        sessions_dir = resolve_absolute_path(cli_sessions_dir)
    elif env_sessions_dir:
        sessions_dir = resolve_absolute_path(env_sessions_dir)
    else:
        # Default: {project_dir}/.agent-orchestrator/agent-sessions
        sessions_dir = project_dir / ".agent-orchestrator" / "agent-sessions"

    # Part E: Apply precedence for AGENTS_DIR
    # CLI > ENV > DEFAULT
    if cli_agents_dir:
        agents_dir = resolve_absolute_path(cli_agents_dir)
    elif env_agents_dir:
        agents_dir = resolve_absolute_path(env_agents_dir)
    else:
        # Default: {project_dir}/.agent-orchestrator/agents
        agents_dir = project_dir / ".agent-orchestrator" / "agents"

    # Part F: Validate creation permissions
    # Validate we can create these directories
    validate_can_create(sessions_dir, "sessions")
    validate_can_create(agents_dir, "agents")

    # Part G: Parse logging flag
    # Enable if value is "1", "true", or "yes"
    enable_logging = env_logging in ("1", "true", "yes")

    # Part H: Return Config object
    return Config(
        project_dir=project_dir,
        sessions_dir=sessions_dir,
        agents_dir=agents_dir,
        enable_logging=enable_logging,
    )
