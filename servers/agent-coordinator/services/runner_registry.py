"""
Runner registry for tracking registered runner instances.

Runners register on startup and send periodic heartbeats to stay alive.
Runner identity is deterministically derived from (hostname, project_dir, executor_profile)
to enable automatic reconnection recognition. See ADR-012.
"""

import hashlib
import threading
from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel


class DuplicateRunnerError(Exception):
    """Raised when attempting to register a runner with an identity that's already online."""

    def __init__(self, runner_id: str, hostname: str, project_dir: str, executor_profile: str):
        self.runner_id = runner_id
        self.hostname = hostname
        self.project_dir = project_dir
        self.executor_profile = executor_profile
        super().__init__(
            f"Runner with identity ({hostname}, {project_dir}, {executor_profile}) "
            f"is already registered and online as {runner_id}"
        )


def derive_runner_id(hostname: str, project_dir: str, executor_profile: str, executor_command: str) -> str:
    """
    Deterministically derive runner_id from identifying properties.

    Same properties always produce same ID (enables reconnection recognition).
    This is an internal implementation detail, not exposed to runners.

    Args:
        hostname: The machine hostname where the runner is running
        project_dir: The default project directory for this runner
        executor_profile: The executor profile name (e.g., 'coding', 'research')
        executor_command: The executor command path (ensures uniqueness across profiles)

    Returns:
        Runner ID in format: lnch_{sha256_hash[:12]}
    """
    # Normalize inputs - include command to ensure uniqueness even with same executor type
    key = f"{hostname}:{project_dir}:{executor_profile}:{executor_command}"

    # Generate deterministic hash
    hash_hex = hashlib.sha256(key.encode()).hexdigest()

    # Format with prefix
    return f"lnch_{hash_hex[:12]}"


class RunnerStatus:
    """Runner status constants."""
    ONLINE = "online"
    STALE = "stale"


class RunnerInfo(BaseModel):
    """Information about a registered runner."""
    runner_id: str
    registered_at: str
    last_heartbeat: str
    # Identifying properties (required for ID derivation)
    hostname: str
    project_dir: str
    executor_profile: str
    # Executor details
    executor: dict = {}  # {type, command, config, agents_dir}
    # Capabilities (features the runner offers)
    tags: list[str] = []
    require_matching_tags: bool = False  # If true, only accept runs with matching tags
    # Status managed by coordinator
    status: Literal["online", "stale"] = RunnerStatus.ONLINE


