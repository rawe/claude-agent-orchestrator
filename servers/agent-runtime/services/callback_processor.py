"""
Callback Processor - queues and delivers child completion notifications.

When a child session completes, this processor checks if the parent is idle.
If idle, it creates a resume job immediately. If busy, it queues the notification
for delivery when the parent becomes idle.

This solves the "lost callback" problem where callbacks were dropped when
the parent was executing a blocking operation.

Additionally, a "resume in-flight" lock prevents multiple concurrent callbacks
from creating duplicate resume jobs. When a resume job is created, the parent
is marked as "in-flight". Subsequent callbacks are queued until the parent
session stops (meaning the resume was processed).
"""

import threading
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# In-memory queue: parent_session_name -> [(child_name, result, failed, error), ...]
# Thread-safe access via lock
_pending_notifications: Dict[str, List[tuple]] = {}

# Track parents with pending resume jobs (not yet processed)
# Prevents duplicate resume jobs when multiple callbacks arrive simultaneously
_resume_in_flight: Set[str] = set()

_lock = threading.Lock()


# Callback resume prompt template
CALLBACK_PROMPT_TEMPLATE = """The child agent session "{child_session}" has completed.

## Child Result

{child_result}

Please continue with the orchestration based on this result."""

AGGREGATED_CALLBACK_PROMPT_TEMPLATE = """Multiple child agent sessions have completed.

{children_results}

Please continue with the orchestration based on these results."""


def on_child_completed(
    child_session_name: str,
    parent_session_name: str,
    parent_status: str,
    child_result: Optional[str] = None,
    child_failed: bool = False,
    child_error: Optional[str] = None,
) -> bool:
    """Handle child session completion.

    Args:
        child_session_name: Name of the completed child session
        parent_session_name: Name of the parent session to callback
        parent_status: Current status of parent ("running", "finished", etc.)
        child_result: Result text from the child session
        child_failed: Whether the child failed
        child_error: Error message if child failed

    Returns:
        True if callback was delivered immediately, False if queued
    """
    # Prevent self-loop
    if child_session_name == parent_session_name:
        logger.warning(f"Skipping callback: session {child_session_name} is its own parent")
        return False

    callback_data = (child_session_name, child_result, child_failed, child_error)
    should_create_job = False

    with _lock:
        # Check if a resume job is already pending for this parent
        if parent_session_name in _resume_in_flight:
            # Resume already in progress - queue this callback
            logger.info(f"Parent '{parent_session_name}' has resume in-flight, queuing callback from '{child_session_name}'")
            _pending_notifications.setdefault(parent_session_name, []).append(callback_data)
            return False

        if parent_status == "finished":
            # Parent is idle and no resume in-flight - deliver immediately
            # Mark as in-flight to prevent duplicate resume jobs
            _resume_in_flight.add(parent_session_name)
            should_create_job = True
            logger.info(f"Parent '{parent_session_name}' is idle, delivering callback from '{child_session_name}' (marked in-flight)")
        else:
            # Parent is busy - queue for later
            logger.info(f"Parent '{parent_session_name}' is busy (status={parent_status}), queuing callback from '{child_session_name}'")
            _pending_notifications.setdefault(parent_session_name, []).append(callback_data)
            return False

    # Create job outside lock to avoid holding lock during I/O
    if should_create_job:
        _create_resume_job(parent_session_name, [callback_data])
        return True

    return False


def on_session_stopped(session_name: str, project_dir: Optional[str] = None) -> int:
    """Handle any session stopping - check for pending callbacks.

    Called when ANY session stops. If this session has pending child
    notifications queued, flush them now.

    This also clears the "in-flight" flag since the resume has been processed.
    If there are pending callbacks, a new resume job is created and the
    in-flight flag is set again.

    Args:
        session_name: Name of the session that just stopped
        project_dir: Project directory of the session (for resume job)

    Returns:
        Number of pending callbacks that were flushed
    """
    pending = None
    should_create_job = False

    with _lock:
        # Clear in-flight flag - the resume (if any) has been processed
        was_in_flight = session_name in _resume_in_flight
        _resume_in_flight.discard(session_name)

        if was_in_flight:
            logger.debug(f"Cleared in-flight flag for '{session_name}'")

        # Check for pending callbacks
        if session_name not in _pending_notifications:
            return 0

        pending = _pending_notifications.pop(session_name)

        if pending:
            # Set in-flight again for the new resume job
            _resume_in_flight.add(session_name)
            should_create_job = True
            logger.info(f"Session '{session_name}' stopped with {len(pending)} pending callbacks, flushing (marked in-flight)")

    # Create job outside lock
    if should_create_job and pending:
        _create_resume_job(session_name, pending, project_dir)
        return len(pending)

    return 0


