#!/usr/bin/env python3
"""
Agent Orchestrator MCP Server

This MCP server provides tools to orchestrate specialized Claude Code agents
through the agent-orchestrator Python commands. It enables:
- Listing available agent definitions
- Managing agent sessions (create, resume, list, clean)
- Executing long-running tasks in specialized agent contexts
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from pydantic import ValidationError

from constants import (
    CMD_DELETE_ALL_SESSIONS,
    CMD_GET_RESULT,
    CMD_GET_STATUS,
    CMD_LIST_DEFINITIONS,
    CMD_LIST_SESSIONS,
    CMD_RESUME_SESSION,
    CMD_START_SESSION,
    ENV_COMMAND_PATH,
)
from logger import logger
from schemas import (
    DeleteAllAgentSessionsInput,
    GetAgentSessionResultInput,
    GetAgentSessionStatusInput,
    ListAgentDefinitionsInput,
    ListAgentSessionsInput,
    ResumeAgentSessionInput,
    StartAgentSessionInput,
)
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
        print(f"ERROR: {ENV_COMMAND_PATH} environment variable is required", file=sys.stderr)
        print("Please set it to the absolute path of the commands directory", file=sys.stderr)
        sys.exit(1)

    # Normalize path: remove trailing slash if present
    normalized_path = command_path.rstrip("/")

    return ServerConfig(commandPath=Path(normalized_path).resolve().as_posix())


# Create MCP server instance
server = Server("agent-orchestrator-mcp-server")

# Get server configuration
config = get_server_config()


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="list_agent_definitions",
            description="""List all available agent definitions (blueprints) that can be used to create agent sessions.

This tool discovers agent definitions configured in the agent orchestrator system. Agent definitions are blueprints (not running instances) that provide specialized capabilities (e.g., system architecture, code review, documentation writing).

Args:
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
  - response_format ('markdown' | 'json'): Output format (default: 'markdown')

Returns:
  For JSON format: Structured data with schema:
  {
    "total": number,           // Total number of agents found
    "agents": [
      {
        "name": string,        // Agent name/identifier (e.g., "system-architect")
        "description": string  // Description of agent's capabilities
      }
    ]
  }

  For Markdown format: Human-readable formatted list with agent names and descriptions

Examples:
  - Use when: "What agents are available?" -> Check available agent blueprints
  - Use when: "Show me the agent definitions" -> List all agent definition capabilities
  - Don't use when: You want to see running sessions (use list_agent_sessions instead)