class RunnerRegistry:
    """Thread-safe registry for tracking runners and their agents."""

    def __init__(self, heartbeat_timeout_seconds: int = 120):
        self._runners: dict[str, RunnerInfo] = {}
        self._runner_agents: dict[str, list[dict]] = {}  # runner_id -> list of agent dicts
        self._deregistered: set[str] = set()  # IDs pending deregistration signal
        self._lock = threading.Lock()
        self._heartbeat_timeout = heartbeat_timeout_seconds

    def register_runner(
        self,
        hostname: str,
        project_dir: str,
        executor_profile: str,
        executor: Optional[dict] = None,
        tags: Optional[list[str]] = None,
        require_matching_tags: bool = False,
    ) -> RunnerInfo:
        """Register a runner and return its info.

        If a runner with the same (hostname, project_dir, executor_profile) already exists:
        - If ONLINE: Raises DuplicateRunnerError (cannot have two runners with same identity)
        - If STALE: Treated as reconnection (old runner probably crashed)

        Otherwise, a new runner record is created.

        Args:
            hostname: The machine hostname where the runner is running
            project_dir: The default project directory for this runner
            executor_profile: The executor profile name (e.g., 'coding', 'research')
            executor: Executor details dict with {type, command, config}
            tags: Optional list of capability tags this runner offers
            require_matching_tags: If true, only accept runs with at least one matching tag

        Returns:
            RunnerInfo with the runner_id derived from the properties

        Raises:
            DuplicateRunnerError: If an online runner with the same identity already exists
        """
        # Extract executor command for runner ID derivation
        executor_command = executor.get("command", "") if executor else ""

        # Derive deterministic runner_id from properties (including command for uniqueness)
        runner_id = derive_runner_id(hostname, project_dir, executor_profile, executor_command)
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            existing = self._runners.get(runner_id)
            if existing:
                # Check if existing runner is online (reject duplicate)
                if existing.status == RunnerStatus.ONLINE:
                    raise DuplicateRunnerError(
                        runner_id=runner_id,
                        hostname=hostname,
                        project_dir=project_dir,
                        executor_profile=executor_profile,
                    )

                # Stale runner: treat as reconnection (old runner probably crashed)
                existing.last_heartbeat = now
                existing.status = RunnerStatus.ONLINE
                # Update fields on reconnection (runner may have new capabilities)
                if tags is not None:
                    existing.tags = tags
                if executor is not None:
                    existing.executor = executor
                existing.require_matching_tags = require_matching_tags
                # Remove from deregistered set if it was marked
                self._deregistered.discard(runner_id)
                return existing

            # New registration
            runner = RunnerInfo(
                runner_id=runner_id,
                registered_at=now,
                last_heartbeat=now,
                hostname=hostname,
                project_dir=project_dir,
                executor_profile=executor_profile,
                executor=executor or {},
                tags=tags or [],
                require_matching_tags=require_matching_tags,
                status=RunnerStatus.ONLINE,
            )
            self._runners[runner_id] = runner
            return runner

    def heartbeat(self, runner_id: str) -> bool:
        """Update last heartbeat timestamp.

        Returns True if runner exists, False otherwise.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            runner = self._runners.get(runner_id)
            if not runner:
                return False

            runner.last_heartbeat = now
            return True

    def get_runner(self, runner_id: str) -> Optional[RunnerInfo]:
        """Get runner info by ID."""
        with self._lock:
            return self._runners.get(runner_id)

    def get_seconds_since_heartbeat(self, runner_id: str) -> float | None:
        """Get seconds since last heartbeat for a runner.

        Returns None if runner not found.
        """
        with self._lock:
            runner = self._runners.get(runner_id)
            if not runner:
                return None

            last_hb = datetime.fromisoformat(runner.last_heartbeat.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return (now - last_hb).total_seconds()

    def is_runner_alive(self, runner_id: str) -> bool:
        """Check if runner is registered and has sent a recent heartbeat."""
        seconds = self.get_seconds_since_heartbeat(runner_id)
        if seconds is None:
            return False
        return seconds < self._heartbeat_timeout

    def get_all_runners(self) -> list[RunnerInfo]:
        """Get all registered runners."""
        with self._lock:
            return list(self._runners.values())

    def _remove_runner_agents_unlocked(self, runner_id: str) -> int:
        """Internal helper to remove runner agents without acquiring lock.

        Must be called while holding self._lock.
        """
        agents = self._runner_agents.pop(runner_id, [])
        return len(agents)

    def remove_runner(self, runner_id: str) -> bool:
        """Remove a runner and its agents from the registry.

        Returns True if runner was removed, False if not found.
        """
        with self._lock:
            if runner_id in self._runners:
                del self._runners[runner_id]
                self._remove_runner_agents_unlocked(runner_id)
                return True
            return False

    def mark_deregistered(self, runner_id: str) -> bool:
        """Mark a runner for deregistration.

        The runner will be signaled on its next poll and then removed.
        Returns True if runner exists, False otherwise.
        """
        with self._lock:
            if runner_id not in self._runners:
                return False
            self._deregistered.add(runner_id)
            return True

    def is_deregistered(self, runner_id: str) -> bool:
        """Check if runner has been marked for deregistration."""
        with self._lock:
            return runner_id in self._deregistered

    def confirm_deregistered(self, runner_id: str) -> bool:
        """Confirm deregistration and remove runner and its agents from registry.

        Called after runner has been notified of deregistration.
        Returns True if runner was removed, False if not found.
        """
        with self._lock:
            self._deregistered.discard(runner_id)
            if runner_id in self._runners:
                del self._runners[runner_id]
                self._remove_runner_agents_unlocked(runner_id)
                return True
            return False

    def update_lifecycle(
        self,
        stale_threshold_seconds: float = 120.0,
        remove_threshold_seconds: float = 600.0,
    ) -> tuple[list[str], list[str]]:
        """Update runner lifecycle states based on heartbeat age.

        Runners that haven't sent a heartbeat:
        - For stale_threshold+ seconds: marked as stale
        - For remove_threshold+ seconds: removed from registry

        Args:
            stale_threshold_seconds: Seconds without heartbeat before marking stale
            remove_threshold_seconds: Seconds without heartbeat before removal

        Returns:
            Tuple of (stale_runner_ids, removed_runner_ids)
        """
        now = datetime.now(timezone.utc)
        stale_ids: list[str] = []
        remove_ids: list[str] = []

        with self._lock:
            for runner_id, runner in list(self._runners.items()):
                last_hb = datetime.fromisoformat(
                    runner.last_heartbeat.replace('Z', '+00:00')
                )
                age_seconds = (now - last_hb).total_seconds()

                if age_seconds >= remove_threshold_seconds:
                    remove_ids.append(runner_id)
                elif age_seconds >= stale_threshold_seconds:
                    if runner.status != RunnerStatus.STALE:
                        runner.status = RunnerStatus.STALE
                        stale_ids.append(runner_id)

            # Remove old runners and their agents
            for runner_id in remove_ids:
                del self._runners[runner_id]
                self._remove_runner_agents_unlocked(runner_id)
                self._deregistered.discard(runner_id)

        return stale_ids, remove_ids

    # =========================================================================
    # Runner Agents (in-memory storage)
    # =========================================================================

    def store_runner_agents(self, runner_id: str, agents: list[dict]) -> None:
        """Store agents registered by a runner.

        Replaces any existing agents for this runner.

        Args:
            runner_id: The runner that owns these agents
            agents: List of agent dicts with name, description, command, parameters_schema
        """
        with self._lock:
            self._runner_agents[runner_id] = agents

    def get_runner_agents(self, runner_id: str) -> list[dict]:
        """Get all agents registered by a runner.

        Args:
            runner_id: The runner ID to query

        Returns:
            List of agent dicts (empty list if runner has no agents)
        """
        with self._lock:
            return list(self._runner_agents.get(runner_id, []))

    def delete_runner_agents(self, runner_id: str) -> int:
        """Delete all agents registered by a runner.

        Args:
            runner_id: The runner ID

        Returns:
            Number of agents deleted
        """
        with self._lock:
            return self._remove_runner_agents_unlocked(runner_id)

    def get_runner_agent_by_name(self, name: str) -> tuple[dict, str] | None:
        """Get a runner-owned agent by name.

        If multiple runners have an agent with the same name, returns the first one found.

        Args:
            name: The agent name to look up

        Returns:
            Tuple of (agent_dict, runner_id) or None if not found
        """
        with self._lock:
            for runner_id, agents in self._runner_agents.items():
                for agent in agents:
                    if agent.get("name") == name:
                        return (agent, runner_id)
            return None

    def get_all_runner_agents(self) -> list[dict]:
        """Get all runner-owned agents.

        Returns:
            List of agent dicts with runner_id included
        """
        with self._lock:
            result = []
            for runner_id, agents in self._runner_agents.items():
                for agent in agents:
                    # Include runner_id in each agent dict
                    agent_with_runner = {**agent, "runner_id": runner_id}
                    result.append(agent_with_runner)
            return result


# Module-level singleton
runner_registry = RunnerRegistry()
