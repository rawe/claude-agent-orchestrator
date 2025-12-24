"""
Blueprint Resolver - fetches and resolves agent blueprints.

Fetches agent blueprints from Agent Coordinator and resolves placeholders
in the mcp_servers configuration before passing to executors.

This is part of Schema 2.0 which moves blueprint resolution from the
executor to the Agent Runner.
"""

import copy
import logging
from typing import Optional, Any, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from auth0_client import Auth0M2MClient

logger = logging.getLogger(__name__)


class BlueprintNotFoundError(Exception):
    """Raised when a blueprint cannot be found."""
    pass


class BlueprintResolver:
    """
    Fetches agent blueprints from Coordinator and resolves placeholders.

    Supports the following placeholders in mcp_servers configuration:
    - ${AGENT_ORCHESTRATOR_MCP_URL}: Replaced with the MCP server URL
    - ${AGENT_SESSION_ID}: Replaced with the current session ID
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
        # Fetch blueprint from Coordinator
        blueprint = self._fetch_blueprint(agent_name)

        # Resolve placeholders
        return self.resolve_placeholders(
            blueprint=blueprint,
            session_id=session_id,
            mcp_server_url=mcp_server_url,
        )

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

    def resolve_placeholders(
        self,
        blueprint: dict,
        session_id: str,
        mcp_server_url: Optional[str] = None,
    ) -> dict:
        """
        Resolve placeholders in blueprint's mcp_servers config.

        Recursively walks mcp_servers and replaces:
        - ${AGENT_ORCHESTRATOR_MCP_URL} -> mcp_server_url
        - ${AGENT_SESSION_ID} -> session_id

        Placeholders without matching values pass through unchanged.

        Args:
            blueprint: Blueprint dict to resolve
            session_id: Session ID for placeholder replacement
            mcp_server_url: MCP server URL for placeholder replacement

        Returns:
            New blueprint dict with resolved placeholders
        """
        result = copy.deepcopy(blueprint)
        mcp_servers = result.get("mcp_servers", {})

        if not mcp_servers:
            return result

        for server_name, config in mcp_servers.items():
            if not isinstance(config, dict):
                continue

            # Resolve URL placeholder
            if "url" in config and isinstance(config["url"], str):
                config["url"] = self._resolve_string(
                    config["url"],
                    session_id=session_id,
                    mcp_server_url=mcp_server_url,
                )

            # Resolve headers placeholders
            headers = config.get("headers", {})
            if isinstance(headers, dict):
                for key, value in headers.items():
                    if isinstance(value, str):
                        headers[key] = self._resolve_string(
                            value,
                            session_id=session_id,
                            mcp_server_url=mcp_server_url,
                        )

            # Resolve args list (for command-based MCP servers)
            args = config.get("args", [])
            if isinstance(args, list):
                config["args"] = [
                    self._resolve_string(arg, session_id=session_id, mcp_server_url=mcp_server_url)
                    if isinstance(arg, str) else arg
                    for arg in args
                ]

            # Resolve env dict (for command-based MCP servers)
            env = config.get("env", {})
            if isinstance(env, dict):
                for key, value in env.items():
                    if isinstance(value, str):
                        env[key] = self._resolve_string(
                            value,
                            session_id=session_id,
                            mcp_server_url=mcp_server_url,
                        )

        return result

    def _resolve_string(
        self,
        value: str,
        session_id: str,
        mcp_server_url: Optional[str],
    ) -> str:
        """Resolve placeholders in a string value.

        Args:
            value: String that may contain placeholders
            session_id: Session ID replacement value
            mcp_server_url: MCP server URL replacement value

        Returns:
            String with placeholders resolved
        """
        result = value

        # Replace session ID placeholder
        result = result.replace("${AGENT_SESSION_ID}", session_id)

        # Replace MCP URL placeholder only if we have a URL
        if mcp_server_url:
            result = result.replace("${AGENT_ORCHESTRATOR_MCP_URL}", mcp_server_url)

        return result

    def close(self):
        """Close the HTTP client."""
        self._http.close()