Error Handling:
  - Returns "No agent definitions found" if no agents are configured
  - Returns error message if script execution fails""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Optional project directory path (must be absolute path). Only set when instructed to set a project dir!",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                        "description": "Output format: 'markdown' for human-readable or 'json' for machine-readable",
                    },
                },
            },
        ),
        types.Tool(
            name="list_agent_sessions",
            description="""List all agent session instances (running, completed, or initializing).

This tool shows all agent session instances that have been created, including their names, session IDs, and the project directory used for each session. These are running or completed instances, not blueprints.

Args:
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
  - response_format ('markdown' | 'json'): Output format (default: 'markdown')

Returns:
  For JSON format: Structured data with schema:
  {
    "total": number,              // Total number of sessions
    "sessions": [
      {
        "name": string,           // Session name (e.g., "architect")
        "session_id": string,     // Session ID or status ("initializing", "unknown")
        "project_dir": string     // Project directory path used for this session
      }
    ]
  }

  For Markdown format: Human-readable formatted list with session names, IDs, and project directories

Session ID values:
  - UUID string: Normal session ID (e.g., "3db5dca9-6829-4cb7-a645-c64dbd98244d")
  - "initializing": Session file exists but hasn't started yet
  - "unknown": Session ID couldn't be extracted

Project Directory values:
  - Absolute path: The project directory used when the session was created
  - "unknown": Project directory couldn't be extracted (legacy sessions)

Examples:
  - Use when: "What sessions exist?" -> See all created session instances
  - Use when: "Show me my agent sessions" -> List all session instances with their IDs and project directories
  - Don't use when: You want to see available agent blueprints (use list_agent_definitions instead)

Error Handling:
  - Returns "No sessions found" if no sessions exist
  - Returns error message if script execution fails""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Optional project directory path (must be absolute path). Only set when instructed to set a project dir!",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                        "description": "Output format: 'markdown' for human-readable or 'json' for machine-readable",
                    },
                },
            },
        ),
        types.Tool(
            name="start_agent_session",
            description="""Start a new agent session instance that immediately begins execution.

This tool creates a new agent session instance that runs in a separate Claude Code context. Sessions can be generic (no agent definition) or specialized (with an agent definition blueprint). The agent session will execute the provided prompt and return the result.

IMPORTANT: This operation may take significant time to complete as it runs a full Claude Code session. The agent will process the prompt and may use multiple tool calls to complete the task.

Args:
  - session_name (string): Unique identifier for the agent session instance (alphanumeric, dash, underscore; max 60 chars)
  - agent_definition_name (string, optional): Name of agent definition (blueprint) to use for this session (optional for generic sessions)
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
  - prompt (string): Initial task description or prompt for the agent session
  - async (boolean, optional): Run in background mode (default: false)

Session naming rules:
  - Must be unique (cannot already exist)
  - 1-60 characters
  - Only alphanumeric, dash (-), and underscore (_) allowed
  - Use descriptive names (e.g., "architect", "reviewer", "dev-agent")

Returns:
  The result/output from the completed agent session. This is the agent's final response after processing the prompt and completing all necessary tasks.

Examples:
  - Use when: "Create an architecture design" -> Start session with system-architect agent definition
  - Use when: "Analyze this codebase" -> Start generic session or use code-reviewer agent definition
  - Don't use when: Session already exists (use resume_agent_session instead)
  - Don't use when: You just want to list available agent definitions (use list_agent_definitions instead)

Error Handling:
  - "Session already exists" -> Use resume_agent_session or choose different name
  - "Session name too long" -> Use shorter name (max 60 characters)
  - "Invalid characters" -> Only use alphanumeric, dash, underscore
  - "Agent not found" -> Check available agent definitions with list_agent_definitions
  - "No prompt provided" -> Provide a prompt argument""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Unique identifier for this agent session instance",
                    },
                    "agent_definition_name": {
                        "type": "string",
                        "description": "Name of agent definition (blueprint) to use for this session (optional for generic sessions)",
                    },
                    "project_dir": {
                        "type": "string",
                        "description": "Optional project directory path (must be absolute path). Only set when instructed to set a project dir!",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Initial prompt or task description for the agent session",
                    },
                    "async": {
                        "type": "boolean",
                        "default": False,
                        "description": "Run agent in background (fire-and-forget mode). When true, returns immediately with session info.",
                    },
                },
                "required": ["session_name", "prompt"],
            },
        ),
        types.Tool(
            name="resume_agent_session",
            description="""Resume an existing agent session instance with a new prompt to continue work.

This tool continues an existing agent session instance, allowing you to build upon previous work. The agent session remembers all context from previous interactions. Any agent definition from session creation is automatically maintained.

IMPORTANT: This operation may take significant time to complete as it runs a full Claude Code session. The agent will process the new prompt in the context of all previous interactions.

Args:
  - session_name (string): Name of the existing agent session instance to resume
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
  - prompt (string): Continuation prompt building on previous session context
  - async (boolean, optional): Run in background mode (default: false)

Returns:
  The result/output from the resumed agent session. This is the agent's response after processing the new prompt in context of previous interactions.

Examples:
  - Use when: "Continue the architecture work" -> Resume existing architect session instance
  - Use when: "Add security considerations" -> Resume session to build on previous work
  - Use when: "Review the changes made" -> Resume to get status or make adjustments
  - Don't use when: Session doesn't exist (use start_agent_session to create it)
  - Don't use when: Starting fresh work (use start_agent_session for new sessions)

Error Handling:
  - "Session does not exist" -> Use start_agent_session to create a new session
  - "Session name invalid" -> Check session name format
  - "No prompt provided" -> Provide a prompt argument

Note: The agent definition used during session creation is automatically remembered and applied when resuming.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Name of the existing agent session instance to resume",
                    },
                    "project_dir": {
                        "type": "string",
                        "description": "Optional project directory path (must be absolute path). Only set when instructed to set a project dir!",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Continuation prompt building on previous session context",
                    },
                    "async": {
                        "type": "boolean",
                        "default": False,
                        "description": "Run agent in background (fire-and-forget mode). When true, returns immediately with session info.",
                    },
                },
                "required": ["session_name", "prompt"],
            },
        ),
        types.Tool(
            name="delete_all_agent_sessions",
            description="""Permanently delete all agent session instances and their associated data.

This tool permanently deletes all agent session instances, including their conversation history and metadata. This operation cannot be undone.

WARNING: This is a destructive operation. All session data will be permanently lost.

Args:
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!

Returns:
  Confirmation message indicating sessions were removed or that no sessions existed.

Examples:
  - Use when: "Clear all sessions" -> Remove all session data
  - Use when: "Start fresh" -> Delete all existing sessions
  - Use when: "Clean up old sessions" -> Remove all sessions to free up space
  - Don't use when: You only want to remove specific sessions (currently not supported)
  - Don't use when: You might want to resume sessions later

Error Handling:
  - "No sessions to remove" -> No sessions exist (safe to ignore)
  - Returns error message if script execution fails

Note: This operation is idempotent - running it multiple times has the same effect as running it once.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Optional project directory path (must be absolute path). Only set when instructed to set a project dir!",
                    },
                },
            },
        ),
        types.Tool(
            name="get_agent_session_status",
            description="""Check the current status of an agent session instance (running, finished, or not_existent).

Returns one of three statuses:
- "running": Session instance is currently executing or initializing
- "finished": Session instance completed successfully with a result
- "not_existent": Session instance does not exist

Use this tool to poll for completion when using async mode with start_agent_session or resume_agent_session.

Args:
  - session_name (string): Name of the agent session instance to check
  - project_dir (string, optional): Project directory path
  - wait_seconds (number, optional): Seconds to wait before checking status (default: 0, max: 300)

Returns:
  JSON object with status field: {"status": "running"|"finished"|"not_existent"}

Examples:
  - Poll until finished: Keep calling until status="finished"
  - Poll with interval: Use wait_seconds=10 to wait 10 seconds before checking (reduces token usage)
  - Check before resume: Verify session exists before resuming
  - Monitor background execution: Track progress of async agents

Polling Strategy:
  - Short tasks: Poll every 2-5 seconds (wait_seconds=2-5)
  - Long tasks: Poll every 10-30 seconds (wait_seconds=10-30)
  - Very long tasks: Poll every 60+ seconds (wait_seconds=60+)
  - Using wait_seconds reduces token usage by spacing out status checks""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Name of the agent session instance to check",
                    },
                    "project_dir": {
                        "type": "string",
                        "description": "Optional project directory path (must be absolute path). Only set when instructed to set a project dir!",
                    },
                    "wait_seconds": {
                        "type": "integer",
                        "default": 0,
                        "minimum": 0,
                        "maximum": 300,
                        "description": "Number of seconds to wait before checking status",
                    },
                },
                "required": ["session_name"],
            },
        ),
        types.Tool(
            name="get_agent_session_result",
            description="""Retrieve the final output/result from a completed agent session instance.

This tool extracts the result from a session instance that has finished executing. It will fail with an error if the session is still running or does not exist.

Workflow:
  1. Start agent session with async=true
  2. Poll with get_agent_session_status until status="finished"
  3. Call get_agent_session_result to retrieve the final output

Args:
  - session_name (string): Name of the completed agent session instance
  - project_dir (string, optional): Project directory path

Returns:
  The agent's final response/result as text

Error Handling:
  - "Session still running" -> Poll get_agent_session_status until finished
  - "Session not found" -> Verify session name is correct
  - "No result found" -> Session may have failed, check status""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Name of the completed agent session instance",
                    },
                    "project_dir": {
                        "type": "string",
                        "description": "Optional project directory path (must be absolute path). Only set when instructed to set a project dir!",
                    },
                },
                "required": ["session_name"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls"""

    try:
        if name == "list_agent_definitions":
            return await handle_list_agent_definitions(arguments)
        elif name == "list_agent_sessions":
            return await handle_list_agent_sessions(arguments)
        elif name == "start_agent_session":
            return await handle_start_agent_session(arguments)
        elif name == "resume_agent_session":
            return await handle_resume_agent_session(arguments)
        elif name == "delete_all_agent_sessions":
            return await handle_delete_all_agent_sessions(arguments)
        elif name == "get_agent_session_status":
            return await handle_get_agent_session_status(arguments)
        elif name == "get_agent_session_result":
            return await handle_get_agent_session_result(arguments)
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except ValidationError as e:
        error_msg = f"Validation error: {e}"
        logger.error(f"{name}: validation error", {"error": str(e)})
        return [types.TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(f"{name}: exception", {"error": str(e)})
        return [types.TextContent(type="text", text=error_msg)]


async def handle_list_agent_definitions(arguments: dict) -> list[types.TextContent]:
    """Handle list_agent_definitions tool call"""
    params = ListAgentDefinitionsInput(**arguments)

    logger.info(
        "list_agent_definitions called",
        {
            "project_dir": params.project_dir,
            "response_format": params.response_format,
        },
    )

    try:
        # Build command arguments - command name must be first
        args = [CMD_LIST_DEFINITIONS]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        logger.debug("list_agent_definitions: executing script", {"args": args})

        # Execute list-agents command
        result = await execute_script(config, args)

        if result.exitCode != 0:
            error_msg = handle_script_error(result)
            return [types.TextContent(type="text", text=error_msg)]

        # Parse the agent list
        agents = parse_agent_list(result.stdout)

        # Format based on requested format
        formatted_response = format_tool_response(
            agents,
            params.response_format,
            format_agents_as_markdown,
            format_agents_as_json,
        )

        # Check character limit
        text, truncated = truncate_response(formatted_response)

        return [types.TextContent(type="text", text=text)]

    except Exception as error:
        return [types.TextContent(type="text", text=f"Error: {str(error)}")]


async def handle_list_agent_sessions(arguments: dict) -> list[types.TextContent]:
    """Handle list_agent_sessions tool call"""
    params = ListAgentSessionsInput(**arguments)

    logger.info(
        "list_agent_sessions called",
        {
            "project_dir": params.project_dir,
            "response_format": params.response_format,
        },
    )

    try:
        # Build command arguments - command name must be first
        args = [CMD_LIST_SESSIONS]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        logger.debug("list_agent_sessions: executing script", {"args": args})

        # Execute list command
        result = await execute_script(config, args)

        if result.exitCode != 0:
            error_msg = handle_script_error(result)
            return [types.TextContent(type="text", text=error_msg)]

        # Parse the session list
        sessions = parse_session_list(result.stdout)

        # Format based on requested format
        formatted_response = format_tool_response(
            sessions,
            params.response_format,
            format_sessions_as_markdown,
            format_sessions_as_json,
        )

        # Check character limit
        text, truncated = truncate_response(formatted_response)

        return [types.TextContent(type="text", text=text)]

    except Exception as error:
        return [types.TextContent(type="text", text=f"Error: {str(error)}")]


async def handle_start_agent_session(arguments: dict) -> list[types.TextContent]:
    """Handle start_agent_session tool call"""
    params = StartAgentSessionInput(**arguments)

    logger.info(
        "start_agent_session called",
        {
            "session_name": params.session_name,
            "agent_definition_name": params.agent_definition_name,
            "project_dir": params.project_dir,
            "prompt_length": len(params.prompt),
            "async": params.async_,
        },
    )

    try:
        # Build command arguments
        args = [CMD_START_SESSION, params.session_name]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        # Add agent if specified
        if params.agent_definition_name:
            args.extend(["--agent", params.agent_definition_name])

        # Add prompt
        args.extend(["-p", params.prompt])

        logger.debug("start_agent_session: executing script", {"args": args, "async": params.async_})

        # Check if async mode requested
        if params.async_:
            logger.info("start_agent_session: using async execution (fire-and-forget mode)")

            # Execute in background (detached mode)
            async_result = await execute_script_async(config, args)

            logger.info(
                "start_agent_session: async process spawned",
                {"session_name": async_result.session_name},
            )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "session_name": async_result.session_name,
                            "status": async_result.status,
                            "message": async_result.message,
                        },
                        indent=2,
                    ),
                )
            ]

        # Original blocking behavior (async=false or undefined)
        logger.info("start_agent_session: using synchronous execution (blocking mode)")
        result = await execute_script(config, args)

        if result.exitCode != 0:
            logger.error(
                "start_agent_session: script failed",
                {
                    "exitCode": result.exitCode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

            error_msg = handle_script_error(result)
            return [types.TextContent(type="text", text=error_msg)]

        logger.info(
            "start_agent_session: script succeeded",
            {
                "stdoutLength": len(result.stdout),
                "stderrLength": len(result.stderr),
            },
        )

        # Check character limit
        text, truncated = truncate_response(result.stdout)

        if truncated:
            logger.warn(
                "start_agent_session: response truncated",
                {
                    "originalLength": len(result.stdout),
                    "truncatedLength": len(text),
                },
            )

        return [types.TextContent(type="text", text=text)]

    except Exception as error:
        logger.error(
            "start_agent_session: exception",
            {"error": str(error)},
        )
        return [types.TextContent(type="text", text=f"Error: {str(error)}")]


async def handle_resume_agent_session(arguments: dict) -> list[types.TextContent]:
    """Handle resume_agent_session tool call"""
    params = ResumeAgentSessionInput(**arguments)

    logger.info(
        "resume_agent_session called",
        {
            "session_name": params.session_name,
            "project_dir": params.project_dir,
            "prompt_length": len(params.prompt),
            "async": params.async_,
        },
    )

    try:
        # Build command arguments
        args = [CMD_RESUME_SESSION, params.session_name]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        # Add prompt
        args.extend(["-p", params.prompt])

        logger.debug("resume_agent_session: executing script", {"args": args, "async": params.async_})

        # Check if async mode requested
        if params.async_:
            logger.info("resume_agent_session: using async execution (fire-and-forget mode)")

            # Execute in background (detached mode)
            async_result = await execute_script_async(config, args)

            logger.info(
                "resume_agent_session: async process spawned",
                {"session_name": async_result.session_name},
            )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "session_name": async_result.session_name,
                            "status": async_result.status,
                            "message": async_result.message,
                        },
                        indent=2,
                    ),
                )
            ]

        # Original blocking behavior (async=false or undefined)
        logger.info("resume_agent_session: using synchronous execution (blocking mode)")
        result = await execute_script(config, args)

        if result.exitCode != 0:
            error_msg = handle_script_error(result)
            return [types.TextContent(type="text", text=error_msg)]

        # Check character limit
        text, truncated = truncate_response(result.stdout)

        return [types.TextContent(type="text", text=text)]

    except Exception as error:
        return [types.TextContent(type="text", text=f"Error: {str(error)}")]


async def handle_delete_all_agent_sessions(arguments: dict) -> list[types.TextContent]:
    """Handle delete_all_agent_sessions tool call"""
    params = DeleteAllAgentSessionsInput(**arguments)

    logger.info("delete_all_agent_sessions called", {"project_dir": params.project_dir})

    try:
        # Build command arguments - command name must be first
        args = [CMD_DELETE_ALL_SESSIONS]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        logger.debug("delete_all_agent_sessions: executing script", {"args": args})

        # Execute clean command
        result = await execute_script(config, args)

        if result.exitCode != 0:
            error_msg = handle_script_error(result)
            return [types.TextContent(type="text", text=error_msg)]

        return [types.TextContent(type="text", text=result.stdout)]

    except Exception as error:
        return [types.TextContent(type="text", text=f"Error: {str(error)}")]


async def handle_get_agent_session_status(arguments: dict) -> list[types.TextContent]:
    """Handle get_agent_session_status tool call"""
    params = GetAgentSessionStatusInput(**arguments)

    logger.info(
        "get_agent_session_status called",
        {
            "session_name": params.session_name,
            "wait_seconds": params.wait_seconds,
        },
    )

    try:
        # Wait if wait_seconds is specified and > 0
        if params.wait_seconds and params.wait_seconds > 0:
            logger.debug(
                "get_agent_session_status: waiting before status check",
                {"wait_seconds": params.wait_seconds},
            )
            await asyncio.sleep(params.wait_seconds)
            logger.debug("get_agent_session_status: wait completed, checking status now")

        args = [CMD_GET_STATUS, params.session_name]

        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        result = await execute_script(config, args)

        if result.exitCode != 0:
            # Handle error - likely means session not found or other issue
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"status": "not_existent"}, indent=2),
                )
            ]

        # Parse status from stdout (should be one of: running, finished, not_existent)
        status = result.stdout.strip()

        return [types.TextContent(type="text", text=json.dumps({"status": status}, indent=2))]

    except Exception as error:
        # Handle exceptions
        logger.error("get_agent_session_status: exception", {"error": str(error)})
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"status": "not_existent"}, indent=2),
            )
        ]


async def handle_get_agent_session_result(arguments: dict) -> list[types.TextContent]:
    """Handle get_agent_session_result tool call"""
    params = GetAgentSessionResultInput(**arguments)

    logger.info("get_agent_session_result called", {"session_name": params.session_name})

    try:
        # First check status to provide helpful error messages
        status_args = [CMD_GET_STATUS, params.session_name]
        if params.project_dir:
            status_args.extend(["--project-dir", params.project_dir])

        status_result = await execute_script(config, status_args)
        status = status_result.stdout.strip()

        if status == "not_existent":
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: Session '{params.session_name}' does not exist. Please check the session name.",
                )
            ]

        if status == "running":
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: Session '{params.session_name}' is still running. Use get_agent_session_status to poll until status is 'finished'.",
                )
            ]

        # Session is finished, retrieve result
        args = [CMD_GET_RESULT, params.session_name]
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        result = await execute_script(config, args)

        if result.exitCode != 0:
            logger.error(
                "get_agent_session_result: script failed",
                {
                    "exitCode": result.exitCode,
                    "stderr": result.stderr,
                },
            )

            return [
                types.TextContent(
                    type="text",
                    text=f"Error retrieving result: {result.stderr or 'Unknown error'}",
                )
            ]

        # Check character limit
        text, truncated = truncate_response(result.stdout)

        if truncated:
            logger.warn(
                "get_agent_session_result: response truncated",
                {
                    "originalLength": len(result.stdout),
                    "truncatedLength": len(text),
                },
            )

        return [types.TextContent(type="text", text=text)]

    except Exception as error:
        logger.error("get_agent_session_result: exception", {"error": str(error)})
        return [types.TextContent(type="text", text=f"Error: {str(error)}")]


async def main():
    """Main function to run the MCP server"""
    logger.info(
        "Agent Orchestrator MCP Server starting",
        {
            "commandPath": config.commandPath,
            "cwd": os.getcwd(),
            "pythonVersion": sys.version,
            "env": {
                "AGENT_ORCHESTRATOR_COMMAND_PATH": os.environ.get("AGENT_ORCHESTRATOR_COMMAND_PATH"),
                "AGENT_ORCHESTRATOR_PROJECT_DIR": os.environ.get("AGENT_ORCHESTRATOR_PROJECT_DIR"),
                "PATH": os.environ.get("PATH"),
            },
        },
    )

    print("Agent Orchestrator MCP Server", file=sys.stderr)
    print(f"Commands path: {config.commandPath}", file=sys.stderr)
    print("", file=sys.stderr)

    # Run server with stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Agent Orchestrator MCP server connected and running")
        print("Agent Orchestrator MCP server running via stdio", file=sys.stderr)

        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\nServer stopped", file=sys.stderr)
    except Exception as error:
        logger.error("Server error", {"error": str(error)})
        print(f"Server error: {error}", file=sys.stderr)
        sys.exit(1)
