#!/usr/bin/env python3
"""
Agent Orchestrator MCP Server

This MCP server provides tools to orchestrate specialized Claude Code agents
through the agent-orchestrator Python commands. It enables:
- Listing available agent blueprints
- Managing agent sessions (create, resume, list, clean)
- Executing long-running tasks in specialized agent contexts

Supports both stdio and HTTP transports via FastMCP.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Literal, Optional

from fastmcp import FastMCP
from pydantic import Field

from constants import (
    CMD_DELETE_ALL_SESSIONS,
    CMD_GET_RESULT,
    CMD_GET_STATUS,
    CMD_LIST_BLUEPRINTS,
    CMD_LIST_SESSIONS,
    CMD_RESUME_SESSION,
    CMD_START_SESSION,
    ENV_COMMAND_PATH,
    MAX_SESSION_NAME_LENGTH,
)
from logger import logger
from types_models import ResponseFormat, ServerConfig
from utils import (
    execute_script,
    execute_script_async,
    format_agents_as_json,
    format_agents_as_markdown,
    format_sessions_as_json,
    format_sessions_as_markdown,
    format_tool_response,
    handle_script_error,
    parse_agent_list,
    parse_session_list,
    truncate_response,
)


def get_server_config() -> ServerConfig:
    """Get configuration from environment variables"""
    command_path = os.environ.get(ENV_COMMAND_PATH)
    if not command_path:
        print(f"ERROR: {ENV_COMMAND_PATH} environment variable not set and auto-discovery failed", file=sys.stderr)
        print("This should not happen - please check the MCP server installation", file=sys.stderr)
        sys.exit(1)

    # Normalize path: remove trailing slash if present
    normalized_path = command_path.rstrip("/")

    return ServerConfig(commandPath=Path(normalized_path).resolve().as_posix())


# Get server configuration
config = get_server_config()

# Create FastMCP server instance
mcp = FastMCP(
    "agent-orchestrator-mcp-server",
    instructions="""Agent Orchestrator MCP Server - Orchestrate specialized Claude Code agents.

