"""
HTTP client for Agent API (agent blueprints).

The agent registry is now merged into the agent-coordinator service.

Environment variables:
    AGENT_ORCHESTRATOR_API_URL: API base URL (default: http://localhost:8765)
"""

import urllib.request
import urllib.error
import json
from typing import Optional

from config import get_api_url


class AgentAPIError(Exception):
    """Error communicating with Agent API."""

    pass


def _request(method: str, path: str, data: Optional[dict] = None) -> dict | list | None:
    """Make HTTP request to Agent API."""
    url = f"{get_api_url()}{path}"

    request = urllib.request.Request(url, method=method)
    request.add_header("Content-Type", "application/json")

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(request, body, timeout=10) as response:
            if response.status == 204:
                return None
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        try:
            error_body = json.loads(e.read().decode("utf-8"))
            detail = error_body.get("detail", str(e))
        except Exception:
            detail = str(e)
        raise AgentAPIError(f"API error ({e.code}): {detail}")
    except urllib.error.URLError as e:
        raise AgentAPIError(
            f"Cannot connect to Agent API at {get_api_url()}\n"
            f"Ensure the agent-coordinator service is running: make start-bg\n"
            f"Error: {e.reason}"
        )


def list_agents_api(tags: Optional[str] = None) -> list[dict]:
    """
    List agents from API filtered by tags.

    Args:
        tags: Comma-separated tags. Returns agents with ALL specified tags (AND logic).
              None or empty string returns all agents.

    Returns:
        List of active agent dictionaries matching the tag filter

    Raises:
        AgentAPIError: If API is unavailable or returns error
    """
    path = "/agents"
    if tags:
        path = f"/agents?tags={tags}"
    result = _request("GET", path)
    if not result:
        return []
    # Filter to active agents only
    return [a for a in result if a.get("status") == "active"]


def get_agent_api(name: str) -> Optional[dict]:
    """
    Get agent by name from API.

    Returns:
        Agent dictionary or None if not found

    Raises:
        AgentAPIError: If API is unavailable or returns error
    """
    return _request("GET", f"/agents/{name}")
