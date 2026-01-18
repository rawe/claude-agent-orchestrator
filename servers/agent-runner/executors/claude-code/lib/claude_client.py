"""
Claude SDK Integration

Wrapper around Claude Agent SDK for session creation and resumption.
Uses SessionClient to communicate with the Runner Gateway.

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
from dataclasses import dataclass, field
import asyncio
import copy
import json
import os
import re
from datetime import datetime, UTC

from enum import StrEnum

from session_client import SessionClient, SessionClientError


# =============================================================================
# Output Schema Validation
# =============================================================================

class OutputSchemaValidationError(Exception):
    """Raised when output validation fails after retries."""
    def __init__(self, message: str, errors: list[dict]):
        super().__init__(message)
        self.errors = errors


@dataclass
class ValidationResult:
    """Result of validating agent output against JSON Schema."""
    valid: bool
    errors: list[dict] = field(default_factory=list)


def validate_against_schema(output: dict | None, schema: dict) -> ValidationResult:
    """Validate agent output against JSON Schema.

    Args:
        output: The extracted JSON output from the agent
        schema: The JSON Schema to validate against

    Returns:
        ValidationResult with valid=True if valid, or valid=False with errors
    """
    from jsonschema import Draft7Validator

    if output is None:
        return ValidationResult(
            valid=False,
            errors=[{"path": "$", "message": "No JSON output found but output_schema requires structured output"}]
        )

    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(output))

    if not errors:
        return ValidationResult(valid=True)

    return ValidationResult(
        valid=False,
        errors=[
            {
                "path": f"$.{'.'.join(str(p) for p in e.absolute_path)}" if e.absolute_path else "$",
                "message": e.message,
            }
            for e in errors
        ]
    )


def extract_json_from_response(text: str) -> dict | None:
    """Extract JSON object from AI response text.

    Tries to find JSON in code blocks first, then raw JSON objects.

    Args:
        text: The AI response text

    Returns:
        Extracted JSON dict or None if no valid JSON found
    """
    # Try to find JSON in code blocks first
    code_block_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def enrich_system_prompt_with_output_schema(system_prompt: str | None, output_schema: dict | None) -> str | None:
    """Append output schema instructions to system prompt.

    Args:
        system_prompt: The original system prompt (may be None)
        output_schema: The JSON Schema for output validation (may be None)

    Returns:
        Enriched system prompt or None if no schema
    """
    if not output_schema:
        return system_prompt

    base_prompt = system_prompt or ""

    output_instructions = f"""

## Required Output Format

You MUST provide structured output as JSON conforming to this schema:

```json
{json.dumps(output_schema, indent=2)}
```

Your final response MUST be valid JSON that matches this schema exactly. Output ONLY the JSON, no additional text."""

    return base_prompt + output_instructions


def build_validation_error_prompt(errors: list[dict], schema: dict) -> str:
    """Build prompt for schema validation retry.

    Args:
        errors: List of validation errors
        schema: The JSON Schema that failed validation

    Returns:
        Prompt instructing the agent to correct its output
    """
    error_lines = "\n".join(f"- {e['path']}: {e['message']}" for e in errors)

    return f"""<output-validation-error>
Your output did not match the required schema.

## Validation Errors
{error_lines}

## Required Schema
```json
{json.dumps(schema, indent=2)}
```

