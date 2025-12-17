"""
Thread-safe in-memory run queue for Agent Runner.

Runs are created via POST /runs and claimed by the Runner via GET /runner/runs.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from pydantic import BaseModel


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
    """Request body for creating a new run."""
    type: RunType
    session_name: str
    agent_name: Optional[str] = None
    prompt: str
    project_dir: Optional[str] = None
    parent_session_name: Optional[str] = None


class Run(BaseModel):
    """Full run representation."""
    run_id: str
    type: RunType
    session_name: str
    agent_name: Optional[str] = None
    prompt: str
    project_dir: Optional[str] = None
    parent_session_name: Optional[str] = None
    status: RunStatus = RunStatus.PENDING
    runner_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    claimed_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class RunQueue:
    """Thread-safe in-memory run queue."""

    def __init__(self):
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

    def add_run(self, run_create: RunCreate) -> Run:
        """Create a new run with pending status."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        run = Run(
            run_id=run_id,
            type=run_create.type,
            session_name=run_create.session_name,
            agent_name=run_create.agent_name,
            prompt=run_create.prompt,
            project_dir=run_create.project_dir,
            parent_session_name=run_create.parent_session_name,
            status=RunStatus.PENDING,
            created_at=now,
        )

        with self._lock:
            self._runs[run_id] = run

        return run

    def claim_run(self, runner_id: str) -> Optional[Run]:
        """Atomically claim a pending run for a runner.

        Returns the claimed run or None if no pending runs.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            # Find first pending run
            for run in self._runs.values():
                if run.status == RunStatus.PENDING:
                    # Claim it
                    run.status = RunStatus.CLAIMED
                    run.runner_id = runner_id
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

    def get_run_by_session_name(self, session_name: str) -> Optional[Run]:
        """Find an active run by session_name.

        Used to link run's parent_session_name to newly created sessions,
        and to find runs for stop commands.
        """
        with self._lock:
            for run in self._runs.values():
                if run.session_name == session_name and run.status in (
                    RunStatus.CLAIMED, RunStatus.RUNNING, RunStatus.STOPPING
                ):
                    return run
        return None


# Module-level singleton
run_queue = RunQueue()
