"""
Core functions for Agent Orchestrator MCP Server.

These functions implement the actual logic by calling the Agent Coordinator API.
They are used by both the MCP tools and the REST API.

Note: Uses session_id (coordinator-generated) per ADR-010.
"""

import asyncio
import json
import os
from typing import Literal, Optional

from api_client import APIClient, APIError
from constants import (
    CHARACTER_LIMIT,
    ENV_AGENT_SESSION_ID,
    HEADER_AGENT_SESSION_ID,
    ENV_AGENT_TAGS,
    HEADER_AGENT_TAGS,
    ENV_ADDITIONAL_DEMANDS,
    HEADER_ADDITIONAL_DEMANDS,
)
from logger import logger
from types_models import ServerConfig


def get_api_client(config: ServerConfig) -> APIClient:
    """Get API client instance."""
    return APIClient(config.api_url)


def get_parent_session_id(http_headers: Optional[dict] = None) -> Optional[str]:
    """
    Get parent session ID from environment or HTTP headers.

    - stdio mode: reads from AGENT_SESSION_ID env var
    - HTTP mode: reads from X-Agent-Session-Id header
    """
    # Try HTTP header first (if provided)
    if http_headers:
        # HTTP headers are case-insensitive; get_http_headers() returns lowercase keys
        header_key_lower = HEADER_AGENT_SESSION_ID.lower()
        parent = http_headers.get(header_key_lower)
        if parent:
            return parent

    # Fall back to environment variable
    return os.environ.get(ENV_AGENT_SESSION_ID)


def get_filter_tags(http_headers: Optional[dict] = None) -> Optional[str]:
    """
    Get filter tags from environment or HTTP headers.

    - stdio mode: reads from AGENT_TAGS env var
    - HTTP mode: reads from X-Agent-Tags header

    Returns: Comma-separated tag string or None if not set.
    """
    # Try HTTP header first (if provided)
    if http_headers:
        header_key_lower = HEADER_AGENT_TAGS.lower()
        tags = http_headers.get(header_key_lower)
        if tags:
            return tags

    # Fall back to environment variable
    return os.environ.get(ENV_AGENT_TAGS)


def get_additional_demands(http_headers: Optional[dict] = None) -> Optional[dict]:
    """
    Get additional demands from environment or HTTP headers.

    - stdio mode: reads from ADDITIONAL_DEMANDS env var
    - HTTP mode: reads from X-Additional-Demands header

    Value should be JSON: {"hostname": "...", "project_dir": "...", "executor_type": "...", "tags": [...]}

    Returns: Parsed demands dict or None if not set/invalid.
    """
    demands_str = None

    # Try HTTP header first (if provided)
    if http_headers:
        header_key_lower = HEADER_ADDITIONAL_DEMANDS.lower()
        demands_str = http_headers.get(header_key_lower)

    # Fall back to environment variable
    if not demands_str:
        demands_str = os.environ.get(ENV_ADDITIONAL_DEMANDS)

    if not demands_str:
        return None

    # Parse JSON
    try:
        demands = json.loads(demands_str)
        if isinstance(demands, dict):
            return demands
        logger.warning(f"Additional demands must be a JSON object, got: {type(demands)}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse additional demands JSON: {e}")
        return None


def truncate_response(text: str) -> tuple[str, bool]:
    """Truncate response if it exceeds character limit."""
    if len(text) <= CHARACTER_LIMIT:
        return text, False

    truncated = text[:CHARACTER_LIMIT] + "\n\n[Response truncated due to length]"
    return truncated, True


