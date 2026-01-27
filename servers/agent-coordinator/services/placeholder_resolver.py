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
"""

import os
import re
from typing import Any, Optional

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
