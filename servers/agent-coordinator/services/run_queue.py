"""
Thread-safe in-memory run queue for Agent Runner.

Runs are created via POST /runs and claimed by the Runner via GET /runner/runs.
Supports demand-based matching per ADR-011.
Session ID is coordinator-generated at run creation per ADR-010.
Execution mode controls callback behavior per ADR-003.
"""

import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel

if TYPE_CHECKING:
    from models import RunnerDemands, ExecutionMode as ExecutionModeType
    from services.runner_registry import RunnerInfo

# Import ExecutionMode for runtime use
from models import ExecutionMode


class RunType(str, Enum):
    START_SESSION = "start_session"
    RESUME_SESSION = "resume_session"


class RunStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    STOPPING = "stopping"  # Stop requested, waiting for runner
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"    # Successfully stopped


class RunCreate(BaseModel):
    """Request body for creating a new run.

    session_id is optional - coordinator generates it if not provided (ADR-010).
    execution_mode controls callback behavior per ADR-003.
    """
    type: RunType
    session_id: Optional[str] = None  # Coordinator generates if not provided
    agent_name: Optional[str] = None
    prompt: str
    project_dir: Optional[str] = None
    parent_session_id: Optional[str] = None
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    # Additional demands to merge with blueprint demands (additive only)
    additional_demands: Optional[dict] = None


class Run(BaseModel):
    """Full run representation."""
    run_id: str
    type: RunType
    session_id: str  # Coordinator-generated (ADR-010)
    agent_name: Optional[str] = None
    prompt: str
    project_dir: Optional[str] = None
    parent_session_id: Optional[str] = None
    execution_mode: ExecutionMode = ExecutionMode.SYNC  # ADR-003
    # Merged demands (blueprint + additional) - stored as dict for serialization
    demands: Optional[dict] = None
    status: RunStatus = RunStatus.PENDING
    runner_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    claimed_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    # Timeout for no-match scenarios (ISO timestamp)
    timeout_at: Optional[str] = None


def generate_session_id() -> str:
    """Generate a coordinator session_id per ADR-010.

    Format: ses_{12-char-hex}
    Example: ses_abc123def456
    """
    return f"ses_{uuid.uuid4().hex[:12]}"


# Default timeout for runs waiting for a matching runner (5 minutes)
DEFAULT_NO_MATCH_TIMEOUT_SECONDS = 300


# Demand field names (matching RunnerDemands model in models.py)
class DemandFields:
    """Field names for demands matching."""
    HOSTNAME = "hostname"
    PROJECT_DIR = "project_dir"
    EXECUTOR_TYPE = "executor_type"
    TAGS = "tags"


def capabilities_satisfy_demands(
    runner: "RunnerInfo",
    demands: Optional[dict],
) -> bool:
    """
    Check if runner capabilities satisfy run demands.

    All specified demands must be met (hard requirements).
    See ADR-011 for details.

    Args:
        runner: Runner info with properties and tags
        demands: Demands dict with hostname, project_dir, executor_type, tags

    Returns:
        True if runner satisfies all demands, False otherwise
    """
    if demands is None:
        # No demands = any runner can claim
        return True

    # Property demands (exact match required)
    demanded_hostname = demands.get(DemandFields.HOSTNAME)
    if demanded_hostname and runner.hostname != demanded_hostname:
        return False

    demanded_project_dir = demands.get(DemandFields.PROJECT_DIR)
    if demanded_project_dir and runner.project_dir != demanded_project_dir:
        return False

    demanded_executor_type = demands.get(DemandFields.EXECUTOR_TYPE)
    if demanded_executor_type and runner.executor_type != demanded_executor_type:
        return False

    # Tag demands - runner must have ALL demanded tags
    demanded_tags = demands.get(DemandFields.TAGS, [])
    if demanded_tags:
        runner_tags = set(runner.tags or [])
        if not set(demanded_tags).issubset(runner_tags):
            return False

    return True