def _queue_notification(
    parent_session_name: str,
    child_session_name: str,
    child_result: Optional[str],
    child_failed: bool,
    child_error: Optional[str],
) -> None:
    """Queue a callback notification for later delivery."""
    with _lock:
        if parent_session_name not in _pending_notifications:
            _pending_notifications[parent_session_name] = []

        _pending_notifications[parent_session_name].append(
            (child_session_name, child_result, child_failed, child_error)
        )

    logger.debug(f"Queued callback: {child_session_name} -> {parent_session_name}")


def _create_resume_job(
    parent_session_name: str,
    children: List[tuple],  # [(child_name, result, failed, error), ...]
    project_dir: Optional[str] = None,
) -> Optional[str]:
    """Create a resume job for the parent with child results.

    Args:
        parent_session_name: Session to resume
        children: List of (child_name, result, failed, error) tuples
        project_dir: Project directory for the resume job

    Returns:
        Job ID if created successfully, None on error
    """
    from services.job_queue import job_queue, JobCreate, JobType

    # Build the callback prompt
    if len(children) == 1:
        child_name, result, failed, error = children[0]
        if failed:
            child_result = f"Error: Child session failed.\n\n{error or 'Unknown error'}"
        else:
            child_result = result or "(No result available)"

        prompt = CALLBACK_PROMPT_TEMPLATE.format(
            child_session=child_name,
            child_result=child_result,
        )
    else:
        # Multiple children - aggregate results
        results_parts = []
        for child_name, result, failed, error in children:
            if failed:
                child_result = f"Error: {error or 'Unknown error'}"
            else:
                child_result = result or "(No result available)"

            results_parts.append(f"### Child: {child_name}\n\n{child_result}")

        prompt = AGGREGATED_CALLBACK_PROMPT_TEMPLATE.format(
            children_results="\n\n---\n\n".join(results_parts)
        )

    try:
        job = job_queue.add_job(JobCreate(
            type=JobType.RESUME_SESSION,
            session_name=parent_session_name,
            prompt=prompt,
            project_dir=project_dir,
        ))
        logger.info(f"Created callback resume job {job.job_id} for parent '{parent_session_name}' with {len(children)} child result(s)")
        return job.job_id
    except Exception as e:
        logger.error(f"Failed to create callback job for '{parent_session_name}': {e}")
        return None


def get_pending_count(parent_session_name: str) -> int:
    """Get the number of pending callbacks for a parent session.

    Useful for debugging and monitoring.
    """
    with _lock:
        return len(_pending_notifications.get(parent_session_name, []))


def get_all_pending() -> Dict[str, int]:
    """Get count of pending callbacks for all parents.

    Useful for debugging and monitoring.
    """
    with _lock:
        return {k: len(v) for k, v in _pending_notifications.items()}


def clear_pending(parent_session_name: str) -> int:
    """Clear pending callbacks for a parent (e.g., if parent is deleted).

    Also clears the in-flight flag if set.

    Returns the number of callbacks that were cleared.
    """
    with _lock:
        # Clear in-flight flag
        _resume_in_flight.discard(parent_session_name)

        if parent_session_name in _pending_notifications:
            count = len(_pending_notifications[parent_session_name])
            del _pending_notifications[parent_session_name]
            logger.info(f"Cleared {count} pending callbacks for deleted parent '{parent_session_name}'")
            return count
    return 0


def is_resume_in_flight(parent_session_name: str) -> bool:
    """Check if a resume job is pending for the given parent.

    Useful for debugging and monitoring.
    """
    with _lock:
        return parent_session_name in _resume_in_flight


def get_all_in_flight() -> Set[str]:
    """Get all parents with resume jobs in-flight.

    Useful for debugging and monitoring.
    """
    with _lock:
        return _resume_in_flight.copy()
