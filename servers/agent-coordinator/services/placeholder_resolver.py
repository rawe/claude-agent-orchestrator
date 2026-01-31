"""
Resolve placeholders in agent blueprint configuration.

Part of MCP Resolution at Coordinator (mcp-resolution-at-coordinator.md).

Placeholder Sources:
- params: Agent input parameters (${params.X})
- scope: Run scope, LLM-invisible context (${scope.X})
- env: Coordinator's environment variables (${env.X})
- runtime: Framework context like session_id, run_id (${runtime.X})
- runner: Runner-specific values - NOT resolved here (${runner.X})

The 'runner' source is special - values like ${runner.orchestrator_mcp_url}
are left unresolved because only the Runner knows the dynamic port.

Phase 2 Extension (mcp-server-registry.md):
- MCP server refs are resolved from the registry
- Config inheritance: registry defaults → capability → agent → run
- Required config validation using config_schema
"""

import os
import re
from typing import Any, Optional

from services.mcp_registry import (
    get_mcp_server,
    validate_required_config,
    MCPServerNotFoundError,
)

# Pattern for ${source.key} placeholders
PLACEHOLDER_PATTERN = re.compile(r'\$\{([^}]+)\}')

# Placeholders with these prefixes are NOT resolved at Coordinator
# They will be resolved by the Runner at execution time
RUNNER_PREFIXES = ('runner.',)


class PlaceholderResolver:
    """Resolves ${source.key} placeholders in agent blueprint.

    Supports these placeholder sources:
    - params: From run parameters (e.g., ${params.repo_url})
    - scope: From run scope (e.g., ${scope.context_id})
    - env: From Coordinator environment (e.g., ${env.API_KEY})
    - runtime: From run context (e.g., ${runtime.session_id}, ${runtime.run_id})

    Placeholders with 'runner.' prefix are left unresolved.
    """

    def __init__(
        self,
        params: Optional[dict] = None,
        scope: Optional[dict] = None,
        run_id: str = "",
        session_id: str = "",
    ):
        """Initialize resolver with context.

        Args:
            params: Run parameters from request (for ${params.X})
            scope: Run scope from request (for ${scope.X})
            run_id: Current run ID (for ${runtime.run_id})
            session_id: Current session ID (for ${runtime.session_id})
        """
        self.params = params or {}
        self.scope = scope or {}
        self.run_id = run_id
        self.session_id = session_id

    def resolve(self, agent_blueprint: dict) -> dict:
        """Resolve all placeholders in agent blueprint.

        Placeholders with 'runner.' prefix are left unresolved
        (they will be resolved by the Runner).

        Args:
            agent_blueprint: Agent configuration dict

        Returns:
            New dict with placeholders replaced (deep copy)
        """
        return self._resolve_value(agent_blueprint)

    def _resolve_value(self, value: Any) -> Any:
        """Recursively resolve placeholders in any value."""
        if isinstance(value, dict):
            return {k: self._resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_value(item) for item in value]
        elif isinstance(value, str):
            return self._resolve_string(value)
        else:
            return value

    def _resolve_string(self, s: str) -> str:
        """Resolve placeholders in a string value."""
        def replace_match(match: re.Match) -> str:
            placeholder = match.group(1)  # e.g., "scope.context_id"

            # Skip runner.* placeholders (resolved by Runner)
            if placeholder.startswith(RUNNER_PREFIXES):
                return match.group(0)  # Keep as-is

            value = self._get_value(placeholder)
            if value is None:
                # Unresolved placeholder - keep as-is
                # Could log warning here if desired
                return match.group(0)

            return str(value)

        return PLACEHOLDER_PATTERN.sub(replace_match, s)

    def _get_value(self, placeholder: str) -> Optional[Any]:
        """Get value for a placeholder like 'scope.context_id'.

        Args:
            placeholder: Placeholder string without ${} wrapper

        Returns:
            Resolved value or None if not found
        """
        parts = placeholder.split('.', 1)
        if len(parts) != 2:
            return None

        source, key = parts

        if source == 'params':
            return self.params.get(key)
        elif source == 'scope':
            return self.scope.get(key)
        elif source == 'env':
            return os.environ.get(key)
        elif source == 'runtime':
            if key == 'session_id':
                return self.session_id
            elif key == 'run_id':
                return self.run_id

        return None