class RunQueue:
    """Thread-safe in-memory run queue."""

    def __init__(self):
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

    def add_run(self, run_create: RunCreate) -> Run:
        """Create a new run with pending status.

        If session_id is not provided, generates one per ADR-010.
        For resume runs, enriches with agent_name/project_dir from existing session.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Generate session_id if not provided (ADR-010)
        session_id = run_create.session_id or generate_session_id()

        # For resume runs, enrich from existing session so Runner has complete info
        if run_create.type == RunType.RESUME_SESSION and run_create.session_id:
            from database import get_session_by_id
            session = get_session_by_id(run_create.session_id)
            if session:
                # Copy agent_name if not provided in request
                if not run_create.agent_name and session.get("agent_name"):
                    run_create.agent_name = session["agent_name"]
                # Copy project_dir if not provided in request
                if not run_create.project_dir and session.get("project_dir"):
                    run_create.project_dir = session["project_dir"]

        run = Run(
            run_id=run_id,
            type=run_create.type,
            session_id=session_id,
            agent_name=run_create.agent_name,
            prompt=run_create.prompt,
            project_dir=run_create.project_dir,
            parent_session_id=run_create.parent_session_id,
            execution_mode=run_create.execution_mode,
            status=RunStatus.PENDING,
            created_at=now,
        )

        with self._lock:
            self._runs[run_id] = run

        return run

    def claim_run(self, runner: "RunnerInfo") -> Optional[Run]:
        """Atomically claim a pending run for a runner.

        Only runs whose demands are satisfied by the runner's capabilities
        can be claimed. See ADR-011 for matching logic.

        Args:
            runner: The runner attempting to claim a run

        Returns:
            The claimed run or None if no matching pending runs.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            # Find first pending run that matches runner capabilities
            for run in self._runs.values():
                if run.status == RunStatus.PENDING:
                    # Check if runner satisfies run demands
                    if capabilities_satisfy_demands(runner, run.demands):
                        # Claim it
                        run.status = RunStatus.CLAIMED
                        run.runner_id = runner.runner_id
                        run.claimed_at = now
                        return run

        return None

    def get_run(self, run_id: str) -> Optional[Run]:
        """Get run by ID."""
        with self._lock:
            return self._runs.get(run_id)

    def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        error: Optional[str] = None,
    ) -> Optional[Run]:
        """Update run status and optionally set error message.

        Returns updated run or None if run not found.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return None

            run.status = status

            if status == RunStatus.RUNNING:
                run.started_at = now
            elif status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.STOPPED):
                run.completed_at = now
                if error:
                    run.error = error

            return run

    def get_pending_runs(self) -> list[Run]:
        """Get all pending runs (for debugging)."""
        with self._lock:
            return [r for r in self._runs.values() if r.status == RunStatus.PENDING]

    def get_all_runs(self) -> list[Run]:
        """Get all runs (for debugging)."""
        with self._lock:
            return list(self._runs.values())

    def get_run_by_session_id(self, session_id: str) -> Optional[Run]:
        """Find an active run by session_id.

        Used to link run's parent_session_id to newly created sessions,
        and to find runs for stop commands.
        """
        with self._lock:
            for run in self._runs.values():
                if run.session_id == session_id and run.status in (
                    RunStatus.PENDING, RunStatus.CLAIMED, RunStatus.RUNNING, RunStatus.STOPPING
                ):
                    return run
        return None

    def fail_timed_out_runs(self) -> list[Run]:
        """Fail pending runs that have exceeded their timeout.

        Returns list of runs that were failed due to timeout.
        """
        now = datetime.now(timezone.utc)
        failed_runs: list[Run] = []

        with self._lock:
            for run in self._runs.values():
                if run.status == RunStatus.PENDING and run.timeout_at:
                    timeout_time = datetime.fromisoformat(
                        run.timeout_at.replace('Z', '+00:00')
                    )
                    if now >= timeout_time:
                        run.status = RunStatus.FAILED
                        run.completed_at = now.isoformat()
                        run.error = "No matching runner available within timeout"
                        failed_runs.append(run)

        return failed_runs

    def set_run_demands(
        self,
        run_id: str,
        demands: Optional[dict],
        timeout_seconds: int = DEFAULT_NO_MATCH_TIMEOUT_SECONDS,
    ) -> Optional[Run]:
        """Set demands and timeout on a run after creation.

        This is called by main.py after merging blueprint and additional demands.

        Args:
            run_id: The run to update
            demands: Merged demands dict
            timeout_seconds: Seconds until run fails if not claimed

        Returns:
            Updated run or None if not found
        """
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return None

            run.demands = demands
            # Only set timeout if there are demands (otherwise any runner can claim)
            if demands and not all(v is None or v == [] for v in demands.values()):
                timeout_at = datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)
                run.timeout_at = timeout_at.isoformat()

            return run


# Module-level singleton
run_queue = RunQueue()