async def list_agent_blueprints_impl(
    config: ServerConfig,
    response_format: Literal["markdown", "json"] = "markdown",
    http_headers: Optional[dict] = None,
) -> str:
    """List all available agent blueprints filtered by tags."""
    logger.info("list_agent_blueprints called", {"response_format": response_format})

    try:
        # Get filter tags from headers/env
        tags = get_filter_tags(http_headers)

        client = get_api_client(config)
        agents = await client.list_agents(tags=tags)

        # Filter to active agents only
        active_agents = [a for a in agents if a.get("status") == "active"]

        if response_format == "json":
            return json.dumps(
                {
                    "total": len(active_agents),
                    "agents": [
                        {"name": a["name"], "description": a.get("description", "")}
                        for a in active_agents
                    ],
                },
                indent=2,
            )
        else:
            if not active_agents:
                return "No agent blueprints found"

            lines = ["# Available Agent Blueprints", ""]
            for agent in active_agents:
                lines.append(f"## {agent['name']}")
                lines.append(agent.get("description", "No description"))
                lines.append("")
            return "\n".join(lines)

    except APIError as e:
        logger.error("list_agent_blueprints error", {"error": str(e)})
        return f"Error: {str(e)}"


async def list_agent_sessions_impl(
    config: ServerConfig,
    response_format: Literal["markdown", "json"] = "markdown",
) -> str:
    """List all agent sessions."""
    logger.info("list_agent_sessions called", {"response_format": response_format})

    try:
        client = get_api_client(config)
        sessions = await client.list_sessions()

        if response_format == "json":
            return json.dumps(
                {"total": len(sessions), "sessions": sessions},
                indent=2,
            )
        else:
            if not sessions:
                return "No sessions found"

            lines = ["# Agent Sessions", "", f"Found {len(sessions)} session(s)", ""]
            for s in sessions:
                lines.append(f"## {s.get('session_id', 'unknown')}")
                lines.append(f"- **Status**: {s.get('status', 'unknown')}")
                lines.append(f"- **Project Directory**: {s.get('project_dir', 'N/A')}")
                if s.get('agent_name'):
                    lines.append(f"- **Agent**: {s.get('agent_name')}")
                lines.append("")
            return "\n".join(lines)

    except APIError as e:
        logger.error("list_agent_sessions error", {"error": str(e)})
        return f"Error: {str(e)}"


async def start_agent_session_impl(
    config: ServerConfig,
    prompt: str,
    agent_blueprint_name: Optional[str] = None,
    project_dir: Optional[str] = None,
    async_mode: bool = False,
    callback: bool = False,
    http_headers: Optional[dict] = None,
) -> str:
    """Start a new agent session.

    Session ID is generated by coordinator (ADR-010).
    """
    logger.info(
        "start_agent_session called",
        {
            "agent_blueprint_name": agent_blueprint_name,
            "async_mode": async_mode,
            "callback": callback,
        },
    )

    try:
        client = get_api_client(config)

        # Get parent session ID for callback support (ADR-010)
        parent_session_id = None
        if callback:
            parent_session_id = get_parent_session_id(http_headers)
            if not parent_session_id:
                logger.warn("callback=true but no parent session ID available")

        # Get additional demands from headers/env (ADR-011)
        additional_demands = get_additional_demands(http_headers)
        if additional_demands:
            logger.info(f"Additional demands: {additional_demands}")

        # Create agent run - coordinator generates session_id
        # Note: If project_dir is None, the Agent Coordinator/Runner decides the default
        result = await client.create_run(
            run_type="start_session",
            prompt=prompt,
            agent_name=agent_blueprint_name,
            project_dir=project_dir,
            parent_session_id=parent_session_id,
            additional_demands=additional_demands,
        )

        run_id = result["run_id"]
        session_id = result["session_id"]

        logger.info(f"Created run {run_id} for session {session_id}")

        if async_mode:
            # Return immediately
            response = {
                "session_id": session_id,
                "run_id": run_id,
                "status": "running",
                "message": "Agent started in background. Use get_agent_session_status to poll for completion.",
            }
            if callback and parent_session_id:
                response["callback_to"] = parent_session_id
            return json.dumps(response, indent=2)

        # Synchronous: wait for completion
        logger.info(f"Waiting for run {run_id} to complete...")
        await client.wait_for_run(run_id)

        # Get result from session
        session = await client.get_session(session_id)
        if not session:
            return f"Error: Session '{session_id}' not found after run completed"

        result_text = await client.get_session_result(session_id)
        text, truncated = truncate_response(result_text)
        if truncated:
            logger.warn("start_agent_session: response truncated")
        return text

    except APIError as e:
        logger.error("start_agent_session error", {"error": str(e)})
        return f"Error: {str(e)}"


