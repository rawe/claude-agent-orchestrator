"""
Claude SDK Integration

Wrapper around Claude Agent SDK for session creation and resumption.
Implements async session execution with message streaming to .jsonl files.
Uses SessionClient for API-based session management.
"""

from pathlib import Path
from typing import Optional
import json
import asyncio
import dataclasses
from datetime import datetime, UTC

from session_client import SessionClient, SessionClientError


async def run_claude_session(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    session_name: Optional[str] = None,
    sessions_dir: Optional[Path] = None,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
    session_manager_url: str = "http://127.0.0.1:8765",
    agent_name: Optional[str] = None,
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
        session_manager_url: Base URL of session manager API
        agent_name: Agent name (optional, for session metadata)

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
    # Create session client for API calls
    session_client = SessionClient(session_manager_url)

    # Import SDK here to give better error message if not installed
    try:
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage, SystemMessage
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

    # Import file backup toggle
    from config import FILE_BACKUP_ENABLED

    # Initialize tracking variables
    session_id = None
    result = None

    # Only create files if file backup is enabled
    if FILE_BACKUP_ENABLED:
        # Ensure parent directory exists
        session_file.parent.mkdir(parents=True, exist_ok=True)

        # Write user message to .jsonl first (before SDK streaming)
        # This creates a complete conversation history in one file
        user_message = {
            "type": "user_message",
            "content": prompt,
            "timestamp": datetime.now(UTC).isoformat()
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
                # Write each message to JSONL file (append mode) if file backup enabled
                # Note: SDK messages are dataclasses
                if FILE_BACKUP_ENABLED:
                    message_dict = dataclasses.asdict(message)
                    with open(session_file, 'a') as f:
                        json.dump(message_dict, f)
                        f.write('\n')

                # Extract session_id from FIRST SystemMessage (arrives early!)
                # SystemMessage with subtype='init' contains session_id in data dict
                if isinstance(message, SystemMessage) and session_id is None:
                    # Extract session_id from SystemMessage.data
                    if message.subtype == 'init' and message.data:
                        extracted_session_id = message.data.get('session_id')
                        if extracted_session_id:
                            session_id = extracted_session_id

                            # Create or update session via API
                            try:
                                if not resume_session_id:
                                    # New session: create via API
                                    session_client.create_session(
                                        session_id=session_id,
                                        session_name=session_name or session_id,
                                        project_dir=str(project_dir),
                                        agent_name=agent_name
                                    )
                                else:
                                    # Resume: update last_resumed_at
                                    session_client.update_session(
                                        session_id=session_id,
                                        last_resumed_at=datetime.now(UTC).isoformat()
                                    )
                            except SessionClientError as e:
                                # Don't fail the session if API call fails
                                import sys
                                print(f"Warning: Session API error: {e}", file=sys.stderr)

                            # Update file-based metadata as backup
                            if FILE_BACKUP_ENABLED and session_name and sessions_dir:
                                try:
                                    from session import update_session_id as _update_session_id
                                    _update_session_id(session_name, session_id, sessions_dir)
                                except Exception as e:
                                    import sys
                                    print(
                                        f"Warning: Failed to update session_id in metadata: {e}",
                                        file=sys.stderr
                                    )

                # Extract result from ResultMessage
                if isinstance(message, ResultMessage):
                    # Capture session_id if we somehow didn't get it from SystemMessage
                    if session_id is None:
                        session_id = message.session_id

                    # Capture result (overwrite each time to get final result)
                    result = message.result

                    # Send assistant message event to API
                    if message.result and session_id:
                        try:
                            session_client.add_event(session_id, {
                                "event_type": "message",
                                "session_id": session_id,
                                "session_name": session_name or session_id,
                                "timestamp": datetime.now(UTC).isoformat(),
                                "role": "assistant",
                                "content": [{"type": "text", "text": message.result}]
                            })
                        except SessionClientError:
                            pass  # Silent failure

            # Send session_stop event after message loop completes
            if session_id:
                try:
                    session_client.add_event(session_id, {
                        "event_type": "session_stop",
                        "session_id": session_id,
                        "session_name": session_name or session_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "exit_code": 0,
                        "reason": "completed"
                    })
                except SessionClientError:
                    pass  # Silent failure

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
    session_manager_url: str = "http://127.0.0.1:8765",
    agent_name: Optional[str] = None,
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
        session_manager_url: Base URL of session manager API
        agent_name: Agent name (optional, for session metadata)

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
            session_manager_url=session_manager_url,
            agent_name=agent_name,
        )
    )
