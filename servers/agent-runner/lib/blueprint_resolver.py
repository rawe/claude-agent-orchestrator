"""
Blueprint Resolver - fetches and resolves agent blueprints.

Uses Pydantic models for type-safe MCP server configuration handling.
This ensures HTTP servers never get stdio-specific fields (like args) and vice versa.

Part of Schema 2.0: Runner resolves blueprints before passing to executors.
"""

import copy
import logging
from typing import Optional, Literal, Union, TYPE_CHECKING

import httpx
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from auth0_client import Auth0M2MClient

logger = logging.getLogger(__name__)


# =============================================================================
# Placeholder Resolution
# =============================================================================

def _resolve_string(
    value: str,
    session_id: str,
    mcp_server_url: Optional[str],
) -> str:
    """Resolve placeholders in a string value.

    Supported placeholders:
    - ${AGENT_SESSION_ID}: Current session identifier
    - ${AGENT_ORCHESTRATOR_MCP_URL}: Runner's embedded MCP server URL
    """
    result = value.replace("${AGENT_SESSION_ID}", session_id)
    if mcp_server_url:
        result = result.replace("${AGENT_ORCHESTRATOR_MCP_URL}", mcp_server_url)
    return result


# =============================================================================
# MCP Server Models (Runner's view of the API contract)
# =============================================================================

class MCPServerHttp(BaseModel):
    """HTTP transport MCP server configuration.

    Fields: type, url, headers (optional)
    Note: No args/command/env - those are stdio-specific.
    """

    model_config = ConfigDict(extra="ignore")  # Forward-compatible with new fields

    type: Literal["http"]
    url: str
    headers: Optional[dict[str, str]] = None

    def with_resolved_placeholders(
        self,
        session_id: str,
        mcp_server_url: Optional[str] = None,
    ) -> "MCPServerHttp":
        """Create new instance with placeholders resolved."""
        resolved_url = _resolve_string(self.url, session_id, mcp_server_url)

        resolved_headers = None
        if self.headers:
            resolved_headers = {
                key: _resolve_string(value, session_id, mcp_server_url)
                for key, value in self.headers.items()
            }

        return MCPServerHttp(
            type=self.type,
            url=resolved_url,
            headers=resolved_headers,
        )


class MCPServerStdio(BaseModel):
    """Stdio transport MCP server configuration.

    Fields: type, command, args, env (optional)
    Note: No url/headers - those are HTTP-specific.
    """

    model_config = ConfigDict(extra="ignore")  # Forward-compatible with new fields

    type: Literal["stdio"]
    command: str
    args: list[str] = []
    env: Optional[dict[str, str]] = None

    def with_resolved_placeholders(
        self,
        session_id: str,
        mcp_server_url: Optional[str] = None,
    ) -> "MCPServerStdio":
        """Create new instance with placeholders resolved."""
        resolved_command = _resolve_string(self.command, session_id, mcp_server_url)

        resolved_args = [
            _resolve_string(arg, session_id, mcp_server_url)
            for arg in self.args
        ]

        resolved_env = None
        if self.env:
            resolved_env = {
                key: _resolve_string(value, session_id, mcp_server_url)
                for key, value in self.env.items()
            }

        return MCPServerStdio(
            type=self.type,
            command=resolved_command,
            args=resolved_args,
            env=resolved_env,
        )


# Union type for type-safe handling
MCPServerConfig = Union[MCPServerHttp, MCPServerStdio]


def parse_mcp_server(name: str, config: dict) -> MCPServerConfig:
    """Parse MCP server config dict into appropriate typed model.

    Args:
        name: Server name (for error messages)
        config: Raw config dict from API

    Returns:
        Typed MCP server model (MCPServerHttp or MCPServerStdio)

    Raises:
        ValueError: If server type is unknown or invalid
    """
    server_type = config.get("type")

    if server_type == "http":
        return MCPServerHttp.model_validate(config)
    elif server_type == "stdio":
        return MCPServerStdio.model_validate(config)
    else:
        raise ValueError(f"Unknown MCP server type '{server_type}' for '{name}'")


# =============================================================================
# Blueprint Resolver
# =============================================================================

class BlueprintNotFoundError(Exception):
    """Raised when a blueprint cannot be found."""
    pass


