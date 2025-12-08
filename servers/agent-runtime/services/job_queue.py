"""
Thread-safe in-memory job queue for Agent Launcher.

Jobs are created via POST /jobs and claimed by the Launcher via GET /launcher/jobs.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from pydantic import BaseModel


class JobType(str, Enum):
    START_SESSION = "start_session"
    RESUME_SESSION = "resume_session"


class JobStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreate(BaseModel):
    """Request body for creating a new job."""
    type: JobType
    session_name: str
    agent_name: Optional[str] = None
    prompt: str
    project_dir: Optional[str] = None
    parent_session_name: Optional[str] = None


class Job(BaseModel):
    """Full job representation."""
    job_id: str
    type: JobType
    session_name: str
    agent_name: Optional[str] = None
    prompt: str
    project_dir: Optional[str] = None
    parent_session_name: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    launcher_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    claimed_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class JobQueue:
    """Thread-safe in-memory job queue."""

    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def add_job(self, job_create: JobCreate) -> Job:
        """Create a new job with pending status."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        job = Job(
            job_id=job_id,
            type=job_create.type,
            session_name=job_create.session_name,
            agent_name=job_create.agent_name,
            prompt=job_create.prompt,
            project_dir=job_create.project_dir,
            parent_session_name=job_create.parent_session_name,
            status=JobStatus.PENDING,
            created_at=now,
        )

        with self._lock:
            self._jobs[job_id] = job

        return job

    def claim_job(self, launcher_id: str) -> Optional[Job]:
        """Atomically claim a pending job for a launcher.

        Returns the claimed job or None if no pending jobs.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            # Find first pending job
            for job in self._jobs.values():
                if job.status == JobStatus.PENDING:
                    # Claim it
                    job.status = JobStatus.CLAIMED
                    job.launcher_id = launcher_id
                    job.claimed_at = now
                    return job

        return None

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job status and optionally set error message.

        Returns updated job or None if job not found.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            job.status = status

            if status == JobStatus.RUNNING:
                job.started_at = now
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                job.completed_at = now
                if error:
                    job.error = error

            return job

    def get_pending_jobs(self) -> list[Job]:
        """Get all pending jobs (for debugging)."""
        with self._lock:
            return [j for j in self._jobs.values() if j.status == JobStatus.PENDING]

    def get_all_jobs(self) -> list[Job]:
        """Get all jobs (for debugging)."""
        with self._lock:
            return list(self._jobs.values())

    def get_job_by_session_name(self, session_name: str) -> Optional[Job]:
        """Find a running or claimed job by session_name.

        Used to link job's parent_session_name to newly created sessions.
        """
        with self._lock:
            for job in self._jobs.values():
                if job.session_name == session_name and job.status in (JobStatus.CLAIMED, JobStatus.RUNNING):
                    return job
        return None


# Module-level singleton
job_queue = JobQueue()
