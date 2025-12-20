"""
Callback Processor - queues and delivers child completion notifications.

When a child session completes, this processor checks if the parent is idle.
If idle, it creates a resume run immediately. If busy, it queues the notification
for delivery when the parent becomes idle.

This solves the "lost callback" problem where callbacks were dropped when
the parent was executing a blocking operation.

Additionally, a "resume in-flight" lock prevents multiple concurrent callbacks
from creating duplicate resume runs. When a resume run is created, the parent
is marked as "in-flight". Subsequent callbacks are queued until the parent
session stops (meaning the resume was processed).

Note: Uses session_id (coordinator-generated) per ADR-010.
"""

import threading
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# In-memory queue: parent_session_id -> [(child_id, result, failed, error), ...]
# Thread-safe access via lock
_pending_notifications: Dict[str, List[tuple]] = {}

# Track parents with pending resume runs (not yet processed)
# Prevents duplicate resume runs when multiple callbacks arrive simultaneously
_resume_in_flight: Set[str] = set()

_lock = threading.Lock()


# Callback resume prompt templates
CALLBACK_PROMPT_TEMPLATE = """The child agent session "{child_session_id}" has completed.

## Child Result

{child_result}

Please continue with the orchestration based on this result."""

CALLBACK_FAILED_PROMPT_TEMPLATE = """The child agent session "{child_session_id}" has failed.

## Error

{child_error}

Please handle this failure and continue with the orchestration."""

AGGREGATED_CALLBACK_PROMPT_TEMPLATE = """Multiple child agent sessions have completed.

{children_results}

Please continue with the orchestration based on these results."""


def on_child_completed(
    child_session_id: str,
    parent_session_id: str,
    parent_status: str,
    child_result: Optional[str] = None,
    child_failed: bool = False,
    child_error: Optional[str] = None,
) -> bool:
    """Handle child session completion.

    Args:
        child_session_id: ID of the completed child session
        parent_session_id: ID of the parent session to callback
        parent_status: Current status of parent ("running", "finished", etc.)
        child_result: Result text from the child session
        child_failed: Whether the child failed
        child_error: Error message if child failed

    Returns:
        True if callback was delivered immediately, False if queued
    """
    # Prevent self-loop
    if child_session_id == parent_session_id:
        logger.warning(f"Skipping callback: session {child_session_id} is its own parent")
        return False

    callback_data = (child_session_id, child_result, child_failed, child_error)
    should_create_run = False

    with _lock:
        # Check if a resume run is already pending for this parent
        if parent_session_id in _resume_in_flight:
            # Resume already in progress - queue this callback
            logger.info(f"Parent '{parent_session_id}' has resume in-flight, queuing callback from '{child_session_id}'")
            _pending_notifications.setdefault(parent_session_id, []).append(callback_data)
            return False

        if parent_status == "finished":
            # Parent is idle and no resume in-flight - deliver immediately
            # Mark as in-flight to prevent duplicate resume runs
            _resume_in_flight.add(parent_session_id)
            should_create_run = True
            logger.info(f"Parent '{parent_session_id}' is idle, delivering callback from '{child_session_id}' (marked in-flight)")
        else:
            # Parent is busy - queue for later
            logger.info(f"Parent '{parent_session_id}' is busy (status={parent_status}), queuing callback from '{child_session_id}'")
            _pending_notifications.setdefault(parent_session_id, []).append(callback_data)
            return False

    # Create run outside lock to avoid holding lock during I/O
    if should_create_run:
        _create_resume_run(parent_session_id, [callback_data])
        return True

    return False


def on_session_stopped(session_id: str, project_dir: Optional[str] = None) -> int:
    """Handle any session stopping - check for pending callbacks.

    Called when ANY session stops. If this session has pending child
    notifications queued, flush them now.

    This also clears the "in-flight" flag since the resume has been processed.
    If there are pending callbacks, a new resume run is created and the
    in-flight flag is set again.

    Args:
        session_id: ID of the session that just stopped
        project_dir: Project directory of the session (for resume run)

    Returns:
        Number of pending callbacks that were flushed
    """
    pending = None
    should_create_run = False

    with _lock:
        # Clear in-flight flag - the resume (if any) has been processed
        was_in_flight = session_id in _resume_in_flight
        _resume_in_flight.discard(session_id)

        if was_in_flight:
            logger.debug(f"Cleared in-flight flag for '{session_id}'")

        # Check for pending callbacks
        if session_id not in _pending_notifications:
            return 0

        pending = _pending_notifications.pop(session_id)

        if pending:
            # Set in-flight again for the new resume run
            _resume_in_flight.add(session_id)
            should_create_run = True
            logger.info(f"Session '{session_id}' stopped with {len(pending)} pending callbacks, flushing (marked in-flight)")

    # Create run outside lock
    if should_create_run and pending:
        _create_resume_run(session_id, pending, project_dir)
        return len(pending)

    return 0


