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

from .constants import ENV_COMMAND_PATH
from .logger import logger
from .schemas import (
    CleanSessionsInput,
    GetAgentResultInput,
    GetAgentStatusInput,
    ListAgentsInput,
    ListSessionsInput,
    ResumeAgentInput,
    StartAgentInput,
)
from .types import ResponseFormat, ServerConfig
from .utils import (
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


# Register list_agents tool
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="list_agents",
            description="""List all available specialized agent definitions that can be used with start_agent.

This tool discovers agent definitions configured in the agent orchestrator system. Each agent provides specialized capabilities (e.g., system architecture, code review, documentation writing) and can be used when starting new agent sessions.

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
  - Use when: "What agents are available?" -> Check available specialized agents
  - Use when: "Show me the agent definitions" -> List all agent capabilities
  - Don't use when: You want to see running sessions (use list_sessions instead)

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
            name="list_sessions",
            description="""List all existing agent sessions with their session IDs and project directories.

This tool shows all agent sessions that have been created, including their names, session IDs, and the project directory used for each session. Sessions can be in various states (running, completed, or initializing).

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
  - Use when: "What sessions exist?" -> See all created sessions
  - Use when: "Show me my agent sessions" -> List all sessions with their IDs and project directories
  - Don't use when: You want to see available agent types (use list_agents instead)

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
            name="start_agent",
            description="""Start a new orchestrated agent session with an optional specialized agent definition.

This tool creates a new agent session that runs in a separate Claude Code context. Sessions can be generic (no agent) or specialized (with an agent definition). The agent will execute the provided prompt and return the result.

IMPORTANT: This operation may take significant time to complete as it runs a full Claude Code session. The agent will process the prompt and may use multiple tool calls to complete the task.

Args:
  - session_name (string): Unique identifier for the session (alphanumeric, dash, underscore; max 60 chars)
  - agent_name (string, optional): Name of agent definition to use (e.g., "system-architect", "code-reviewer")
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
  - prompt (string): Initial task description or prompt for the agent
  - async (boolean, optional): Run in background mode (default: false)

Session naming rules:
  - Must be unique (cannot already exist)
  - 1-60 characters
  - Only alphanumeric, dash (-), and underscore (_) allowed
  - Use descriptive names (e.g., "architect", "reviewer", "dev-agent")

Returns:
  The result/output from the completed agent session. This is the agent's final response after processing the prompt and completing all necessary tasks.

Examples:
  - Use when: "Create an architecture design" -> Start session with system-architect agent
  - Use when: "Analyze this codebase" -> Start generic session or use code-reviewer agent
  - Don't use when: Session already exists (use resume_agent instead)
  - Don't use when: You just want to list available agents (use list_agents instead)

Error Handling:
  - "Session already exists" -> Use resume_agent or choose different name
  - "Session name too long" -> Use shorter name (max 60 characters)
  - "Invalid characters" -> Only use alphanumeric, dash, underscore
  - "Agent not found" -> Check available agents with list_agents
  - "No prompt provided" -> Provide a prompt argument""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Unique name for the agent session (alphanumeric, dash, underscore only)",
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Optional agent definition to use (e.g., 'system-architect', 'code-reviewer')",
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
            name="resume_agent",
            description="""Resume an existing agent session with a new prompt to continue the work.

This tool continues an existing agent session, allowing you to build upon previous work. The agent remembers all context from previous interactions in this session. Any agent association from session creation is automatically maintained.

IMPORTANT: This operation may take significant time to complete as it runs a full Claude Code session. The agent will process the new prompt in the context of all previous interactions.

Args:
  - session_name (string): Name of the existing session to resume
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
  - prompt (string): Continuation prompt or new task description
  - async (boolean, optional): Run in background mode (default: false)

Returns:
  The result/output from the resumed agent session. This is the agent's response after processing the new prompt in context of previous interactions.

Examples:
  - Use when: "Continue the architecture work" -> Resume existing architect session
  - Use when: "Add security considerations" -> Resume session to build on previous work
  - Use when: "Review the changes made" -> Resume to get status or make adjustments
  - Don't use when: Session doesn't exist (use start_agent to create it)
  - Don't use when: Starting fresh work (use start_agent for new sessions)

Error Handling:
  - "Session does not exist" -> Use start_agent to create a new session
  - "Session name invalid" -> Check session name format
  - "No prompt provided" -> Provide a prompt argument

Note: The agent definition used during session creation is automatically remembered and applied when resuming.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Name of the existing session to resume",
                    },
                    "project_dir": {
                        "type": "string",
                        "description": "Optional project directory path (must be absolute path). Only set when instructed to set a project dir!",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Continuation prompt or task description for the resumed session",
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
            name="clean_sessions",
            description="""Remove all agent sessions and their associated data.

This tool permanently deletes all agent sessions, including their conversation history and metadata. This operation cannot be undone.

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
            name="get_agent_status",
            description="""Check the current status of an agent session.

Returns one of three statuses:
- "running": Session is currently executing or initializing
- "finished": Session completed successfully with a result
- "not_existent": Session does not exist

Use this tool to poll for completion when using async mode with start_agent or resume_agent.

Args:
  - session_name (string): Name of the session to check
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
                        "description": "Name of the session to check status for",
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
            name="get_agent_result",
            description="""Retrieve the final result from a completed agent session.

This tool extracts the result from a session that has finished executing. It will fail with an error if the session is still running or does not exist.

Workflow:
  1. Start agent with async=true
  2. Poll with get_agent_status until status="finished"
  3. Call get_agent_result to retrieve the final output

Args:
  - session_name (string): Name of the completed session
  - project_dir (string, optional): Project directory path

Returns:
  The agent's final response/result as text

Error Handling:
  - "Session still running" -> Poll get_agent_status until finished
  - "Session not found" -> Verify session name is correct
  - "No result found" -> Session may have failed, check status""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Name of the session to retrieve result from",
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
        if name == "list_agents":
            return await handle_list_agents(arguments)
        elif name == "list_sessions":
            return await handle_list_sessions(arguments)
        elif name == "start_agent":
            return await handle_start_agent(arguments)
        elif name == "resume_agent":
            return await handle_resume_agent(arguments)
        elif name == "clean_sessions":
            return await handle_clean_sessions(arguments)
        elif name == "get_agent_status":
            return await handle_get_agent_status(arguments)
        elif name == "get_agent_result":
            return await handle_get_agent_result(arguments)
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


async def handle_list_agents(arguments: dict) -> list[types.TextContent]:
    """Handle list_agents tool call"""
    params = ListAgentsInput(**arguments)

    logger.info(
        "list_agents called",
        {
            "project_dir": params.project_dir,
            "response_format": params.response_format,
        },
    )

    try:
        # Build command arguments - command name must be first
        args = ["list-agents"]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        logger.debug("list_agents: executing script", {"args": args})

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


async def handle_list_sessions(arguments: dict) -> list[types.TextContent]:
    """Handle list_sessions tool call"""
    params = ListSessionsInput(**arguments)

    logger.info(
        "list_sessions called",
        {
            "project_dir": params.project_dir,
            "response_format": params.response_format,
        },
    )

    try:
        # Build command arguments - command name must be first
        args = ["list"]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        logger.debug("list_sessions: executing script", {"args": args})

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


async def handle_start_agent(arguments: dict) -> list[types.TextContent]:
    """Handle start_agent tool call"""
    params = StartAgentInput(**arguments)

    logger.info(
        "start_agent called",
        {
            "session_name": params.session_name,
            "agent_name": params.agent_name,
            "project_dir": params.project_dir,
            "prompt_length": len(params.prompt),
            "async": params.async_,
        },
    )

    try:
        # Build command arguments
        args = ["new", params.session_name]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        # Add agent if specified
        if params.agent_name:
            args.extend(["--agent", params.agent_name])

        # Add prompt
        args.extend(["-p", params.prompt])

        logger.debug("start_agent: executing script", {"args": args, "async": params.async_})

        # Check if async mode requested
        if params.async_:
            logger.info("start_agent: using async execution (fire-and-forget mode)")

            # Execute in background (detached mode)
            async_result = await execute_script_async(config, args)

            logger.info(
                "start_agent: async process spawned",
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
        logger.info("start_agent: using synchronous execution (blocking mode)")
        result = await execute_script(config, args)

        if result.exitCode != 0:
            logger.error(
                "start_agent: script failed",
                {
                    "exitCode": result.exitCode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

            error_msg = handle_script_error(result)
            return [types.TextContent(type="text", text=error_msg)]

        logger.info(
            "start_agent: script succeeded",
            {
                "stdoutLength": len(result.stdout),
                "stderrLength": len(result.stderr),
            },
        )

        # Check character limit
        text, truncated = truncate_response(result.stdout)

        if truncated:
            logger.warn(
                "start_agent: response truncated",
                {
                    "originalLength": len(result.stdout),
                    "truncatedLength": len(text),
                },
            )

        return [types.TextContent(type="text", text=text)]

    except Exception as error:
        logger.error(
            "start_agent: exception",
            {"error": str(error)},
        )
        return [types.TextContent(type="text", text=f"Error: {str(error)}")]


async def handle_resume_agent(arguments: dict) -> list[types.TextContent]:
    """Handle resume_agent tool call"""
    params = ResumeAgentInput(**arguments)

    logger.info(
        "resume_agent called",
        {
            "session_name": params.session_name,
            "project_dir": params.project_dir,
            "prompt_length": len(params.prompt),
            "async": params.async_,
        },
    )

    try:
        # Build command arguments
        args = ["resume", params.session_name]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        # Add prompt
        args.extend(["-p", params.prompt])

        logger.debug("resume_agent: executing script", {"args": args, "async": params.async_})

        # Check if async mode requested
        if params.async_:
            logger.info("resume_agent: using async execution (fire-and-forget mode)")

            # Execute in background (detached mode)
            async_result = await execute_script_async(config, args)

            logger.info(
                "resume_agent: async process spawned",
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
        logger.info("resume_agent: using synchronous execution (blocking mode)")
        result = await execute_script(config, args)

        if result.exitCode != 0:
            error_msg = handle_script_error(result)
            return [types.TextContent(type="text", text=error_msg)]

        # Check character limit
        text, truncated = truncate_response(result.stdout)

        return [types.TextContent(type="text", text=text)]

    except Exception as error:
        return [types.TextContent(type="text", text=f"Error: {str(error)}")]


async def handle_clean_sessions(arguments: dict) -> list[types.TextContent]:
    """Handle clean_sessions tool call"""
    params = CleanSessionsInput(**arguments)

    logger.info("clean_sessions called", {"project_dir": params.project_dir})

    try:
        # Build command arguments - command name must be first
        args = ["clean"]

        # Add project_dir if specified (supersedes environment variable)
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        logger.debug("clean_sessions: executing script", {"args": args})

        # Execute clean command
        result = await execute_script(config, args)

        if result.exitCode != 0:
            error_msg = handle_script_error(result)
            return [types.TextContent(type="text", text=error_msg)]

        return [types.TextContent(type="text", text=result.stdout)]

    except Exception as error:
        return [types.TextContent(type="text", text=f"Error: {str(error)}")]


async def handle_get_agent_status(arguments: dict) -> list[types.TextContent]:
    """Handle get_agent_status tool call"""
    params = GetAgentStatusInput(**arguments)

    logger.info(
        "get_agent_status called",
        {
            "session_name": params.session_name,
            "wait_seconds": params.wait_seconds,
        },
    )

    try:
        # Wait if wait_seconds is specified and > 0
        if params.wait_seconds and params.wait_seconds > 0:
            logger.debug(
                "get_agent_status: waiting before status check",
                {"wait_seconds": params.wait_seconds},
            )
            await asyncio.sleep(params.wait_seconds)
            logger.debug("get_agent_status: wait completed, checking status now")

        args = ["status", params.session_name]

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
        logger.error("get_agent_status: exception", {"error": str(error)})
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"status": "not_existent"}, indent=2),
            )
        ]


async def handle_get_agent_result(arguments: dict) -> list[types.TextContent]:
    """Handle get_agent_result tool call"""
    params = GetAgentResultInput(**arguments)

    logger.info("get_agent_result called", {"session_name": params.session_name})

    try:
        # First check status to provide helpful error messages
        status_args = ["status", params.session_name]
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
                    text=f"Error: Session '{params.session_name}' is still running. Use get_agent_status to poll until status is 'finished'.",
                )
            ]

        # Session is finished, retrieve result
        args = ["get-result", params.session_name]
        if params.project_dir:
            args.extend(["--project-dir", params.project_dir])

        result = await execute_script(config, args)

        if result.exitCode != 0:
            logger.error(
                "get_agent_result: script failed",
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
                "get_agent_result: response truncated",
                {
                    "originalLength": len(result.stdout),
                    "truncatedLength": len(text),
                },
            )

        return [types.TextContent(type="text", text=text)]

    except Exception as error:
        logger.error("get_agent_result: exception", {"error": str(error)})
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
