"""
Common Utilities

Shared utility functions for error handling, I/O, and formatting.
"""

import sys
from pathlib import Path
from typing import Optional


def error(message: str, exit_code: int = 1) -> None:
    """
    Print error message to stderr and exit.

    TODO: Add color formatting (red text)
    """
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)


def success(message: str) -> None:
    """
    Print success message to stdout.

    TODO: Add color formatting (green text)
    """
    print(message)


def warning(message: str) -> None:
    """
    Print warning message to stderr.

    TODO: Add color formatting (yellow text)
    """
    print(f"Warning: {message}", file=sys.stderr)


def read_stdin() -> Optional[str]:
    """
    Read from stdin if available.

    Returns:
        Content from stdin or None if not available

    TODO: Implement stdin reading with proper detection
    """
    # TODO: Implement
    raise NotImplementedError("Stdin reading not yet implemented")


def read_prompt_input(flag_prompt: Optional[str]) -> str:
    """
    Read prompt from -p flag and/or stdin.

    Concatenates: flag_prompt + stdin (if both present)

    TODO: Implement combined prompt reading
    """
    # TODO: Implement
    raise NotImplementedError("Prompt input reading not yet implemented")


def ensure_dir(path: Path) -> None:
    """
    Ensure directory exists, create if needed.

    TODO: Implement with proper error handling
    """
    # TODO: Implement
    raise NotImplementedError("Directory creation not yet implemented")


def read_file_safe(path: Path) -> Optional[str]:
    """
    Safely read file contents.

    Returns None if file doesn't exist or can't be read.

    TODO: Implement with error handling
    """
    # TODO: Implement
    raise NotImplementedError("Safe file reading not yet implemented")


def write_file_safe(path: Path, content: str) -> bool:
    """
    Safely write file contents.

    Returns True on success, False on failure.

    TODO: Implement with error handling
    """
    # TODO: Implement
    raise NotImplementedError("Safe file writing not yet implemented")


def get_last_line(file: Path) -> Optional[str]:
    """
    Get the last line of a file efficiently.

    TODO: Implement efficient last line reading
    """
    # TODO: Implement
    raise NotImplementedError("Last line reading not yet implemented")


def get_first_line(file: Path) -> Optional[str]:
    """
    Get the first line of a file.

    TODO: Implement first line reading
    """
    # TODO: Implement
    raise NotImplementedError("First line reading not yet implemented")


def format_timestamp(dt) -> str:
    """
    Format datetime for display.

    TODO: Implement consistent timestamp formatting
    """
    # TODO: Implement
    raise NotImplementedError("Timestamp formatting not yet implemented")


def confirm(message: str) -> bool:
    """
    Ask user for yes/no confirmation.

    TODO: Implement interactive confirmation
    """
    # TODO: Implement
    raise NotImplementedError("Confirmation prompt not yet implemented")