def _queue_notification(
    parent_session_id: str,
    child_session_id: str,
    child_result: Optional[str],
    child_failed: bool,
    child_error: Optional[str],
) -> None:
    """Queue a callback notification for later delivery."""
    with _lock:
        if parent_session_id not in _pending_notifications:
            _pending_notifications[parent_session_id] = []

        _pending_notifications[parent_session_id].append(
            (child_session_id, child_result, child_failed, child_error)
        )

    logger.debug(f"Queued callback: {child_session_id} -> {parent_session_id}")


def _create_resume_run(
    parent_session_id: str,
    children: List[tuple],  # [(child_id, result, failed, error), ...]
    project_dir: Optional[str] = None,
) -> Optional[str]:
    """Create a resume run for the parent with child results.

    Args:
        parent_session_id: Session ID to resume
        children: List of (child_id, result, failed, error) tuples
        project_dir: Project directory for the resume run

    Returns:
        Run ID if created successfully, None on error
    """
    from services.run_queue import run_queue, RunCreate, RunType

    # Build the callback prompt
    if len(children) == 1:
        child_id, result, failed, error = children[0]
        if failed:
            prompt = CALLBACK_FAILED_PROMPT_TEMPLATE.format(
                child_session_id=child_id,
                child_error=error or "Unknown error",
            )
        else:
            prompt = CALLBACK_PROMPT_TEMPLATE.format(
                child_session_id=child_id,
                child_result=result or "(No result available)",
            )
    else:
        # Multiple children - aggregate results
        results_parts = []
        for child_id, result, failed, error in children:
            if failed:
                status = "FAILED"
                child_result = error or "Unknown error"
            else:
                status = "completed"
                child_result = result or "(No result available)"

            results_parts.append(f"### Child: {child_id} ({status})\n\n{child_result}")

        prompt = AGGREGATED_CALLBACK_PROMPT_TEMPLATE.format(
            children_results="\n\n---\n\n".join(results_parts)
        )

    try:
        run = run_queue.add_run(RunCreate(
            type=RunType.RESUME_SESSION,
            session_id=parent_session_id,
            prompt=prompt,
            project_dir=project_dir,
        ))
        logger.info(f"Created callback resume run {run.run_id} for parent '{parent_session_id}' with {len(children)} child result(s)")
        return run.run_id
    except Exception as e:
        logger.error(f"Failed to create callback run for '{parent_session_id}': {e}")
        return None


def get_pending_count(parent_session_id: str) -> int:
    """Get the number of pending callbacks for a parent session.

    Useful for debugging and monitoring.
    """
    with _lock:
        return len(_pending_notifications.get(parent_session_id, []))


def get_all_pending() -> Dict[str, int]:
    """Get count of pending callbacks for all parents.

    Useful for debugging and monitoring.
    """
    with _lock:
        return {k: len(v) for k, v in _pending_notifications.items()}


def clear_pending(parent_session_id: str) -> int:
    """Clear pending callbacks for a parent (e.g., if parent is deleted).

    Also clears the in-flight flag if set.

    Returns the number of callbacks that were cleared.
    """
    with _lock:
        # Clear in-flight flag
        _resume_in_flight.discard(parent_session_id)

        if parent_session_id in _pending_notifications:
            count = len(_pending_notifications[parent_session_id])
            del _pending_notifications[parent_session_id]
            logger.info(f"Cleared {count} pending callbacks for deleted parent '{parent_session_id}'")
            return count
    return 0


def is_resume_in_flight(parent_session_id: str) -> bool:
    """Check if a resume run is pending for the given parent.

    Useful for debugging and monitoring.
    """
    with _lock:
        return parent_session_id in _resume_in_flight


def get_all_in_flight() -> Set[str]:
    """Get all parents with resume runs in-flight.

    Useful for debugging and monitoring.
    """
    with _lock:
        return _resume_in_flight.copy()
