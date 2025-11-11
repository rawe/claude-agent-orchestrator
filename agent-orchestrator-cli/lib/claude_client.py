"""
Claude API Integration

Wrapper for Claude SDK to handle session creation and resumption.
"""

from pathlib import Path
from typing import Optional


def create_new_session(
    prompt: str,
    working_dir: Path,
    system_prompt: Optional[str] = None,
    mcp_config: Optional[dict] = None,
    session_file: Optional[Path] = None,
) -> tuple[str, str]:
    """
    Create a new Claude session.

    Args:
        prompt: Initial prompt for the session
        working_dir: Working directory for the session
        system_prompt: Optional system prompt (from agent)
        mcp_config: Optional MCP configuration (from agent)
        session_file: Optional file to stream output to

    Returns:
        (session_id, result)

    TODO: Implement using Claude SDK
    - Create session with prompt
    - Apply system prompt if provided
    - Configure MCP if provided
    - Stream response to file if provided
    - Return session ID and final result
    """
    # TODO: Implement
    raise NotImplementedError("Session creation not yet implemented")


def resume_session(
    session_id: str,
    prompt: str,
    working_dir: Path,
    session_file: Optional[Path] = None,
) -> str:
    """
    Resume an existing Claude session.

    Args:
        session_id: Existing session ID to resume
        prompt: New prompt to continue the conversation
        working_dir: Working directory for the session
        session_file: Optional file to append output to

    Returns:
        result: The response from Claude

    TODO: Implement using Claude SDK
    - Resume session with ID
    - Send new prompt
    - Stream response to file if provided
    - Return result
    """
    # TODO: Implement
    raise NotImplementedError("Session resumption not yet implemented")


def validate_api_key() -> bool:
    """
    Validate that Claude API key is configured.

    TODO: Check for ANTHROPIC_API_KEY environment variable
    """
    # TODO: Implement
    raise NotImplementedError("API key validation not yet implemented")
