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

    Flushes stderr before exiting to ensure error message is captured
    when running as a subprocess with piped output.

    Args:
        message: Error message to display
        exit_code: Exit code (default: 1)
    """
    print(f"Error: {message}", file=sys.stderr)
    sys.stderr.flush()
    sys.exit(exit_code)


def ensure_directory_exists(path: Path) -> None:
    """
    Create directory if it doesn't exist.

    Args:
        path: Directory path to create
    """
    path.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# Autonomous Agent Input Formatting
# ==============================================================================


def format_autonomous_inputs(parameters: dict) -> str:
    """
    Format parameters for autonomous agents into a prompt string.

    For autonomous agents with custom parameters_schema, this function:
    1. Extracts the 'prompt' from parameters (required)
    2. Extracts additional parameters (those not 'prompt')
    3. Formats additional parameters as an inputs block
    4. Returns formatted prompt with inputs prepended

    If there are no additional parameters (just prompt), returns the prompt as-is.

    Args:
        parameters: Dict containing 'prompt' and optionally other parameters

    Returns:
        Formatted prompt string with inputs prepended (if any)

    Raises:
        ValueError: If 'prompt' is missing from parameters

    Example:
        >>> params = {"prompt": "Summarize this", "topic": "AI", "max_words": 100}
        >>> format_autonomous_inputs(params)
        '<inputs>
        topic: AI
        max_words: 100
        </inputs>

        Summarize this'
    """
    if "prompt" not in parameters:
        raise ValueError("Missing required 'prompt' in parameters for autonomous agent")

    prompt = parameters["prompt"]

    # Get additional parameters (exclude 'prompt')
    additional_params = {k: v for k, v in parameters.items() if k != "prompt"}

    # If no additional params, return prompt as-is
    if not additional_params:
        return prompt

    # Format additional parameters as inputs block
    lines = ["<inputs>"]
    for key, value in additional_params.items():
        # Handle different value types
        if isinstance(value, str):
            # Multi-line strings get special formatting
            if "\n" in value:
                lines.append(f"{key}:")
                for line in value.split("\n"):
                    lines.append(f"  {line}")
            else:
                lines.append(f"{key}: {value}")
        elif isinstance(value, (list, dict)):
            # JSON-like structures
            import json
            lines.append(f"{key}: {json.dumps(value)}")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {value}")
    lines.append("</inputs>")
    lines.append("")  # Empty line before prompt

    # Combine inputs block with prompt
    inputs_block = "\n".join(lines)
    return f"{inputs_block}\n{prompt}"


