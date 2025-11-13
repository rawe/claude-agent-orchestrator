"""
Claude SDK Integration

Wrapper around Claude Agent SDK for session creation and resumption.
Implements async session execution with message streaming to .jsonl files.
"""

from pathlib import Path
from typing import Optional
import json
import asyncio
import dataclasses
from datetime import datetime


async def run_claude_session(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    session_name: Optional[str] = None,
    sessions_dir: Optional[Path] = None,
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
        session_name: Session name (required for Stage 2 metadata update)
        sessions_dir: Sessions directory (required for Stage 2 metadata update)
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
        ...     project_dir=project_dir,
        ...     session_name="test",
        ...     sessions_dir=Path("/tmp/sessions")
        ... )
    """
    # Import SDK here to give better error message if not installed
    try:
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage
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
        setting_sources=["user", "project", "local"],
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

    # Write user message to .jsonl first (before SDK streaming)
    # This creates a complete conversation history in one file
    user_message = {
        "type": "user_message",
        "content": prompt,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    with open(session_file, 'a') as f:
        json.dump(user_message, f)
        f.write('\n')

    # Stream session and write to file using ClaudeSDKClient
    try:
        async with ClaudeSDKClient(options=options) as client:
            # Send the query
            await client.query(prompt)

            # Stream messages from client
            async for message in client.receive_response():
                # Write each message to JSONL file (append mode)
                # Note: SDK messages are dataclasses
                with open(session_file, 'a') as f:
                    json.dump(dataclasses.asdict(message), f)
                    f.write('\n')

                # Extract session_id and result from ResultMessage
                if isinstance(message, ResultMessage):
                    # Capture session_id from first ResultMessage
                    if session_id is None:
                        session_id = message.session_id

                        # STAGE 2: Update metadata with session_id immediately
                        # This makes the session resumable even while still running
                        if session_name and sessions_dir:
                            try:
                                from session import update_session_id as _update_session_id
                                _update_session_id(session_name, session_id, sessions_dir)
                            except Exception as e:
                                # Don't fail the session if metadata update fails
                                # Just log to stderr for debugging
                                import sys
                                print(
                                    f"Warning: Failed to update session_id in metadata: {e}",
                                    file=sys.stderr
                                )

                    # Capture result (overwrite each time to get final result)
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
    session_name: Optional[str] = None,
    sessions_dir: Optional[Path] = None,
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
        session_name: Session name (required for Stage 2 metadata update)
        sessions_dir: Sessions directory (required for Stage 2 metadata update)
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
        ...     project_dir=project_dir,
        ...     session_name="test",
        ...     sessions_dir=Path("/tmp/sessions")
        ... )
    """
    return asyncio.run(
        run_claude_session(
            prompt=prompt,
            session_file=session_file,
            project_dir=project_dir,
            session_name=session_name,
            sessions_dir=sessions_dir,
            mcp_servers=mcp_servers,
            resume_session_id=resume_session_id,
        )
    )
