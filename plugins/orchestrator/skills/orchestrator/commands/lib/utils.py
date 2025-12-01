"""
Common Utilities

Shared utility functions for error handling, I/O, and formatting.
"""

import os
import sys
import traceback
from pathlib import Path
from typing import Optional, Any
from datetime import datetime


# ============================================================================
# DEBUG LOGGING - TEMPORARY
# This is temporary debugging infrastructure to diagnose session directory
# path resolution issues. Should be removed after debugging is complete.
# ============================================================================

# CONFIGURATION: Set to True to enable debug logging, False to disable
ENABLE_DEBUG_LOGGING = False

# CONFIGURATION: Set the absolute path where debug log should be written
# Example: "/tmp/debug.log" or use project root as shown below
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DEBUG_LOG_PATH = _PROJECT_ROOT / "debug-session-path.log"


def debug_log(context: str, data: dict[str, Any]) -> None:
    """
    Append debug information to hardcoded log file.

    This is a TEMPORARY debugging mechanism for diagnosing session directory
    path resolution issues. It logs to a hardcoded path and should be easy to
    remove once the issue is resolved.

    Args:
        context: Description of what is being logged (e.g., "resolve_absolute_path")
        data: Dictionary of key-value pairs to log
    """
    # Check if debug logging is enabled
    if not ENABLE_DEBUG_LOGGING:
        return

    try:
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Determine calling command by inspecting call stack
        caller = _get_calling_command()

        # Build log entry
        lines = [
            "=" * 80,
            f"[{timestamp}] {context}",
            f"Command: {caller}",
        ]

        # Add data items
        for key, value in data.items():
            lines.append(f"  {key}: {value}")

        lines.append("")  # Blank line for readability

        log_entry = "\n".join(lines)

        # Append to log file (create if doesn't exist)
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(log_entry)

    except Exception as e:
        # Don't break the command if logging fails
        # Optionally print to stderr for visibility
        print(f"Debug logging failed: {e}", file=sys.stderr)


def _get_calling_command() -> str:
    """
    Determine which command is running by inspecting the call stack.

    Returns:
        Command name (e.g., "ao-start") or "unknown"
    """
    try:
        # Get call stack
        stack = traceback.extract_stack()

        # Look for command file in stack (files without .py extension)
        for frame in stack:
            filename = Path(frame.filename).name
            if filename.startswith("ao-") and not filename.endswith(".py"):
                return filename

        return "unknown"
    except Exception:
        return "unknown"


# ============================================================================
# END DEBUG LOGGING
# ============================================================================


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
