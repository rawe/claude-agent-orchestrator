"""
Common Utilities

Shared utility functions for error handling, I/O, and formatting.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def get_prompt_from_args_and_stdin(prompt_arg: Optional[str]) -> str:
    """
    Get prompt from -p flag and/or stdin.

    Implementation (from bash get_prompt):
    1. Initialize: final_prompt = ""
    2. If prompt_arg provided: final_prompt = prompt_arg
    3. Check if stdin has data:
       - Use sys.stdin.isatty() - False means stdin is piped
       - If not isatty():
           stdin_content = sys.stdin.read()
           if stdin_content:
               if final_prompt:
                   final_prompt = final_prompt + "\n" + stdin_content
               else:
                   final_prompt = stdin_content
    4. If final_prompt is empty: raise ValueError("No prompt provided")
    5. Return final_prompt

    Args:
        prompt_arg: Optional prompt from -p CLI flag

    Returns:
        Combined prompt from -p flag and/or stdin

    Raises:
        ValueError: If no prompt provided from either source
    """
    final_prompt = ""

    # Add prompt from -p flag if provided
    if prompt_arg:
        final_prompt = prompt_arg

    # Check if stdin has data (not a terminal)
    if not sys.stdin.isatty():
        stdin_content = sys.stdin.read()
        if stdin_content:
            # Combine with -p flag if both present
            if final_prompt:
                final_prompt = final_prompt + "\n" + stdin_content
            else:
                final_prompt = stdin_content

    # Validate we got something
    if not final_prompt:
        raise ValueError("No prompt provided. Use -p flag or pipe content to stdin.")

    return final_prompt


def error_exit(message: str, exit_code: int = 1) -> None:
    """
    Print error message to stderr and exit.

    Args:
        message: Error message to display
        exit_code: Exit code (default: 1)
    """
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)


def ensure_directory_exists(path: Path) -> None:
    """
    Create directory if it doesn't exist.

    Args:
        path: Directory path to create
    """
    path.mkdir(parents=True, exist_ok=True)


def log_command(
    session_name: str,
    command_type: str,
    agent_name: Optional[str],
    mcp_config_path: Optional[str],
    full_command: str,
    prompt: str,
    sessions_dir: Path,
    project_dir: Path,
    agents_dir: Path,
    enable_logging: bool,
) -> None:
    """
    Log command execution to .log file (if logging enabled).

    Implementation (from bash log_command):
    1. Check if logging enabled: if not enable_logging: return
    2. Build log entry with timestamp, command details, environment
    3. Append to {session_name}.log file

    Args:
        session_name: Name of the session
        command_type: Type of command (e.g., "new", "resume")
        agent_name: Name of agent (or None)
        mcp_config_path: Path to MCP config (or None)
        full_command: Complete command line that was executed
        prompt: User prompt
        sessions_dir: Sessions directory path
        project_dir: Project directory path
        agents_dir: Agents directory path
        enable_logging: Whether logging is enabled
    """
    # Skip if logging not enabled
    if not enable_logging:
        return

    # Build log entry
    timestamp = datetime.utcnow().isoformat() + "Z"
    log_file = sessions_dir / f"{session_name}.log"

    entry = f"""================================================================================
Timestamp: {timestamp}
Command Type: {command_type}
Working Directory: {project_dir}
Agents Directory: {agents_dir}
Agent Name: {agent_name or "none"}
MCP Config: {mcp_config_path or "none"}

Full Command:
{full_command}

Environment:
AGENT_ORCHESTRATOR_PROJECT_DIR={os.environ.get('AGENT_ORCHESTRATOR_PROJECT_DIR', 'not set')}
AGENT_ORCHESTRATOR_AGENTS_DIR={os.environ.get('AGENT_ORCHESTRATOR_AGENTS_DIR', 'not set')}
AGENT_ORCHESTRATOR_SESSIONS_DIR={os.environ.get('AGENT_ORCHESTRATOR_SESSIONS_DIR', 'not set')}
AGENT_ORCHESTRATOR_ENABLE_LOGGING={os.environ.get('AGENT_ORCHESTRATOR_ENABLE_LOGGING', 'not set')}

Prompt:
{prompt}
================================================================================

"""

    # Append to log file
    with open(log_file, 'a') as f:
        f.write(entry)


def log_result(
    session_name: str,
    result: str,
    sessions_dir: Path,
    enable_logging: bool,
) -> None:
    """
    Log result to .log file (if logging enabled).

    Args:
        session_name: Name of the session
        result: Result text to log
        sessions_dir: Sessions directory path
        enable_logging: Whether logging is enabled
    """
    # Skip if logging not enabled
    if not enable_logging:
        return

    # Build result entry
    timestamp = datetime.utcnow().isoformat() + "Z"
    log_file = sessions_dir / f"{session_name}.log"

    entry = f"""Result (at {timestamp}):
{result}
================================================================================

"""

    # Append to log file
    with open(log_file, 'a') as f:
        f.write(entry)