class BlueprintResolver:
    """
    Fetches agent blueprints from Coordinator and resolves placeholders.

    Uses typed Pydantic models to ensure type-safe placeholder resolution.
    HTTP servers only get HTTP fields, stdio servers only get stdio fields.

    Supported placeholders in mcp_servers configuration:
    - ${AGENT_ORCHESTRATOR_MCP_URL}: Runner's embedded MCP server URL
    - ${AGENT_SESSION_ID}: Current session identifier
    """

    def __init__(
        self,
        coordinator_url: str,
        auth0_client: Optional["Auth0M2MClient"] = None,
    ):
        """Initialize BlueprintResolver.

        Args:
            coordinator_url: Agent Coordinator API URL
            auth0_client: Auth0 client for authenticated API calls
        """
        self._coordinator_url = coordinator_url.rstrip("/")
        self._auth0_client = auth0_client
        self._http = httpx.Client(timeout=30.0)

    def _get_auth_headers(self) -> dict:
        """Get Authorization header if auth configured."""
        if self._auth0_client and self._auth0_client.is_configured:
            token = self._auth0_client.get_access_token()
            if token:
                return {"Authorization": f"Bearer {token}"}
        return {}

    def resolve(
        self,
        agent_name: str,
        session_id: str,
        mcp_server_url: Optional[str] = None,
    ) -> dict:
        """
        Fetch blueprint and resolve placeholders.

        Args:
            agent_name: Blueprint name to fetch
            session_id: For ${AGENT_SESSION_ID} replacement
            mcp_server_url: For ${AGENT_ORCHESTRATOR_MCP_URL} replacement

        Returns:
            Resolved agent_blueprint dict

        Raises:
            BlueprintNotFoundError: If blueprint doesn't exist
        """
        blueprint = self._fetch_blueprint(agent_name)
        return self._resolve_blueprint(blueprint, session_id, mcp_server_url)

    def _fetch_blueprint(self, agent_name: str) -> dict:
        """Fetch blueprint from Coordinator API.

        Args:
            agent_name: Name of the agent blueprint

        Returns:
            Blueprint dict

        Raises:
            BlueprintNotFoundError: If blueprint not found
        """
        try:
            response = self._http.get(
                f"{self._coordinator_url}/agents/{agent_name}",
                headers=self._get_auth_headers(),
            )

            if response.status_code == 404:
                raise BlueprintNotFoundError(f"Blueprint not found: {agent_name}")

            response.raise_for_status()
            data = response.json()

            # The API returns the agent in an "agent" wrapper
            agent = data.get("agent", data)
            if not agent:
                raise BlueprintNotFoundError(f"Blueprint not found: {agent_name}")

            logger.debug(f"Fetched blueprint: {agent_name}")
            return agent

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch blueprint {agent_name}: {e}")
            raise BlueprintNotFoundError(f"Failed to fetch blueprint: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error fetching blueprint {agent_name}: {e}")
            raise BlueprintNotFoundError(f"Request error: {e}")

    def _resolve_blueprint(
        self,
        blueprint: dict,
        session_id: str,
        mcp_server_url: Optional[str],
    ) -> dict:
        """
        Resolve placeholders in blueprint using typed models.

        Process:
        1. Parse each MCP server config into typed model (validates structure)
        2. Call with_resolved_placeholders() to create resolved instance
        3. Serialize back to dict with exclude_none=True (clean output)

        Args:
            blueprint: Raw blueprint dict from API
            session_id: Session ID for placeholder replacement
            mcp_server_url: MCP server URL for placeholder replacement

        Returns:
            New blueprint dict with resolved MCP servers
        """
        result = copy.deepcopy(blueprint)
        raw_mcp_servers = result.get("mcp_servers", {})

        if not raw_mcp_servers:
            return result

        resolved_servers = {}
        for name, config in raw_mcp_servers.items():
            if not isinstance(config, dict):
                logger.warning(f"Skipping invalid MCP server config '{name}': not a dict")
                continue

            try:
                # Parse into typed model (validates structure)
                server = parse_mcp_server(name, config)

                # Resolve placeholders (returns new immutable instance)
                resolved = server.with_resolved_placeholders(session_id, mcp_server_url)

                # Serialize to dict (exclude_none ensures clean output)
                resolved_servers[name] = resolved.model_dump(
                    mode="json",
                    exclude_none=True,
                )

            except ValueError as e:
                # Unknown server type - pass through unmodified
                logger.warning(f"Skipping MCP server '{name}': {e}")
                resolved_servers[name] = config
            except Exception as e:
                # Validation error - pass through unmodified
                logger.warning(f"Failed to parse MCP server '{name}': {e}")
                resolved_servers[name] = config

        result["mcp_servers"] = resolved_servers
        return result

    def close(self):
        """Close the HTTP client."""
        self._http.close()
