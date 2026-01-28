"""
Run Executor - spawns ao-*-exec subprocess with JSON payload via stdin.

Maps agent run types to execution modes and handles subprocess spawning.
Uses unified ao-*-exec entrypoint with structured JSON payloads.

Schema 2.1: Runner fetches and resolves blueprints before spawning executor.
The executor receives a fully resolved agent_blueprint with placeholders replaced,
and executor_config from the profile (if configured).

Note: Uses session_id (coordinator-generated) per ADR-010.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
import logging

from api_client import Run
from invocation import SCHEMA_VERSION

if TYPE_CHECKING:
    from blueprint_resolver import BlueprintResolver

logger = logging.getLogger(__name__)


# Default executor path and type (used when no profile is specified)
DEFAULT_EXECUTOR_PATH = "executors/claude-code/ao-claude-code-exec"
DEFAULT_EXECUTOR_TYPE = "autonomous"


def get_runner_dir() -> Path:
    """Get the agent-runner directory."""
    return Path(__file__).parent.parent.resolve()


# =============================================================================
# Executor Profiles
# =============================================================================


@dataclass
class ExecutorProfile:
    """Loaded executor profile.

    A profile bundles an executor type with its configuration.
    Profiles are stored as JSON files in the profiles/ directory.

    Attributes:
        name: Profile name (e.g., "coding") - derived from filename
        type: Executor type (e.g., "autonomous" or "procedural") - for coordinator visibility
        command: Relative path to executor script from agent-runner dir
        config: Executor-specific configuration (passed as-is to executor)
        agents_dir: Optional path to agents directory (relative to runner dir)
    """

    name: str
    type: str
    command: str
    config: dict[str, Any]
    agents_dir: Optional[str] = None  # Path to agents directory (relative to runner dir)


def get_profiles_dir() -> Path:
    """Get the profiles directory."""
    return get_runner_dir() / "profiles"


def list_profiles() -> list[str]:
    """List available profile names.

    Scans the profiles/ directory for JSON files.

    Returns:
        List of profile names (without .json extension) sorted alphabetically
    """
    profiles_dir = get_profiles_dir()
    if not profiles_dir.exists():
        return []
    return sorted([p.stem for p in profiles_dir.glob("*.json")])


def load_profile(name: str) -> ExecutorProfile:
    """Load executor profile by name.

    Reads and validates a profile JSON file from the profiles/ directory.

    Args:
        name: Profile name (must match profiles/<name>.json)

    Returns:
        ExecutorProfile with type, command, and config

    Raises:
        RuntimeError: If profile file not found, invalid JSON, or missing required fields
    """
    profile_path = get_profiles_dir() / f"{name}.json"

    if not profile_path.exists():
        available = ", ".join(list_profiles()) or "none"
        raise RuntimeError(f"Profile '{name}' not found. Available: {available}")

    try:
        with open(profile_path) as f:
            profile = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Profile '{name}' has invalid JSON: {e}")

    # Validate required fields
    for field in ("type", "command"):
        if field not in profile:
            raise RuntimeError(f"Profile '{name}' missing required '{field}' field")

    # Validate command path exists
    command_path = get_runner_dir() / profile["command"]
    if not command_path.exists():
        raise RuntimeError(
            f"Profile '{name}' command not found: {profile['command']}"
        )

    return ExecutorProfile(
        name=name,
        type=profile["type"],
        command=profile["command"],
        config=profile.get("config", {}),
        agents_dir=profile.get("agents_dir"),
    )


def load_agents_from_profile(profile: ExecutorProfile) -> list[dict]:
    """Load agents from profile's agents_dir if specified.

    Args:
        profile: Executor profile with optional agents_dir

    Returns:
        List of agent dicts (name, description, command, parameters_schema)
    """
    if not profile.agents_dir:
        return []

    # Resolve path relative to agent-runner directory
    agents_dir = Path(profile.agents_dir)
    if not agents_dir.is_absolute():
        agents_dir = get_runner_dir() / agents_dir

    agents = []
    if agents_dir.exists():
        for path in agents_dir.glob("*.json"):
            with open(path) as f:
                agent = json.load(f)
                agents.append(agent)

    return agents


class RunExecutor:
    """Executes agent runs by spawning executor subprocess with JSON payload.

    Schema 2.1: The executor fetches and resolves blueprints before spawning,
    passing a fully resolved agent_blueprint and executor_config to the executor subprocess.
    """

    def __init__(
        self,
        default_project_dir: str,
        profile: Optional[ExecutorProfile] = None,
        blueprint_resolver: Optional["BlueprintResolver"] = None,
        mcp_server_url: Optional[str] = None,
    ):
        """Initialize executor.

        Args:
            default_project_dir: Default project directory if agent run doesn't specify one
            profile: Optional executor profile with command and config (None = use defaults)
            blueprint_resolver: Optional resolver for fetching and resolving blueprints
            mcp_server_url: Optional MCP server URL for placeholder resolution
        """
        self.default_project_dir = default_project_dir
        self.blueprint_resolver = blueprint_resolver
        self.mcp_server_url = mcp_server_url

        # Resolve executor path and config from profile or defaults
        if profile:
            self.executor_path = get_runner_dir() / profile.command
            self.executor_config = profile.config
        else:
            self.executor_path = get_runner_dir() / DEFAULT_EXECUTOR_PATH
            self.executor_config = {}

        logger.debug(f"Executor path: {self.executor_path}")
        if self.executor_config:
            logger.debug(f"Executor config: {self.executor_config}")
        if blueprint_resolver:
            logger.debug("Blueprint resolver enabled")

    def execute_run(self, run: Run, parent_session_id: Optional[str] = None) -> subprocess.Popen:
        """Execute an agent run by spawning ao-*-exec with JSON payload via stdin.

        Args:
            run: The agent run to execute
            parent_session_id: Optional parent session ID for callback context

        Returns:
            The spawned subprocess.Popen object
        """
        # Map run type to execution mode
        if run.type == "start_session":
            mode = "start"
        elif run.type == "resume_session":
            mode = "resume"
        else:
            raise ValueError(f"Unknown agent run type: {run.type}")

        return self._execute_with_payload(run, mode)

    def _resolve_runner_placeholders(self, blueprint: dict) -> dict:
        """Resolve ${runner.*} placeholders in blueprint.

        This is the ONLY placeholder resolution at Runner level.
        Currently only ${runner.orchestrator_mcp_url} is supported.

        Part of MCP Resolution at Coordinator (mcp-resolution-at-coordinator.md).

        Args:
            blueprint: Agent blueprint with possible ${runner.*} placeholders

        Returns:
            New blueprint with runner placeholders resolved
        """
        import copy
        import re

        RUNNER_PLACEHOLDER = re.compile(r'\$\{runner\.([^}]+)\}')

        def resolve_string(s: str) -> str:
            def replace_match(match: re.Match) -> str:
                key = match.group(1)
                if key == 'orchestrator_mcp_url':
                    return self.mcp_server_url or match.group(0)
                # Unknown runner.* placeholder - keep as-is
                return match.group(0)
            return RUNNER_PLACEHOLDER.sub(replace_match, s)

        def resolve_value(value):
            if isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            elif isinstance(value, str):
                return resolve_string(value)
            else:
                return value

        return resolve_value(copy.deepcopy(blueprint))

    def _build_payload(self, run: Run, mode: str) -> dict:
        """Build JSON payload for ao-*-exec.

        Schema 2.2+: Uses resolved_agent_blueprint from run payload if available
        (mcp-resolution-at-coordinator.md). Falls back to blueprint_resolver for
        backward compatibility.

        Args:
            run: The agent run to execute
            mode: Execution mode ('start' or 'resume')

        Returns:
            Dictionary payload for JSON serialization
        """
        payload = {
            "schema_version": SCHEMA_VERSION,
            "mode": mode,
            "session_id": run.session_id,
            "parameters": run.parameters,
        }

        # Add project_dir for start mode
        if mode == "start":
            project_dir = run.project_dir or self.default_project_dir
            payload["project_dir"] = project_dir

        # Add agent_name if present (for procedural executors)
        if run.agent_name:
            payload["agent_name"] = run.agent_name

        # Add executor_config from profile if present
        if self.executor_config:
            payload["executor_config"] = self.executor_config

        # Use resolved_agent_blueprint from run if available (mcp-resolution-at-coordinator.md)
        # This is the preferred path - blueprint already resolved at Coordinator
        if run.resolved_agent_blueprint:
            # Resolve only ${runner.*} placeholders (e.g., ${runner.orchestrator_mcp_url})
            agent_blueprint = self._resolve_runner_placeholders(run.resolved_agent_blueprint)
            payload["agent_blueprint"] = agent_blueprint
            logger.debug(
                f"Using resolved blueprint from run for session {run.session_id}"
            )
        # Fallback: Resolve blueprint using blueprint_resolver (backward compatibility)
        elif run.agent_name and self.blueprint_resolver:
            try:
                agent_blueprint = self.blueprint_resolver.resolve(
                    agent_name=run.agent_name,
                    session_id=run.session_id,
                    mcp_server_url=self.mcp_server_url,
                )
                payload["agent_blueprint"] = agent_blueprint
                logger.debug(
                    f"Resolved blueprint '{run.agent_name}' for session {run.session_id}:\n"
                    f"{json.dumps(agent_blueprint, indent=2)}"
                )
            except Exception as e:
                logger.error(f"Failed to resolve blueprint '{run.agent_name}': {e}")
                raise

        return payload

    def _execute_with_payload(self, run: Run, mode: str) -> subprocess.Popen:
        """Execute executor with JSON payload via stdin.

        Args:
            run: The agent run to execute
            mode: Execution mode ('start' or 'resume')

        Returns:
            The spawned subprocess.Popen object
        """
        # Build JSON payload
        payload = self._build_payload(run, mode)
        payload_json = json.dumps(payload)

        # Build command - use 'uv run --script' for cross-platform compatibility
        # (Windows doesn't support shebangs, so we need explicit uv invocation)
        cmd = ["uv", "run", "--script", str(self.executor_path)]

        # Build environment
        env = os.environ.copy()

        # Set AGENT_SESSION_ID so the session knows its own identity.
        # This allows MCP servers to include the session ID in HTTP headers
        # for callback support (X-Agent-Session-Id header).
        # Flow: Runner sets env -> ao-*-exec replaces ${AGENT_SESSION_ID} in MCP config
        #       -> Claude sends X-Agent-Session-Id header -> MCP server reads it
        env["AGENT_SESSION_ID"] = run.session_id

        # Log action (don't log full payload - prompt may be large/sensitive)
        if mode == "start":
            logger.info(
                f"Starting session: {run.session_id}"
                + (f" (agent={run.agent_name})" if run.agent_name else "")
            )
        else:
            logger.info(f"Resuming session: {run.session_id}")

        if run.prompt:
            logger.debug(
                f"Executing ao-*-exec: mode={mode} session={run.session_id} "
                f"prompt_len={len(run.prompt)}"
            )
        else:
            logger.debug(
                f"Executing ao-*-exec: mode={mode} session={run.session_id} "
                f"parameters={list(run.parameters.keys()) if run.parameters else []}"
            )

        # Spawn subprocess with stdin pipe
        # encoding='utf-8' required for Windows (defaults to CP1252 which can't handle emojis)
        # cwd is set for start mode so the executor runs in the correct project directory
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=payload.get("project_dir") or self.default_project_dir,
            text=True,
            encoding='utf-8',
            errors='replace',
        )

        # Write payload to stdin and close
        process.stdin.write(payload_json)
        process.stdin.close()

        return process
