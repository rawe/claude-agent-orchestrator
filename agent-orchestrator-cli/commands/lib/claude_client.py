"""
Claude SDK Integration

Wrapper around Claude Agent SDK for session creation and resumption.
Implements async session execution with message streaming to .jsonl files.
"""

from pathlib import Path
from typing import Optional
import json
import asyncio


async def run_claude_session(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
) -> tuple[str, str]:
    """
    Run Claude session and stream output to .jsonl file.

    This function uses the Claude Agent SDK to create or resume a session,
    streaming all messages to a JSONL file for persistence and later replay.

    Args:
        prompt: User prompt (may include prepended system prompt from agent)
        session_file: Path to .jsonl file to append messages
        project_dir: Working directory for Claude (sets cwd)
        mcp_servers: MCP server configuration dict (from agent.mcp.json)
        resume_session_id: If provided, resume existing session

    Returns:
        Tuple of (session_id, result)

    Raises:
        ValueError: If session_id or result not found in messages
        ImportError: If claude-agent-sdk is not installed
        Exception: SDK errors are propagated

    Example:
        >>> session_file = Path("/tmp/test.jsonl")
        >>> project_dir = Path.cwd()
        >>> session_id, result = await run_claude_session(
        ...     prompt="What is 2+2?",
        ...     session_file=session_file,
        ...     project_dir=project_dir
        ... )
    """
    # Import SDK here to give better error message if not installed
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError as e:
        raise ImportError(
            "claude-agent-sdk is not installed. "
            "Commands using the SDK should have 'claude-agent-sdk' "
            "in their uv script header dependencies."
        ) from e

    # Build ClaudeAgentOptions
    options = ClaudeAgentOptions(
        cwd=str(project_dir.resolve()),
        permission_mode="bypassPermissions",
    )

    # Add resume session ID if provided
    if resume_session_id:
        options.resume = resume_session_id

    # Add MCP servers if provided
    if mcp_servers:
        options.mcp_servers = mcp_servers

    # Initialize tracking variables
    session_id = None
    result = None

    # Ensure parent directory exists
    session_file.parent.mkdir(parents=True, exist_ok=True)

    # Stream session and write to file
    try:
        async for message in query(prompt=prompt, options=options):
            # Write each message to JSONL file (append mode)
            with open(session_file, 'a') as f:
                json.dump(message.model_dump(), f)
                f.write('\n')

            # Capture session_id from first message that has it
            if session_id is None and hasattr(message, 'session_id'):
                session_id = message.session_id

            # Capture result from last message that has it (overwrite each time)
            if hasattr(message, 'result'):
                result = message.result

    except Exception as e:
        # Propagate SDK errors with context
        raise Exception(f"Claude SDK error during session execution: {e}") from e

    # Validate we received required data
    if not session_id:
        raise ValueError(
            "No session_id received from Claude SDK. "
            "This may indicate an SDK version mismatch or API error."
        )

    if not result:
        raise ValueError(
            "No result received from Claude SDK. "
            "The session may have been interrupted or encountered an error."
        )

    return session_id, result


def run_session_sync(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
) -> tuple[str, str]:
    """
    Synchronous wrapper for run_claude_session.

    This allows command scripts to remain synchronous while using
    the SDK's async API internally.

    Args:
        prompt: User prompt (may include prepended system prompt from agent)
        session_file: Path to .jsonl file to append messages
        project_dir: Working directory for Claude (sets cwd)
        mcp_servers: MCP server configuration dict (from agent.mcp.json)
        resume_session_id: If provided, resume existing session

    Returns:
        Tuple of (session_id, result)

    Raises:
        ValueError: If session_id or result not found in messages
        ImportError: If claude-agent-sdk is not installed
        Exception: SDK errors are propagated

    Example:
        >>> session_file = Path("/tmp/test.jsonl")
        >>> project_dir = Path.cwd()
        >>> session_id, result = run_session_sync(
        ...     prompt="What is 2+2?",
        ...     session_file=session_file,
        ...     project_dir=project_dir
        ... )
    """
    return asyncio.run(
        run_claude_session(
            prompt=prompt,
            session_file=session_file,
            project_dir=project_dir,
            mcp_servers=mcp_servers,
            resume_session_id=resume_session_id,
        )
    )
