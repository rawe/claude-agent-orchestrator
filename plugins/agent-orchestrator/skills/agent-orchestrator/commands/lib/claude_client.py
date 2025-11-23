"""
Claude SDK Integration

Wrapper around Claude Agent SDK for session creation and resumption.
Implements async session execution with message streaming to .jsonl files.
Uses programmatic hooks for observability integration.
"""

from pathlib import Path
from typing import Optional
import json
import asyncio
import dataclasses
from datetime import datetime, UTC

from observability import (
    send_message,
    send_session_stop,
    set_observability_url,
    get_observability_url,
    update_session_metadata,
    user_prompt_hook,
    pre_tool_hook,
    post_tool_hook,
)


async def run_claude_session(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    session_name: Optional[str] = None,
    sessions_dir: Optional[Path] = None,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
    observability_enabled: bool = False,
    observability_url: str = "http://127.0.0.1:8765",
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
        observability_enabled: If True, send events to observability backend
        observability_url: Base URL of observability backend
        agent_name: Agent name (optional, for observability metadata)

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
    # Set observability URL for hook functions
    set_observability_url(observability_url)

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

    # Add programmatic hooks for observability if enabled
    if observability_enabled:
        try:
            from claude_agent_sdk.types import HookMatcher

            options.hooks = {
                # SessionStart hook not called by SDK - using fallback in message loop
                # "SessionStart": [
                #     HookMatcher(hooks=[session_start_hook]),
                # ],
                "UserPromptSubmit": [
                    HookMatcher(hooks=[user_prompt_hook]),
                ],
                #"PreToolUse": [
                #    HookMatcher(hooks=[pre_tool_hook]),
                #],
                "PostToolUse": [
                    HookMatcher(hooks=[post_tool_hook]),
                ],
                # Stop hook fires before message loop completes, so we send
                # session_stop manually after loop to ensure correct event order
                # "Stop": [
                #     HookMatcher(hooks=[session_stop_hook]),
                # ],
            }
        except ImportError as e:
            # If HookMatcher is not available, fall back to no hooks
            import sys
            print(
                f"Warning: Could not import HookMatcher for observability hooks: {e}",
                file=sys.stderr
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
                # Write each message to JSONL file (append mode)
                # Note: SDK messages are dataclasses
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

                            # STAGE 2: Update metadata with session_id immediately
                            # This makes the session resumable even while still running
                            # SystemMessage arrives BEFORE Claude starts processing, so this is early!
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

                            # Update observability backend with session metadata
                            # This happens once, right after we get the session_id from SystemMessage
                            # Since SystemMessage arrives first, this is sent BEFORE Claude processes!
                            if observability_enabled and session_name and not resume_session_id:
                                update_session_metadata(
                                    observability_url,
                                    session_id,
                                    session_name=session_name,
                                    project_dir=str(project_dir),
                                    agent_name=agent_name
                                )

                # Extract result from ResultMessage
                if isinstance(message, ResultMessage):
                    # Capture session_id if we somehow didn't get it from SystemMessage
                    if session_id is None:
                        session_id = message.session_id

                    # Capture result (overwrite each time to get final result)
                    result = message.result

                    # Send assistant message to observability
                    if observability_enabled and message.result:
                        send_message(
                            get_observability_url(),
                            session_id,
                            "assistant",
                            [{"type": "text", "text": message.result}]
                        )

            # Send session_stop after message loop completes
            # This ensures correct event order: assistant message before session_stop
            if observability_enabled and session_id:
                send_session_stop(get_observability_url(), session_id)

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
    observability_enabled: bool = False,
    observability_url: str = "http://127.0.0.1:8765",
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
        observability_enabled: If True, send events to observability backend
        observability_url: Base URL of observability backend
        agent_name: Agent name (optional, for observability metadata)

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
            observability_enabled=observability_enabled,
            observability_url=observability_url,
            agent_name=agent_name,
        )
    )