async def resume_agent_session_impl(
    config: ServerConfig,
    session_id: str,
    prompt: str,
    async_mode: bool = False,
    callback: bool = False,
    http_headers: Optional[dict] = None,
) -> str:
    """Resume an existing agent session."""
    logger.info(
        "resume_agent_session called",
        {
            "session_id": session_id,
            "async_mode": async_mode,
            "callback": callback,
        },
    )

    try:
        client = get_api_client(config)

        # Get parent session ID for callback support (ADR-010)
        parent_session_id = None
        if callback:
            parent_session_id = get_parent_session_id(http_headers)
            if not parent_session_id:
                logger.warn("callback=true but no parent session ID available")

        # Get additional demands from headers/env (ADR-011)
        additional_demands = get_additional_demands(http_headers)
        if additional_demands:
            logger.info(f"Additional demands for resume: {additional_demands}")

        # Create resume run
        result = await client.create_run(
            run_type="resume_session",
            session_id=session_id,
            prompt=prompt,
            parent_session_id=parent_session_id,
            additional_demands=additional_demands,
        )

        run_id = result["run_id"]

        logger.info(f"Created resume run {run_id} for session {session_id}")

        if async_mode:
            response = {
                "session_id": session_id,
                "run_id": run_id,
                "status": "running",
                "message": "Agent resumed in background. Use get_agent_session_status to poll for completion.",
            }
            if callback and parent_session_id:
                response["callback_to"] = parent_session_id
            return json.dumps(response, indent=2)

        # Synchronous: wait for completion
        await client.wait_for_run(run_id)

        # Get result
        session = await client.get_session(session_id)
        if not session:
            return f"Error: Session '{session_id}' not found after run completed"

        result_text = await client.get_session_result(session_id)
        text, _ = truncate_response(result_text)
        return text

    except APIError as e:
        logger.error("resume_agent_session error", {"error": str(e)})
        return f"Error: {str(e)}"


async def get_agent_session_status_impl(
    config: ServerConfig,
    session_id: str,
    wait_seconds: int = 0,
) -> str:
    """Get session status."""
    logger.info(
        "get_agent_session_status called",
        {
            "session_id": session_id,
            "wait_seconds": wait_seconds,
        },
    )

    try:
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        client = get_api_client(config)
        session = await client.get_session(session_id)

        if not session:
            return json.dumps({"status": "not_existent"}, indent=2)

        status = await client.get_session_status(session_id)
        return json.dumps({"status": status}, indent=2)

    except APIError as e:
        logger.error("get_agent_session_status error", {"error": str(e)})
        return json.dumps({"status": "not_existent"}, indent=2)


async def get_agent_session_result_impl(
    config: ServerConfig,
    session_id: str,
) -> str:
    """Get session result."""
    logger.info("get_agent_session_result called", {"session_id": session_id})

    try:
        client = get_api_client(config)
        session = await client.get_session(session_id)

        if not session:
            return f"Error: Session '{session_id}' does not exist."

        status = await client.get_session_status(session_id)

        if status == "running":
            return f"Error: Session '{session_id}' is still running. Use get_agent_session_status to poll until finished."

        result = await client.get_session_result(session_id)
        text, truncated = truncate_response(result)
        if truncated:
            logger.warn("get_agent_session_result: response truncated")
        return text

    except APIError as e:
        logger.error("get_agent_session_result error", {"error": str(e)})
        return f"Error: {str(e)}"


async def delete_all_agent_sessions_impl(config: ServerConfig) -> str:
    """Delete all agent sessions."""
    logger.info("delete_all_agent_sessions called")

    try:
        client = get_api_client(config)
        sessions = await client.list_sessions()

        if not sessions:
            return "No sessions to delete"

        deleted = 0
        for session in sessions:
            if await client.delete_session(session["session_id"]):
                deleted += 1

        return f"Deleted {deleted} session(s)"

    except APIError as e:
        logger.error("delete_all_agent_sessions error", {"error": str(e)})
        return f"Error: {str(e)}"
