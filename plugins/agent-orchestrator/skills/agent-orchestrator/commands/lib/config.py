"""
Configuration Management

Handles configuration loading with precedence:
CLI Flags > Environment Variables > Defaults (PWD)
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from utils import debug_log


# Environment variable names (MUST match bash script exactly)
ENV_PROJECT_DIR = "AGENT_ORCHESTRATOR_PROJECT_DIR"
ENV_SESSIONS_DIR = "AGENT_ORCHESTRATOR_SESSIONS_DIR"
ENV_AGENTS_DIR = "AGENT_ORCHESTRATOR_AGENTS_DIR"
ENV_ENABLE_LOGGING = "AGENT_ORCHESTRATOR_ENABLE_LOGGING"

# Observability environment variables
ENV_OBSERVABILITY_ENABLED = "AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED"
ENV_OBSERVABILITY_URL = "AGENT_ORCHESTRATOR_OBSERVABILITY_URL"
DEFAULT_OBSERVABILITY_URL = "http://127.0.0.1:8765"


@dataclass
class Config:
    """Configuration for agent orchestrator."""

    project_dir: Path
    sessions_dir: Path
    agents_dir: Path
    enable_logging: bool
    observability_enabled: bool
    observability_url: str


def resolve_absolute_path(path_str: str) -> Path:
    """
    Convert path string to absolute Path object.

    Args:
        path_str: Path string (can be relative or absolute)

    Returns:
        Absolute Path object with normalized path
    """
    path = Path(path_str)
    is_absolute = path.is_absolute()
    cwd = Path.cwd()

    if not is_absolute:
        path = cwd / path

    resolved_path = path.resolve()

    # DEBUG LOGGING - Track path resolution
    debug_log("resolve_absolute_path", {
        "input_path": path_str,
        "is_absolute": is_absolute,
        "cwd": str(cwd),
        "resolved_path": str(resolved_path),
    })

    return resolved_path


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
    # DEBUG LOGGING - Entry point
    debug_log("load_config - ENTRY", {
        "cwd": str(Path.cwd()),
        "cli_project_dir": cli_project_dir or "None",
        "cli_sessions_dir": cli_sessions_dir or "None",
        "cli_agents_dir": cli_agents_dir or "None",
    })

    # Part A: Read environment variables
    env_project_dir = os.environ.get(ENV_PROJECT_DIR)
    env_sessions_dir = os.environ.get(ENV_SESSIONS_DIR)
    env_agents_dir = os.environ.get(ENV_AGENTS_DIR)
    env_logging = os.environ.get(ENV_ENABLE_LOGGING, "").lower()

    # DEBUG LOGGING - Environment variables
    debug_log("load_config - ENV VARS", {
        "AGENT_ORCHESTRATOR_PROJECT_DIR": env_project_dir or "not set",
        "AGENT_ORCHESTRATOR_SESSIONS_DIR": env_sessions_dir or "not set",
        "AGENT_ORCHESTRATOR_AGENTS_DIR": env_agents_dir or "not set",
        "AGENT_ORCHESTRATOR_ENABLE_LOGGING": env_logging or "not set",
    })

    # Part B: Apply precedence for PROJECT_DIR
    # CLI > ENV > DEFAULT
    if cli_project_dir:
        project_dir_str = cli_project_dir
        project_dir_source = "CLI"
    elif env_project_dir:
        project_dir_str = env_project_dir
        project_dir_source = "ENV"
    else:
        project_dir_str = str(Path.cwd())
        project_dir_source = "DEFAULT"

    # Resolve to absolute path
    project_dir = resolve_absolute_path(project_dir_str)

    # DEBUG LOGGING - PROJECT_DIR resolution
    debug_log("load_config - PROJECT_DIR", {
        "source": project_dir_source,
        "raw_value": project_dir_str,
        "resolved_path": str(project_dir),
    })

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
        sessions_dir_source = "CLI"
        sessions_dir_raw = cli_sessions_dir
    elif env_sessions_dir:
        sessions_dir = resolve_absolute_path(env_sessions_dir)
        sessions_dir_source = "ENV"
        sessions_dir_raw = env_sessions_dir
    else:
        # Default: {project_dir}/.agent-orchestrator/agent-sessions
        sessions_dir = project_dir / ".agent-orchestrator" / "agent-sessions"
        sessions_dir_source = "DEFAULT"
        sessions_dir_raw = "{project_dir}/.agent-orchestrator/agent-sessions"

    # DEBUG LOGGING - SESSIONS_DIR resolution
    debug_log("load_config - SESSIONS_DIR", {
        "source": sessions_dir_source,
        "raw_value": sessions_dir_raw,
        "resolved_path": str(sessions_dir),
    })

    # Part E: Apply precedence for AGENTS_DIR
    # CLI > ENV > DEFAULT
    if cli_agents_dir:
        agents_dir = resolve_absolute_path(cli_agents_dir)
        agents_dir_source = "CLI"
        agents_dir_raw = cli_agents_dir
    elif env_agents_dir:
        agents_dir = resolve_absolute_path(env_agents_dir)
        agents_dir_source = "ENV"
        agents_dir_raw = env_agents_dir
    else:
        # Default: {project_dir}/.agent-orchestrator/agents
        agents_dir = project_dir / ".agent-orchestrator" / "agents"
        agents_dir_source = "DEFAULT"
        agents_dir_raw = "{project_dir}/.agent-orchestrator/agents"

    # DEBUG LOGGING - AGENTS_DIR resolution
    debug_log("load_config - AGENTS_DIR", {
        "source": agents_dir_source,
        "raw_value": agents_dir_raw,
        "resolved_path": str(agents_dir),
    })

    # Part F: Validate creation permissions
    # Validate we can create these directories
    validate_can_create(sessions_dir, "sessions")
    validate_can_create(agents_dir, "agents")

    # Part G: Parse logging flag
    # Enable if value is "1", "true", or "yes"
    enable_logging = env_logging in ("1", "true", "yes")

    # Part H: Parse observability configuration
    # Default is TRUE (enabled). Only disable if explicitly set to "0", "false", or "no"
    env_observability_enabled = os.environ.get(ENV_OBSERVABILITY_ENABLED, "").lower()
    observability_enabled = env_observability_enabled not in ("0", "false", "no")
    observability_url = os.environ.get(ENV_OBSERVABILITY_URL, DEFAULT_OBSERVABILITY_URL)

    # DEBUG LOGGING - Observability configuration
    debug_log("load_config - OBSERVABILITY", {
        "enabled": observability_enabled,
        "url": observability_url,
    })

    # Part I: Return Config object
    config = Config(
        project_dir=project_dir,
        sessions_dir=sessions_dir,
        agents_dir=agents_dir,
        enable_logging=enable_logging,
        observability_enabled=observability_enabled,
        observability_url=observability_url,
    )

    # DEBUG LOGGING - Final config
    debug_log("load_config - FINAL CONFIG", {
        "project_dir": str(config.project_dir),
        "sessions_dir": str(config.sessions_dir),
        "agents_dir": str(config.agents_dir),
        "enable_logging": config.enable_logging,
        "observability_enabled": config.observability_enabled,
        "observability_url": config.observability_url,
    })

    return config