Please provide output matching the schema exactly. Output ONLY valid JSON.
</output-validation-error>"""


# =============================================================================
# Claude Code Executor Config
# =============================================================================

class ClaudeConfigKey(StrEnum):
    """Keys for claude-code executor configuration."""
    PERMISSION_MODE = "permission_mode"
    SETTING_SOURCES = "setting_sources"
    MODEL = "model"


# Default values when executor_config is missing or incomplete
EXECUTOR_CONFIG_DEFAULTS = {
    ClaudeConfigKey.PERMISSION_MODE: "bypassPermissions",
    ClaudeConfigKey.SETTING_SOURCES: ["user", "project", "local"],
    ClaudeConfigKey.MODEL: None,  # None = use SDK default
}


def get_claude_config(executor_config: Optional[dict]) -> dict:
    """
    Extract claude-code specific configuration with defaults.

    Args:
        executor_config: Raw executor_config dict from invocation (may be None)

    Returns:
        Dict with permission_mode, setting_sources, model (with defaults applied)
    """
    config = executor_config or {}
    return {
        ClaudeConfigKey.PERMISSION_MODE: config.get(
            ClaudeConfigKey.PERMISSION_MODE,
            EXECUTOR_CONFIG_DEFAULTS[ClaudeConfigKey.PERMISSION_MODE]
        ),
        ClaudeConfigKey.SETTING_SOURCES: config.get(
            ClaudeConfigKey.SETTING_SOURCES,
            EXECUTOR_CONFIG_DEFAULTS[ClaudeConfigKey.SETTING_SOURCES]
        ),
        ClaudeConfigKey.MODEL: config.get(
            ClaudeConfigKey.MODEL,
            EXECUTOR_CONFIG_DEFAULTS[ClaudeConfigKey.MODEL]
        ),
    }


# =============================================================================
# MCP Config Placeholder Replacement
# =============================================================================

def _replace_env_placeholders(value: str) -> str:
    """
    Replace ${VAR_NAME} placeholders with environment variable values.

    If the environment variable is not set, the placeholder is left unchanged.
    """
    def replace_match(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(r'\$\{([^}]+)\}', replace_match, value)


def _process_mcp_servers(mcp_servers: dict) -> dict:
    """
    Process MCP server config to replace environment variable placeholders.

    Handles ${AGENT_SESSION_ID} and similar placeholders in header values.
    Creates a deep copy to avoid modifying the original config.

    Example:
        Input:  {"headers": {"X-Agent-Session-Id": "${AGENT_SESSION_ID}"}}
        Output: {"headers": {"X-Agent-Session-Id": "ses_abc123def456"}}
    """
    result = copy.deepcopy(mcp_servers)

    for server_name, server_config in result.items():
        if isinstance(server_config, dict):
            # Process headers if present (HTTP servers)
            headers = server_config.get('headers')
            if isinstance(headers, dict):
                for header_name, header_value in headers.items():
                    if isinstance(header_value, str):
                        headers[header_name] = _replace_env_placeholders(header_value)

            # Process env if present (stdio servers)
            env = server_config.get('env')
            if isinstance(env, dict):
                for env_name, env_value in env.items():
                    if isinstance(env_value, str):
                        env[env_name] = _replace_env_placeholders(env_value)

    return result


# =============================================================================
# Module-level state for SDK hooks
# =============================================================================
_session_client: Optional[SessionClient] = None
_current_session_id: Optional[str] = None


def _set_hook_context(
    client: SessionClient,
    session_id: str,
) -> None:
    """Set the session context for hook functions."""
    global _session_client, _current_session_id
    _session_client = client
    _current_session_id = session_id


# =============================================================================
# SDK Hook Functions
# =============================================================================

async def post_tool_hook(
    input_data: dict,
    tool_use_id: Optional[str],
    context: dict
) -> dict:
    """
    PostToolUse hook - sends post_tool event to session manager.
    """
    if _session_client and _current_session_id:
        try:
            _session_client.add_event(_current_session_id, {
                "event_type": "post_tool",
                "session_id": _current_session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "tool_name": input_data.get("tool_name", "unknown"),
                "tool_input": input_data.get("tool_input", {}),
                "tool_output": input_data.get("tool_response", ""),
                "error": input_data.get("error"),
            })
        except SessionClientError:
            pass  # Silent failure - don't block agent execution
    return {}


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
        output_schema: JSON Schema for output validation. If provided, the agent's
            output will be validated against this schema and retried once on failure.

    Returns:
        Tuple of (executor_session_id, result) where executor_session_id is
        the Claude SDK's session UUID

    Raises:
        ValueError: If session_id or result not found in messages
        ImportError: If claude-agent-sdk is not installed
        OutputSchemaValidationError: If output validation fails after retry
        Exception: SDK errors are propagated

    Example:
        >>> project_dir = Path.cwd()
        >>> executor_session_id, result = await run_claude_session(
        ...     prompt="What is 2+2?",
        ...     project_dir=project_dir,
        ...     session_id="ses_abc123def456"
        ... )
    """
    # Create session client for API calls (communicates via Runner Gateway)
    session_client = SessionClient(api_url)

    # Import SDK here to give better error message if not installed
    try:
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage, SystemMessage
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
    # Enrich with output schema instructions if output_schema is defined
    enriched_system_prompt = enrich_system_prompt_with_output_schema(system_prompt, output_schema)
    if enriched_system_prompt:
        options.system_prompt = enriched_system_prompt

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

    # Add MCP servers if provided (with placeholder replacement)
    if mcp_servers:
        options.mcp_servers = _process_mcp_servers(mcp_servers)

    # Initialize tracking variables
    executor_session_id = None
    result = None
    session_bound = False  # Track if we've bound the session

    # Helper function to process message stream and extract result
    # skip_assistant_message: When True, don't emit assistant message events.
    # Used for structured output agents where only the result event matters.
    async def process_message_stream(client, current_prompt: str, skip_assistant_message: bool = False):
        nonlocal executor_session_id, result, session_bound

        stream_result = None

        async for message in client.receive_response():
            # Extract session_id from FIRST SystemMessage (arrives early!)
            # Only do binding on first query, not retries
            if isinstance(message, SystemMessage) and executor_session_id is None:
                if message.subtype == 'init' and message.data:
                    extracted_session_id = message.data.get('session_id')
                    if extracted_session_id:
                        executor_session_id = extracted_session_id

                        # Bind session executor (ADR-010)
                        if not session_bound:
                            try:
                                session_client.bind(
                                    session_id=session_id,
                                    executor_session_id=executor_session_id,
                                    project_dir=str(project_dir),
                                )
                                session_bound = True
                            except SessionClientError as e:
                                import sys
                                print(f"Warning: Session bind failed: {e}", file=sys.stderr)

                            # Set hook context so post_tool_hook can send events
                            _set_hook_context(session_client, session_id)

                            # For resume, update last_resumed_at
                            if resume_executor_session_id:
                                try:
                                    session_client.update_session(
                                        session_id=session_id,
                                        last_resumed_at=datetime.now(UTC).isoformat()
                                    )
                                except SessionClientError as e:
                                    import sys
                                    print(f"Warning: Session update failed: {e}", file=sys.stderr)

                        # Send user message event (for both initial and retry prompts)
                        try:
                            session_client.add_event(session_id, {
                                "event_type": "message",
                                "session_id": session_id,
                                "timestamp": datetime.now(UTC).isoformat(),
                                "role": "user",
                                "content": [{"type": "text", "text": current_prompt}]
                            })
                        except SessionClientError:
                            pass  # Silent failure

            # Extract result from ResultMessage
            if isinstance(message, ResultMessage):
                if executor_session_id is None:
                    executor_session_id = message.session_id

                stream_result = message.result

                # Send assistant message event to API (for conversation history)
                # Skip for structured output agents - they only emit result events
                if message.result and session_id and not skip_assistant_message:
                    try:
                        session_client.add_event(session_id, {
                            "event_type": "message",
                            "session_id": session_id,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "role": "assistant",
                            "content": [{"type": "text", "text": message.result}]
                        })
                    except SessionClientError:
                        pass  # Silent failure

        return stream_result

    # Stream session using ClaudeSDKClient
    try:
        async with ClaudeSDKClient(options=options) as client:
            # Send the initial query and process response
            # For structured output agents, skip assistant message events - only result matters
            skip_messages = output_schema is not None
            await client.query(prompt)
            result = await process_message_stream(client, prompt, skip_assistant_message=skip_messages)

            # Output schema validation (if schema defined)
            if output_schema:
                if not result:
                    raise OutputSchemaValidationError(
                        "No result received but output_schema requires structured output",
                        [{"path": "$", "message": "No result received from agent"}]
                    )

                output_json = extract_json_from_response(result)
                validation = validate_against_schema(output_json, output_schema)

                if not validation.valid:
                    # First attempt failed - retry once
                    retry_prompt = build_validation_error_prompt(validation.errors, output_schema)
                    await client.query(retry_prompt)
                    result = await process_message_stream(client, retry_prompt, skip_assistant_message=True)

                    # Validate retry response
                    if not result:
                        raise OutputSchemaValidationError(
                            "Output validation failed after 1 retry",
                            [{"path": "$", "message": "No result received from retry attempt"}]
                        )

                    output_json = extract_json_from_response(result)
                    validation = validate_against_schema(output_json, output_schema)

                    if not validation.valid:
                        # Retry exhausted - report failure
                        raise OutputSchemaValidationError(
                            "Output validation failed after 1 retry",
                            validation.errors
                        )

                # Validation passed - send result event with structured data
                try:
                    session_client.add_event(session_id, {
                        "event_type": "result",
                        "session_id": session_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "result_text": None,
                        "result_data": output_json,
                    })
                except SessionClientError:
                    pass  # Silent failure

            elif result and session_id:
                # No output schema - send result event with text
                try:
                    session_client.add_event(session_id, {
                        "event_type": "result",
                        "session_id": session_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "result_text": result,
                        "result_data": None,
                    })
                except SessionClientError:
                    pass  # Silent failure

            # NOTE: Session completion is signaled by the agent runner's supervisor
            # via POST /runner/runs/{run_id}/completed when this process exits.

    except OutputSchemaValidationError:
        # Re-raise validation errors directly (don't wrap them)
        raise
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
        output_schema: JSON Schema for output validation. If provided, the agent's
            output will be validated against this schema and retried once on failure.

    Returns:
        Tuple of (executor_session_id, result)

    Raises:
        ValueError: If session_id or result not found in messages
        ImportError: If claude-agent-sdk is not installed
        OutputSchemaValidationError: If output validation fails after retry
        Exception: SDK errors are propagated

    Example:
        >>> project_dir = Path.cwd()
        >>> executor_session_id, result = run_session_sync(
        ...     prompt="What is 2+2?",
        ...     project_dir=project_dir,
        ...     session_id="ses_abc123def456"
        ... )
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
