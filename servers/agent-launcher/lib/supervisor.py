"""
Supervisor Thread - monitors running subprocesses for completion.

Checks subprocess status periodically and reports completion/failure.
Also handles callback integration: when a child session completes,
automatically resumes the parent session with the child's result.
"""

import threading
import time
import logging
from typing import Optional

from api_client import RuntimeAPIClient
from registry import RunningJobsRegistry

logger = logging.getLogger(__name__)

# Template for callback resume prompt
CALLBACK_PROMPT_TEMPLATE = """The child agent session "{child_session}" has completed.

## Child Result

{child_result}

Please continue with the orchestration based on this result."""


class JobSupervisor:
    """Background thread that monitors running jobs for completion."""

    def __init__(
        self,
        api_client: RuntimeAPIClient,
        registry: RunningJobsRegistry,
        launcher_id: str,
        check_interval: float = 1.0,
    ):
        """Initialize the supervisor.

        Args:
            api_client: HTTP client for Agent Runtime
            registry: Registry of running jobs
            launcher_id: This launcher's ID
            check_interval: How often to check subprocess status (seconds)
        """
        self.api_client = api_client
        self.registry = registry
        self.launcher_id = launcher_id
        self.check_interval = check_interval

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the supervisor thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Supervisor already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._supervision_loop, daemon=True)
        self._thread.start()
        logger.info("Supervisor started")

    def stop(self) -> None:
        """Stop the supervisor thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Supervisor stopped")

    def _supervision_loop(self) -> None:
        """Main supervision loop."""
        while not self._stop_event.is_set():
            try:
                self._check_jobs()
            except Exception as e:
                logger.error(f"Supervision error: {e}")

            time.sleep(self.check_interval)

    def _check_jobs(self) -> None:
        """Check all running jobs for completion."""
        jobs = self.registry.get_all_jobs()

        for job_id, running_job in jobs.items():
            # Check if process has finished
            return_code = running_job.process.poll()

            if return_code is not None:
                # Process has finished
                self._handle_completion(job_id, running_job, return_code)

    def _handle_completion(self, job_id: str, running_job, return_code: int) -> None:
        """Handle job completion (success or failure).

        If the completed session has a parent_session_name, triggers a callback
        by creating a resume job for the parent with the child's result.
        """
        # Remove from registry first
        self.registry.remove_job(job_id)

        # Get any output
        stdout, stderr = "", ""
        try:
            stdout, stderr = running_job.process.communicate(timeout=1.0)
        except Exception:
            pass

        if return_code == 0:
            logger.info(f"Job {job_id} completed successfully (session={running_job.session_name})")
            try:
                self.api_client.report_completed(self.launcher_id, job_id)
            except Exception as e:
                logger.error(f"Failed to report completion for {job_id}: {e}")

            # Check for callback - trigger parent resume if child has parent_session_name
            self._trigger_callback_if_needed(running_job.session_name)
        else:
            error_msg = stderr.strip() if stderr else f"Process exited with code {return_code}"
            logger.error(f"Job {job_id} failed: {error_msg}")
            try:
                self.api_client.report_failed(self.launcher_id, job_id, error_msg)
            except Exception as e:
                logger.error(f"Failed to report failure for {job_id}: {e}")

            # Even on failure, trigger callback so parent knows child failed
            self._trigger_callback_if_needed(running_job.session_name, failed=True, error=error_msg)

    def _trigger_callback_if_needed(
        self,
        child_session_name: str,
        failed: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """Check if child session has a parent and trigger callback resume.

        Args:
            child_session_name: The session name of the completed child
            failed: Whether the child failed
            error: Error message if failed
        """
        try:
            # Look up the child session to get parent info
            child_session = self.api_client.get_session_by_name(child_session_name)
            if not child_session:
                logger.debug(f"No session found for {child_session_name}")
                return

            parent_session_name = child_session.get("parent_session_name")
            if not parent_session_name:
                logger.debug(f"Session {child_session_name} has no parent")
                return

            # Prevent self-loop: don't trigger callback if parent is the same session
            if parent_session_name == child_session_name:
                logger.warning(f"Skipping callback: session {child_session_name} is its own parent (self-loop prevention)")
                return

            # Fetch parent session info (needed for cycle detection and project_dir)
            parent_session = self.api_client.get_session_by_name(parent_session_name)

            # Prevent indirect loops: check if parent also has the child as its ancestor
            # This detects cycles like A -> B -> A
            if parent_session:
                grandparent = parent_session.get("parent_session_name")
                if grandparent == child_session_name:
                    logger.warning(f"Skipping callback: detected cycle {child_session_name} -> {parent_session_name} -> {child_session_name}")
                    return

            logger.info(f"Triggering callback: {child_session_name} -> {parent_session_name}")

            # Get the child's result (or error message)
            if failed:
                child_result = f"Error: Child session failed.\n\n{error or 'Unknown error'}"
            else:
                child_result = self.api_client.get_session_result(child_session_name)
                if not child_result:
                    child_result = "(No result available)"

            # Build callback resume prompt
            prompt = CALLBACK_PROMPT_TEMPLATE.format(
                child_session=child_session_name,
                child_result=child_result,
            )

            # Get parent's project_dir for the resume job
            project_dir = parent_session.get("project_dir") if parent_session else None

            # Create resume job for parent
            job_id = self.api_client.create_resume_job(
                session_name=parent_session_name,
                prompt=prompt,
                project_dir=project_dir,
            )

            if job_id:
                logger.info(f"Created callback resume job {job_id} for parent {parent_session_name}")
            else:
                logger.error(f"Failed to create callback job for parent {parent_session_name}")

        except Exception as e:
            logger.error(f"Error triggering callback for {child_session_name}: {e}")
