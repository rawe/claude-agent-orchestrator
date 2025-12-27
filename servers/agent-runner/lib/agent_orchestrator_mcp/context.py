"""
HTTP Context Extraction for MCP Server.

Extracts context from HTTP request headers for use in MCP tool handlers.
This provides information about the calling agent session, tags for filtering,
and additional demands for runner selection.
"""

import json
import logging
from typing import Optional

from starlette.requests import Request

from .constants import (
    HEADER_SESSION_ID,
    HEADER_AGENT_TAGS,
    HEADER_ADDITIONAL_DEMANDS,
)
from .schemas import RequestContext

logger = logging.getLogger(__name__)


def extract_context(request: Request) -> RequestContext:
    """Extract context from HTTP request headers.

    Parses the following headers:
    - X-Agent-Session-Id: Parent session ID for callbacks
    - X-Agent-Tags: Comma-separated tags for filtering blueprints
    - X-Additional-Demands: JSON object with hostname, project_dir, etc.

    Args:
        request: Starlette Request object

    Returns:
        RequestContext with extracted values
    """
    # Extract parent session ID
    parent_session_id = request.headers.get(HEADER_SESSION_ID)

    # Extract tags
    tags = request.headers.get(HEADER_AGENT_TAGS)

    # Extract additional demands (JSON)
    additional_demands = {}
    demands_str = request.headers.get(HEADER_ADDITIONAL_DEMANDS)
    if demands_str:
        try:
            additional_demands = json.loads(demands_str)
            if not isinstance(additional_demands, dict):
                logger.warning(
                    f"Invalid {HEADER_ADDITIONAL_DEMANDS} header: expected object, got {type(additional_demands).__name__}"
                )
                additional_demands = {}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse {HEADER_ADDITIONAL_DEMANDS} header: {e}")

    return RequestContext(
        parent_session_id=parent_session_id,
        tags=tags,
        additional_demands=additional_demands,
    )


def get_context_from_scope(scope: dict) -> RequestContext:
    """Extract context from ASGI scope.

    Alternative to extract_context for when we have the raw ASGI scope
    instead of a Starlette Request object.

    Args:
        scope: ASGI connection scope

    Returns:
        RequestContext with extracted values
    """
    headers = dict(scope.get("headers", []))

    # Headers in ASGI scope are bytes
    def get_header(name: str) -> Optional[str]:
        key = name.lower().encode()
        value = headers.get(key)
        if value:
            return value.decode("utf-8", errors="replace")
        return None

    parent_session_id = get_header(HEADER_SESSION_ID)
    tags = get_header(HEADER_AGENT_TAGS)

    additional_demands = {}
    demands_str = get_header(HEADER_ADDITIONAL_DEMANDS)
    if demands_str:
        try:
            additional_demands = json.loads(demands_str)
            if not isinstance(additional_demands, dict):
                additional_demands = {}
        except json.JSONDecodeError:
            pass

    return RequestContext(
        parent_session_id=parent_session_id,
        tags=tags,
        additional_demands=additional_demands,
    )
