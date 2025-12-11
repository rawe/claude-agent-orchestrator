"""
Core functions for Agent Orchestrator MCP Server.

These functions implement the actual logic by calling the Agent Runtime API.
They are used by both the MCP tools and the REST API.
"""

import asyncio
import json
import os
from typing import Literal, Optional

from api_client import APIClient, APIError
from constants import (
    CHARACTER_LIMIT,
    ENV_AGENT_SESSION_NAME,
    HEADER_AGENT_SESSION_NAME,
    ENV_AGENT_TAGS,
    HEADER_AGENT_TAGS,
)
from logger import logger
from types_models import ServerConfig


def get_api_client(config: ServerConfig) -> APIClient:
    """Get API client instance."""
    return APIClient(config.api_url)


def get_parent_session_name(http_headers: Optional[dict] = None) -> Optional[str]:
    """
    Get parent session name from environment or HTTP headers.

    - stdio mode: reads from AGENT_SESSION_NAME env var
    - HTTP mode: reads from X-Agent-Session-Name header
    """
    # Try HTTP header first (if provided)
    if http_headers:
        # HTTP headers are case-insensitive; get_http_headers() returns lowercase keys
        header_key_lower = HEADER_AGENT_SESSION_NAME.lower()
        parent = http_headers.get(header_key_lower)
        if parent:
            return parent

    # Fall back to environment variable
    return os.environ.get(ENV_AGENT_SESSION_NAME)


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
                lines.append(f"## {s.get('session_name', 'unknown')}")
                lines.append(f"- **Session ID**: {s.get('session_id', 'unknown')}")
                lines.append(f"- **Status**: {s.get('status', 'unknown')}")
                lines.append(f"- **Project Directory**: {s.get('project_dir', 'N/A')}")
                lines.append("")
            return "\n".join(lines)

    except APIError as e:
        logger.error("list_agent_sessions error", {"error": str(e)})
        return f"Error: {str(e)}"


async def start_agent_session_impl(
    config: ServerConfig,
    session_name: str,
    prompt: str,
    agent_blueprint_name: Optional[str] = None,
    project_dir: Optional[str] = None,
    async_mode: bool = False,
    callback: bool = False,
    http_headers: Optional[dict] = None,
) -> str:
    """Start a new agent session."""
    logger.info(
        "start_agent_session called",
        {
            "session_name": session_name,
            "agent_blueprint_name": agent_blueprint_name,
            "async_mode": async_mode,
            "callback": callback,
        },
    )

    try:
        client = get_api_client(config)

        # Get parent session name for callback support
        parent_session_name = None
        if callback:
            parent_session_name = get_parent_session_name(http_headers)
            if not parent_session_name:
                logger.warn("callback=true but no parent session name available")

        # Create job
        # Note: If project_dir is None, the Agent Runtime/Launcher decides the default
        job_id = await client.create_job(
            job_type="start_session",
            session_name=session_name,
            prompt=prompt,
            agent_name=agent_blueprint_name,
            project_dir=project_dir,
            parent_session_name=parent_session_name,
        )

        logger.info(f"Created job {job_id} for session {session_name}")

        if async_mode:
            # Return immediately
            response = {
                "session_name": session_name,
                "job_id": job_id,
                "status": "running",
                "message": "Agent started in background. Use get_agent_session_status to poll for completion.",
            }
            if callback and parent_session_name:
                response["callback_to"] = parent_session_name
            return json.dumps(response, indent=2)

        # Synchronous: wait for completion
        logger.info(f"Waiting for job {job_id} to complete...")
        await client.wait_for_job(job_id)

        # Get result from session
        session = await client.get_session_by_name(session_name)
        if not session:
            return f"Error: Session '{session_name}' not found after job completed"

        result = await client.get_session_result(session["session_id"])
        text, truncated = truncate_response(result)
        if truncated:
            logger.warn("start_agent_session: response truncated")
        return text

    except APIError as e:
        logger.error("start_agent_session error", {"error": str(e)})
        return f"Error: {str(e)}"


async def resume_agent_session_impl(
    config: ServerConfig,
    session_name: str,
    prompt: str,
    async_mode: bool = False,
    callback: bool = False,
    http_headers: Optional[dict] = None,
) -> str:
    """Resume an existing agent session."""
    logger.info(
        "resume_agent_session called",
        {
            "session_name": session_name,
            "async_mode": async_mode,
            "callback": callback,
        },
    )

    try:
        client = get_api_client(config)

        # Get parent session name for callback support
        parent_session_name = None
        if callback:
            parent_session_name = get_parent_session_name(http_headers)
            if not parent_session_name:
                logger.warn("callback=true but no parent session name available")

        # Create resume job
        job_id = await client.create_job(
            job_type="resume_session",
            session_name=session_name,
            prompt=prompt,
            parent_session_name=parent_session_name,
        )

        logger.info(f"Created resume job {job_id} for session {session_name}")

        if async_mode:
            response = {
                "session_name": session_name,
                "job_id": job_id,
                "status": "running",
                "message": "Agent resumed in background. Use get_agent_session_status to poll for completion.",
            }
            if callback and parent_session_name:
                response["callback_to"] = parent_session_name
            return json.dumps(response, indent=2)

        # Synchronous: wait for completion
        await client.wait_for_job(job_id)

        # Get result
        session = await client.get_session_by_name(session_name)
        if not session:
            return f"Error: Session '{session_name}' not found after job completed"

        result = await client.get_session_result(session["session_id"])
        text, _ = truncate_response(result)
        return text

    except APIError as e:
        logger.error("resume_agent_session error", {"error": str(e)})
        return f"Error: {str(e)}"


async def get_agent_session_status_impl(
    config: ServerConfig,
    session_name: str,
    wait_seconds: int = 0,
) -> str:
    """Get session status."""
    logger.info(
        "get_agent_session_status called",
        {
            "session_name": session_name,
            "wait_seconds": wait_seconds,
        },
    )

    try:
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        client = get_api_client(config)
        session = await client.get_session_by_name(session_name)

        if not session:
            return json.dumps({"status": "not_existent"}, indent=2)

        status = await client.get_session_status(session["session_id"])
        return json.dumps({"status": status}, indent=2)

    except APIError as e:
        logger.error("get_agent_session_status error", {"error": str(e)})
        return json.dumps({"status": "not_existent"}, indent=2)


async def get_agent_session_result_impl(
    config: ServerConfig,
    session_name: str,
) -> str:
    """Get session result."""
    logger.info("get_agent_session_result called", {"session_name": session_name})

    try:
        client = get_api_client(config)
        session = await client.get_session_by_name(session_name)

        if not session:
            return f"Error: Session '{session_name}' does not exist."

        status = await client.get_session_status(session["session_id"])

        if status == "running":
            return f"Error: Session '{session_name}' is still running. Use get_agent_session_status to poll until finished."

        result = await client.get_session_result(session["session_id"])
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
