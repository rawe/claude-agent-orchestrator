"""
Claude SDK Integration

Wrapper around Claude Agent SDK for session creation and resumption.
Uses SessionEventEmitter to communicate with the Runner Gateway.

The Runner Gateway enriches requests with runner-owned data:
- hostname (machine where runner is running)
- executor_profile (profile name like "coding", "research")

The executor only sends data it owns:
- executor_session_id (from Claude SDK)
- project_dir (per-invocation working directory)

NOTE: This module expects the runner lib to already be in sys.path.
      The parent executor (ao-claude-code-exec) is responsible for
      setting up the path before importing this module.

Note: Uses session_id (coordinator-generated) per ADR-010.
      The Claude SDK's session_id is stored as executor_session_id.
"""

from pathlib import Path
from typing import Optional
import asyncio
import json

from mcp_transform import transform_mcp_servers_for_claude_code
from claude_config import ClaudeConfigKey, get_claude_config
from session_events import SessionEventEmitter, set_hook_emitter, post_tool_hook


async def run_claude_session(
    prompt: str,
    project_dir: Path,
    session_id: str,
    mcp_servers: Optional[dict] = None,
    resume_executor_session_id: Optional[str] = None,
    api_url: str = "http://127.0.0.1:8765",
    agent_name: Optional[str] = None,
    executor_config: Optional[dict] = None,
    system_prompt: Optional[str] = None,
    output_schema: Optional[dict] = None,
) -> tuple[str, str]:
    """
    Run Claude session with API-based session management.

    This function uses the Claude Agent SDK to create or resume a session,
    with session state managed via the Runner Gateway (which forwards to
    the Agent Coordinator).

    Note: Auth and runner-owned data (hostname, executor_profile) are handled
    by the Runner Gateway - executors only send data they own.

    Args:
        prompt: User prompt
        project_dir: Working directory for Claude (sets cwd)
        session_id: Coordinator-generated session ID (ADR-010)
        mcp_servers: MCP server configuration dict (from agent blueprint)
        resume_executor_session_id: If provided, resume existing Claude SDK session
        api_url: Base URL of Runner Gateway
        agent_name: Agent name (optional, for session metadata)
        executor_config: Executor-specific config (permission_mode, setting_sources, model)
        system_prompt: System prompt for Claude (only used for new sessions, not resume)
        output_schema: JSON Schema for structured output. If provided, uses SDK
            native output_format for validated JSON responses.

    Returns:
        Tuple of (executor_session_id, result) where executor_session_id is
        the Claude SDK's session UUID

    Raises:
        ValueError: If session_id or result not found, or structured output fails
        ImportError: If claude-agent-sdk is not installed
        Exception: SDK errors are propagated
    """
    # Create event emitter for session lifecycle events
    emitter = SessionEventEmitter(api_url, session_id)

    # Import SDK here to give better error message if not installed
    try:
        from claude_agent_sdk import query as sdk_query, ClaudeAgentOptions, ResultMessage, SystemMessage
    except ImportError as e:
        raise ImportError(
            "claude-agent-sdk is not installed. "
            "Commands using the SDK should have 'claude-agent-sdk' "
            "in their uv script header dependencies."
        ) from e

    # Get executor config with defaults
    claude_config = get_claude_config(executor_config)

    # Build ClaudeAgentOptions
    options = ClaudeAgentOptions(
        cwd=str(project_dir.resolve()),
        permission_mode=claude_config[ClaudeConfigKey.PERMISSION_MODE],
        setting_sources=claude_config[ClaudeConfigKey.SETTING_SOURCES],
    )

    # Set model if specified (None = use SDK default)
    if claude_config[ClaudeConfigKey.MODEL]:
        options.model = claude_config[ClaudeConfigKey.MODEL]

    # Set system prompt if provided (only for new sessions, not resume)
    if system_prompt:
        options.system_prompt = system_prompt

    # Use SDK native structured outputs (handles validation and retries internally)
    if output_schema:
        options.output_format = {"type": "json_schema", "schema": output_schema}

    # Add programmatic hooks for post_tool events
    try:
        from claude_agent_sdk.types import HookMatcher

        options.hooks = {
            "PostToolUse": [
                HookMatcher(hooks=[post_tool_hook]),
            ],
        }
    except ImportError as e:
        # If HookMatcher is not available, continue without hooks
        import sys
        print(
            f"Warning: Could not import HookMatcher for hooks: {e}",
            file=sys.stderr
        )

    # Add resume session ID if provided (use executor_session_id for SDK resume)
    if resume_executor_session_id:
        options.resume = resume_executor_session_id

    # Transform and add MCP servers (coordinator format → Claude Code format)
    if mcp_servers:
        options.mcp_servers = transform_mcp_servers_for_claude_code(mcp_servers)

    # Initialize tracking variables
    executor_session_id = None
    result = None
    structured_output = None  # SDK structured output (when output_format is set)

    # Helper function to process message stream and extract result
    # skip_assistant_message: When True, don't emit assistant message events.
    # Used for structured output agents where only the result event matters.
    async def process_message_stream(messages, current_prompt: str, skip_assistant_message: bool = False):
        nonlocal executor_session_id, result, structured_output

        stream_result = None

        async for message in messages:
            # Extract session_id from FIRST SystemMessage (arrives early!)
            # Only do binding on first query, not retries
            if isinstance(message, SystemMessage) and executor_session_id is None:
                if message.subtype == 'init' and message.data:
                    extracted_session_id = message.data.get('session_id')
                    if extracted_session_id:
                        executor_session_id = extracted_session_id

                        # Bind session and set up hook context (ADR-010)
                        emitter.bind(executor_session_id, str(project_dir))
                        set_hook_emitter(emitter)

                        # For resume, update last_resumed_at
                        if resume_executor_session_id:
                            emitter.update_resumed()

                        # Send user message event
                        emitter.emit_user_message(current_prompt)

            # Extract result from ResultMessage
            if isinstance(message, ResultMessage):
                if executor_session_id is None:
                    executor_session_id = message.session_id

                stream_result = message.result

                # Capture SDK structured output (available when output_format is set)
                if getattr(message, 'structured_output', None) is not None:
                    structured_output = message.structured_output

                # Send assistant message event (for conversation history)
                # Skip for structured output agents - they only emit result events
                if message.result and not skip_assistant_message:
                    emitter.emit_assistant_message(message.result)

        return stream_result

    # Run session using sdk query() function (uses --print mode, not streaming)
    try:
        # Send the initial query and process response
        skip_messages = output_schema is not None
        result = await process_message_stream(
            sdk_query(prompt=prompt, options=options),
            prompt,
            skip_assistant_message=skip_messages,
        )

        # Send result event based on output type
        if output_schema:
            # Structured output: SDK handles validation and retries internally
            if structured_output is not None:
                emitter.emit_result(result_data=structured_output)
                # Return structured JSON as the result text
                result = json.dumps(structured_output)
            else:
                raise ValueError(
                    "Structured output validation failed. "
                    "The agent could not produce valid JSON matching the output schema."
                )

        elif result:
            # No output schema - send result event with text
            emitter.emit_result(result_text=result)

        # NOTE: Session completion is signaled by the agent runner's supervisor
        # via POST /runner/runs/{run_id}/completed when this process exits.

    except Exception as e:
        # Propagate SDK errors with context
        raise Exception(f"Claude SDK error during session execution: {e}") from e

    # Validate we received required data
    if not executor_session_id:
        raise ValueError(
            "No session_id received from Claude SDK. "
            "This may indicate an SDK version mismatch or API error."
        )

    if not result:
        raise ValueError(
            "No result received from Claude SDK. "
            "The session may have been interrupted or encountered an error."
        )

    return executor_session_id, result


def run_session_sync(
    prompt: str,
    project_dir: Path,
    session_id: str,
    mcp_servers: Optional[dict] = None,
    resume_executor_session_id: Optional[str] = None,
    api_url: str = "http://127.0.0.1:8765",
    agent_name: Optional[str] = None,
    executor_config: Optional[dict] = None,
    system_prompt: Optional[str] = None,
    output_schema: Optional[dict] = None,
) -> tuple[str, str]:
    """
    Synchronous wrapper for run_claude_session.

    This allows command scripts to remain synchronous while using
    the SDK's async API internally.

    Note: Auth and runner-owned data are handled by the Runner Gateway.
    """
    return asyncio.run(
        run_claude_session(
            prompt=prompt,
            project_dir=project_dir,
            session_id=session_id,
            mcp_servers=mcp_servers,
            resume_executor_session_id=resume_executor_session_id,
            api_url=api_url,
            agent_name=agent_name,
            executor_config=executor_config,
            system_prompt=system_prompt,
            output_schema=output_schema,
        )
    )
