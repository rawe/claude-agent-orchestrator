"""
Executor Configuration Management

Handles configuration loading for executor scripts with precedence:
CLI Flags > Environment Variables > Defaults (PWD)

Note: Session and agent management is now API-based via AgentCoordinator and AgentRegistry
services. The only directory configuration needed is project_dir for the working directory.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from utils import debug_log


# Environment variable names
ENV_PROJECT_DIR = "AGENT_ORCHESTRATOR_PROJECT_DIR"
ENV_ENABLE_LOGGING = "AGENT_ORCHESTRATOR_ENABLE_LOGGING"

# Agent Orchestrator API configuration (unified service for sessions + blueprints)
ENV_API_URL = "AGENT_ORCHESTRATOR_API_URL"
DEFAULT_API_URL = "http://127.0.0.1:8765"


def get_api_url() -> str:
    """Get Agent Orchestrator API URL from environment or default."""
    return os.environ.get(ENV_API_URL, DEFAULT_API_URL)


@dataclass
class Config:
    """Configuration for executor scripts."""

    project_dir: Path
    enable_logging: bool
    api_url: str


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


def load_config(
    cli_project_dir: Optional[str] = None,
) -> Config:
    """
    Load configuration with CLI > ENV > DEFAULT precedence.

    Args:
        cli_project_dir: Optional CLI override for project directory

    Returns:
        Config object with project_dir resolved to absolute path

    Raises:
        ValueError: If project_dir doesn't exist
    """
    # DEBUG LOGGING - Entry point
    debug_log("load_config - ENTRY", {
        "cwd": str(Path.cwd()),
        "cli_project_dir": cli_project_dir or "None",
    })

    # Read environment variables
    env_project_dir = os.environ.get(ENV_PROJECT_DIR)
    env_logging = os.environ.get(ENV_ENABLE_LOGGING, "").lower()

    # DEBUG LOGGING - Environment variables
    debug_log("load_config - ENV VARS", {
        "AGENT_ORCHESTRATOR_PROJECT_DIR": env_project_dir or "not set",
        "AGENT_ORCHESTRATOR_ENABLE_LOGGING": env_logging or "not set",
    })

    # Apply precedence for PROJECT_DIR: CLI > ENV > DEFAULT
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

    # Validate PROJECT_DIR: must exist and be readable
    if not project_dir.exists():
        raise ValueError(f"Project directory does not exist: {project_dir}")
    if not project_dir.is_dir():
        raise ValueError(f"Project directory is not a directory: {project_dir}")
    if not os.access(project_dir, os.R_OK):
        raise ValueError(f"Project directory is not readable: {project_dir}")

    # Parse logging flag: enable if value is "1", "true", or "yes"
    enable_logging = env_logging in ("1", "true", "yes")

    # Parse API URL configuration
    api_url = get_api_url()

    # DEBUG LOGGING - API configuration
    debug_log("load_config - API_URL", {
        "url": api_url,
    })

    # Return Config object
    config = Config(
        project_dir=project_dir,
        enable_logging=enable_logging,
        api_url=api_url,
    )

    # DEBUG LOGGING - Final config
    debug_log("load_config - FINAL CONFIG", {
        "project_dir": str(config.project_dir),
        "enable_logging": config.enable_logging,
        "api_url": config.api_url,
    })

    return config