# ==============================================================================
# MCP Server Reference Resolution (Phase 2: mcp-server-registry.md)
# ==============================================================================

class MCPRefResolutionError(Exception):
    """Raised when MCP server reference resolution fails."""
    def __init__(self, server_name: str, ref: str, reason: str):
        self.server_name = server_name
        self.ref = ref
        self.reason = reason
        super().__init__(f"Failed to resolve MCP server '{server_name}' (ref: {ref}): {reason}")


class MissingRequiredConfigError(Exception):
    """Raised when required config values are missing after resolution."""
    def __init__(self, server_name: str, missing_fields: list[str]):
        self.server_name = server_name
        self.missing_fields = missing_fields
        super().__init__(
            f"MCP server '{server_name}' missing required config: {', '.join(missing_fields)}"
        )


def resolve_mcp_server_refs(
    mcp_servers: dict,
    placeholder_resolver: Optional[PlaceholderResolver] = None,
    validate_required: bool = True,
) -> dict:
    """Resolve MCP server references from the registry.

    For each server entry with a 'ref' field:
    1. Look up the registry entry
    2. Merge configs: registry defaults → provided config
    3. Resolve placeholders in config values
    4. Optionally validate required config values

    Args:
        mcp_servers: Dict of server_name -> config (may have 'ref' or inline type/url)
        placeholder_resolver: Optional resolver for placeholder substitution
        validate_required: If True, validate required config values

    Returns:
        Dict of server_name -> resolved config with 'url' and 'config' keys

    Raises:
        MCPRefResolutionError: If a ref cannot be resolved
        MissingRequiredConfigError: If required config values are missing
    """
    if not mcp_servers:
        return {}

    resolved = {}
    for server_name, server_config in mcp_servers.items():
        # Check if this is a ref-based config
        if isinstance(server_config, dict) and "ref" in server_config:
            ref = server_config["ref"]
            provided_config = server_config.get("config", {})

            # Look up registry entry
            entry = get_mcp_server(ref)
            if not entry:
                raise MCPRefResolutionError(
                    server_name, ref, f"Not found in registry"
                )

            # Merge configs: registry defaults → provided config
            merged_config = {}
            if entry.default_config:
                merged_config.update(entry.default_config)
            if provided_config:
                merged_config.update(provided_config)

            # Resolve placeholders in config values
            if placeholder_resolver:
                merged_config = placeholder_resolver.resolve(merged_config)

            # Validate required config values
            if validate_required and entry.config_schema:
                missing = validate_required_config(merged_config, entry.config_schema)
                if missing:
                    raise MissingRequiredConfigError(server_name, missing)

            resolved[server_name] = {
                "url": entry.url,
                "config": merged_config,
            }
        else:
            # Inline format not supported - must use ref format
            raise MCPRefResolutionError(
                server_name, "(inline)",
                "Inline format not supported. Use ref format with registry entry."
            )

    return resolved


def resolve_blueprint_with_registry(
    agent_blueprint: dict,
    placeholder_resolver: Optional[PlaceholderResolver] = None,
    validate_required: bool = True,
) -> dict:
    """Resolve an agent blueprint with registry lookups and placeholder resolution.

    This is the main entry point for Phase 2 blueprint resolution.

    Steps:
    1. Resolve MCP server refs from registry
    2. Merge configs (registry defaults → blueprint config)
    3. Resolve placeholders in all values
    4. Validate required config values

    Args:
        agent_blueprint: Agent configuration dict
        placeholder_resolver: Resolver for placeholder substitution
        validate_required: If True, validate required MCP config values

    Returns:
        Resolved blueprint dict with fully resolved MCP servers

    Raises:
        MCPRefResolutionError: If an MCP server ref cannot be resolved
        MissingRequiredConfigError: If required config values are missing
    """
    # Start with a copy to avoid mutation
    result = dict(agent_blueprint)

    # Resolve MCP server refs if present
    if "mcp_servers" in result and result["mcp_servers"]:
        result["mcp_servers"] = resolve_mcp_server_refs(
            result["mcp_servers"],
            placeholder_resolver,
            validate_required,
        )

    # Resolve remaining placeholders in the entire blueprint
    if placeholder_resolver:
        result = placeholder_resolver.resolve(result)

    return result
