"""
Core functions for Agent Orchestrator

These functions contain the actual logic for agent orchestration operations.
They are used by both the MCP tools and the REST API.
"""

import asyncio
import json
from typing import Literal, Optional

from constants import (
    CMD_DELETE_ALL_SESSIONS,
    CMD_GET_RESULT,
    CMD_GET_STATUS,
    CMD_LIST_BLUEPRINTS,
    CMD_LIST_SESSIONS,
    CMD_RESUME_SESSION,
    CMD_START_SESSION,
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


async def list_agent_blueprints_impl(
    config: ServerConfig,
    response_format: Literal["markdown", "json"] = "markdown",
) -> str:
    """List all available agent blueprints that can be used to create agent sessions."""
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


async def list_agent_sessions_impl(
    config: ServerConfig,
    response_format: Literal["markdown", "json"] = "markdown",
) -> str:
    """List all agent session instances (running, completed, or initializing)."""
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


async def start_agent_session_impl(
    config: ServerConfig,
    session_name: str,
    prompt: str,
    agent_blueprint_name: Optional[str] = None,
    project_dir: Optional[str] = None,
    async_mode: bool = False,
) -> str:
    """Start a new agent session instance that immediately begins execution."""
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


async def resume_agent_session_impl(
    config: ServerConfig,
    session_name: str,
    prompt: str,
    async_mode: bool = False,
) -> str:
    """Resume an existing agent session instance with a new prompt to continue work."""
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


async def delete_all_agent_sessions_impl(config: ServerConfig) -> str:
    """Permanently delete all agent session instances and their associated data."""
    logger.info("delete_all_agent_sessions called")

    try:
        args = [CMD_DELETE_ALL_SESSIONS]
        result = await execute_script(config, args)

        if result.exitCode != 0:
            return handle_script_error(result)

        return result.stdout

    except Exception as error:
        return f"Error: {str(error)}"


async def get_agent_session_status_impl(
    config: ServerConfig,
    session_name: str,
    wait_seconds: int = 0,
) -> str:
    """Check the current status of an agent session instance."""
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


async def get_agent_session_result_impl(
    config: ServerConfig,
    session_name: str,
) -> str:
    """Retrieve the final output/result from a completed agent session instance."""
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