Use this server to:
- List available agent blueprints (reusable configurations)
- Start new agent sessions with specific tasks
- Resume existing sessions to continue work
- Monitor session status and retrieve results
- Clean up sessions when done
""",
)


@mcp.tool()
async def list_agent_blueprints(
    response_format: Literal["markdown", "json"] = Field(
        default="markdown",
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    ),
) -> str:
    """List all available agent blueprints that can be used to create agent sessions.

    This tool discovers agent blueprints configured in the agent orchestrator system.
    Agent blueprints are reusable configurations (not running instances) that provide
    specialized capabilities (e.g., system architecture, code review, documentation writing).

    Returns:
      For JSON format: Structured data with total count and agent details
      For Markdown format: Human-readable formatted list with agent names and descriptions

    Examples:
      - Use when: "What agents are available?" -> Check available agent blueprints
      - Use when: "Show me the agent blueprints" -> List all agent blueprint capabilities
      - Don't use when: You want to see running sessions (use list_agent_sessions instead)
    """
    logger.info("list_agent_blueprints called", {"response_format": response_format})

    try:
        args = [CMD_LIST_BLUEPRINTS]
        result = await execute_script(config, args)

        if result.exitCode != 0:
            return handle_script_error(result)

        agents = parse_agent_list(result.stdout)
        fmt = ResponseFormat.JSON if response_format == "json" else ResponseFormat.MARKDOWN
        formatted_response = format_tool_response(
            agents, fmt, format_agents_as_markdown, format_agents_as_json
        )
        text, _ = truncate_response(formatted_response)
        return text

    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
async def list_agent_sessions(
    response_format: Literal["markdown", "json"] = Field(
        default="markdown",
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    ),
) -> str:
    """List all agent session instances (running, completed, or initializing).

    This tool shows all agent session instances that have been created, including
    their names, session IDs, and the project directory used for each session.
    These are running or completed instances, not blueprints.

    Returns:
      For JSON format: Structured data with session details
      For Markdown format: Human-readable formatted list

    Session ID values:
      - UUID string: Normal session ID
      - "initializing": Session file exists but hasn't started yet
      - "unknown": Session ID couldn't be extracted

    Examples:
      - Use when: "What sessions exist?" -> See all created session instances
      - Don't use when: You want to see available blueprints (use list_agent_blueprints)
    """
    logger.info("list_agent_sessions called", {"response_format": response_format})

    try:
        args = [CMD_LIST_SESSIONS]
        result = await execute_script(config, args)

        if result.exitCode != 0:
            return handle_script_error(result)

        sessions = parse_session_list(result.stdout)
        fmt = ResponseFormat.JSON if response_format == "json" else ResponseFormat.MARKDOWN
        formatted_response = format_tool_response(
            sessions, fmt, format_sessions_as_markdown, format_sessions_as_json
        )
        text, _ = truncate_response(formatted_response)
        return text

    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
async def start_agent_session(
    session_name: str = Field(
        description="Unique identifier for this agent session instance (alphanumeric, dash, underscore; max 60 chars)",
        min_length=1,
        max_length=MAX_SESSION_NAME_LENGTH,
    ),
    prompt: str = Field(
        description="Initial prompt or task description for the agent session",
        min_length=1,
    ),
    agent_blueprint_name: Optional[str] = Field(
        default=None,
        description="Name of agent blueprint to use for this session (optional for generic sessions)",
    ),
    project_dir: Optional[str] = Field(
        default=None,
        description="Optional project directory path (must be absolute path). Only set when instructed!",
    ),
    async_mode: bool = Field(
        default=False,
        description="Run agent in background (fire-and-forget mode). When true, returns immediately with session info.",
    ),
) -> str:
    """Start a new agent session instance that immediately begins execution.

    This tool creates a new agent session instance that runs in a separate Claude Code context.
    Sessions can be generic (no agent blueprint) or specialized (using an agent blueprint).
    The agent session will execute the provided prompt and return the result.

    IMPORTANT: This operation may take significant time to complete as it runs a full
    Claude Code session. The agent will process the prompt and may use multiple tool
    calls to complete the task.

    Session naming rules:
      - Must be unique (cannot already exist)
      - 1-60 characters
      - Only alphanumeric, dash (-), and underscore (_) allowed

    Returns:
      The result/output from the completed agent session, or session info if async_mode=True.

    Examples:
      - Use when: "Create an architecture design" -> Start session with system-architect blueprint
      - Don't use when: Session already exists (use resume_agent_session instead)
    """
    logger.info(
        "start_agent_session called",
        {
            "session_name": session_name,
            "agent_blueprint_name": agent_blueprint_name,
            "project_dir": project_dir,
            "prompt_length": len(prompt),
            "async_mode": async_mode,
        },
    )

    try:
        args = [CMD_START_SESSION, session_name]

        if project_dir:
            args.extend(["--project-dir", project_dir])

        if agent_blueprint_name:
            args.extend(["--agent", agent_blueprint_name])

        args.extend(["-p", prompt])

        if async_mode:
            logger.info("start_agent_session: using async execution")
            async_result = await execute_script_async(config, args)
            return json.dumps(
                {
                    "session_name": async_result.session_name,
                    "status": async_result.status,
                    "message": async_result.message,
                },
                indent=2,
            )

        logger.info("start_agent_session: using synchronous execution")
        result = await execute_script(config, args)

        if result.exitCode != 0:
            return handle_script_error(result)

        text, truncated = truncate_response(result.stdout)
        if truncated:
            logger.warn("start_agent_session: response truncated")
        return text

    except Exception as error:
        logger.error("start_agent_session: exception", {"error": str(error)})
        return f"Error: {str(error)}"


@mcp.tool()
async def resume_agent_session(
    session_name: str = Field(
        description="Name of the existing agent session instance to resume",
        min_length=1,
        max_length=MAX_SESSION_NAME_LENGTH,
    ),
    prompt: str = Field(
        description="Continuation prompt building on previous session context",
        min_length=1,
    ),
    async_mode: bool = Field(
        default=False,
        description="Run agent in background (fire-and-forget mode). When true, returns immediately.",
    ),
) -> str:
    """Resume an existing agent session instance with a new prompt to continue work.

    This tool continues an existing agent session instance, allowing you to build upon
    previous work. The agent session remembers all context from previous interactions.
    Any agent blueprint from session creation is automatically maintained.

    IMPORTANT: This operation may take significant time to complete as it runs a full
    Claude Code session.

    Returns:
      The result/output from the resumed agent session.

    Examples:
      - Use when: "Continue the architecture work" -> Resume existing architect session
      - Don't use when: Session doesn't exist (use start_agent_session to create it)
    """
    logger.info(
        "resume_agent_session called",
        {
            "session_name": session_name,
            "prompt_length": len(prompt),
            "async_mode": async_mode,
        },
    )

    try:
        args = [CMD_RESUME_SESSION, session_name]
        args.extend(["-p", prompt])

        if async_mode:
            logger.info("resume_agent_session: using async execution")
            async_result = await execute_script_async(config, args)
            return json.dumps(
                {
                    "session_name": async_result.session_name,
                    "status": async_result.status,
                    "message": async_result.message,
                },
                indent=2,
            )

        logger.info("resume_agent_session: using synchronous execution")
        result = await execute_script(config, args)

        if result.exitCode != 0:
            return handle_script_error(result)

        text, _ = truncate_response(result.stdout)
        return text

    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
async def delete_all_agent_sessions() -> str:
    """Permanently delete all agent session instances and their associated data.

    WARNING: This is a destructive operation. All session data will be permanently lost.
    This operation cannot be undone.

    Returns:
      Confirmation message indicating sessions were removed or that no sessions existed.

    Examples:
      - Use when: "Clear all sessions" -> Remove all session data
      - Use when: "Start fresh" -> Delete all existing sessions
      - Don't use when: You might want to resume sessions later
    """
    logger.info("delete_all_agent_sessions called")

    try:
        args = [CMD_DELETE_ALL_SESSIONS]
        result = await execute_script(config, args)

        if result.exitCode != 0:
            return handle_script_error(result)

        return result.stdout

    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
async def get_agent_session_status(
    session_name: str = Field(
        description="Name of the agent session instance to check",
        min_length=1,
        max_length=MAX_SESSION_NAME_LENGTH,
    ),
    wait_seconds: int = Field(
        default=0,
        ge=0,
        le=300,
        description="Seconds to wait before checking status (default: 0, max: 300). Reduces token usage for polling.",
    ),
) -> str:
    """Check the current status of an agent session instance.

    Returns one of three statuses:
    - "running": Session instance is currently executing or initializing
    - "finished": Session instance completed successfully with a result
    - "not_existent": Session instance does not exist

    Use this tool to poll for completion when using async_mode with start_agent_session
    or resume_agent_session.

    Polling Strategy:
      - Short tasks: Poll every 2-5 seconds (wait_seconds=2-5)
      - Long tasks: Poll every 10-30 seconds (wait_seconds=10-30)
      - Very long tasks: Poll every 60+ seconds (wait_seconds=60+)

    Returns:
      JSON object with status field: {"status": "running"|"finished"|"not_existent"}
    """
    logger.info(
        "get_agent_session_status called",
        {"session_name": session_name, "wait_seconds": wait_seconds},
    )

    try:
        if wait_seconds > 0:
            logger.debug(f"Waiting {wait_seconds} seconds before status check")
            await asyncio.sleep(wait_seconds)

        args = [CMD_GET_STATUS, session_name]
        result = await execute_script(config, args)

        if result.exitCode != 0:
            return json.dumps({"status": "not_existent"}, indent=2)

        status = result.stdout.strip()
        return json.dumps({"status": status}, indent=2)

    except Exception as error:
        logger.error("get_agent_session_status: exception", {"error": str(error)})
        return json.dumps({"status": "not_existent"}, indent=2)


@mcp.tool()
async def get_agent_session_result(
    session_name: str = Field(
        description="Name of the completed agent session instance",
        min_length=1,
        max_length=MAX_SESSION_NAME_LENGTH,
    ),
) -> str:
    """Retrieve the final output/result from a completed agent session instance.

    This tool extracts the result from a session instance that has finished executing.
    It will fail with an error if the session is still running or does not exist.

    Workflow:
      1. Start agent session with async_mode=True
      2. Poll with get_agent_session_status until status="finished"
      3. Call get_agent_session_result to retrieve the final output

    Returns:
      The agent's final response/result as text.

    Error Handling:
      - "Session still running" -> Poll get_agent_session_status until finished
      - "Session not found" -> Verify session name is correct
    """
    logger.info("get_agent_session_result called", {"session_name": session_name})

    try:
        # First check status
        status_args = [CMD_GET_STATUS, session_name]
        status_result = await execute_script(config, status_args)
        status = status_result.stdout.strip()

        if status == "not_existent":
            return f"Error: Session '{session_name}' does not exist. Please check the session name."

        if status == "running":
            return f"Error: Session '{session_name}' is still running. Use get_agent_session_status to poll until status is 'finished'."

        # Session is finished, retrieve result
        args = [CMD_GET_RESULT, session_name]
        result = await execute_script(config, args)

        if result.exitCode != 0:
            return f"Error retrieving result: {result.stderr or 'Unknown error'}"

        text, truncated = truncate_response(result.stdout)
        if truncated:
            logger.warn("get_agent_session_result: response truncated")
        return text

    except Exception as error:
        logger.error("get_agent_session_result: exception", {"error": str(error)})
        return f"Error: {str(error)}"


def run_server(
    transport: Literal["stdio", "streamable-http", "sse"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8080,
):
    """Run the MCP server with the specified transport.

    Args:
        transport: Transport type - "stdio", "streamable-http", or "sse"
        host: Host to bind to (for HTTP transports)
        port: Port to bind to (for HTTP transports)
    """
    logger.info(
        "Agent Orchestrator MCP Server starting",
        {
            "transport": transport,
            "host": host if transport != "stdio" else None,
            "port": port if transport != "stdio" else None,
            "commandPath": config.commandPath,
        },
    )

    print("Agent Orchestrator MCP Server", file=sys.stderr)
    print(f"Commands path: {config.commandPath}", file=sys.stderr)
    print(f"Transport: {transport}", file=sys.stderr)

    if transport == "stdio":
        print("Running via stdio", file=sys.stderr)
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        print(f"Running via HTTP at http://{host}:{port}/mcp", file=sys.stderr)
        mcp.run(transport="streamable-http", host=host, port=port)
    elif transport == "sse":
        print(f"Running via SSE at http://{host}:{port}/sse", file=sys.stderr)
        mcp.run(transport="sse", host=host, port=port)
    else:
        raise ValueError(f"Unknown transport: {transport}")


async def main():
    """Main function for stdio transport (backward compatibility)"""
    run_server(transport="stdio")


if __name__ == "__main__":
    run_server()
