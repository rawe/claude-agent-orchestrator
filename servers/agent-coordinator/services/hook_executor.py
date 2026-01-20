"""
Hook Executor Service - Executes agent run hooks.

Agent run hooks are lifecycle hooks that execute around agent runs:
- on_run_start: Executes synchronously when a runner claims a run; can transform parameters or block execution
- on_run_finish: Executes fire-and-forget when a run completes; observation-only

Hook agents receive structured input and are expected to produce structured output.

See docs/design/agent-run-hooks.md for full specification.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel

from models import (
    HookConfig, HookAgentConfig, HookOnError, AgentHooks,
    Event, StreamEventType, SessionEventType,
)
from database import (
    create_session, get_session_by_id, get_session_result, insert_event,
)

# Debug logging toggle - matches main.py
DEBUG = os.getenv("DEBUG_LOGGING", "").lower() in ("true", "1", "yes")


# ==============================================================================
# Hook Result Types
# ==============================================================================

class HookAction(str, Enum):
    """Action determined by a hook execution."""
    CONTINUE = "continue"  # Continue with the run (possibly with transformed parameters)
    BLOCK = "block"        # Block the run from executing


class HookResult(BaseModel):
    """Result of a hook execution."""
    success: bool                         # Whether hook executed successfully
    action: Optional[HookAction] = None   # Action to take (continue/block)
    parameters: Optional[dict] = None     # Transformed parameters (for on_run_start)
    block_reason: Optional[str] = None    # Reason for blocking (if action=block)
    error: Optional[str] = None           # Error message if hook failed
    duration_ms: int = 0                  # Execution time in milliseconds


# ==============================================================================
# Hook Session Event Types
# ==============================================================================

class HookEventType(str, Enum):
    """Event types specific to hook execution."""
    HOOK_START = "hook_start"      # Hook execution started
    HOOK_COMPLETE = "hook_complete"  # Hook completed successfully
    HOOK_FAILED = "hook_failed"    # Hook failed
    HOOK_BLOCKED = "hook_blocked"  # Hook explicitly blocked the run
    HOOK_TIMEOUT = "hook_timeout"  # Hook timed out


# ==============================================================================
# Hook Session Management
# ==============================================================================

def _generate_hook_session_id() -> str:
    """Generate a unique session ID for a hook execution."""
    return f"hook_{uuid.uuid4().hex[:12]}"


def _parse_on_run_start_output(result: Optional[dict]) -> tuple[HookAction, Optional[dict], Optional[str]]:
    """Parse on_run_start hook output.

    Expected output format:
    - {action: "continue"} - continue with original parameters
    - {action: "continue", parameters: {...}} - continue with transformed parameters
    - {action: "block", block_reason: "..."} - block the run

    Returns:
        Tuple of (action, transformed_parameters, block_reason)
    """
    if not result:
        # No result means continue with original parameters
        return HookAction.CONTINUE, None, None

    result_data = result.get("result_data")
    if not result_data:
        # No structured data - try parsing result_text as JSON
        result_text = result.get("result_text")
        if result_text:
            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                # Can't parse - assume continue
                return HookAction.CONTINUE, None, None
        else:
            return HookAction.CONTINUE, None, None

    action_str = result_data.get("action", "continue")
    action = HookAction.BLOCK if action_str == "block" else HookAction.CONTINUE

    parameters = result_data.get("parameters")
    block_reason = result_data.get("block_reason")

    return action, parameters, block_reason


# ==============================================================================
# Hook Execution Functions
# ==============================================================================

async def execute_on_run_start_hook(
    hook_config: HookAgentConfig,
    run: Any,  # Run model from run_queue
    agent_name: str,
    run_queue: Any,  # RunQueue instance
    sse_manager: Any,  # SSEManager instance
) -> HookResult:
    """
    Execute on_run_start hook synchronously.

    This function:
    1. Creates a new session for the hook agent
    2. Queues a run for the hook agent
    3. Polls for completion with timeout
    4. Parses output to determine action

    Args:
        hook_config: Hook configuration specifying the hook agent
        run: The main run that triggered the hook
        agent_name: Name of the main agent being run
        run_queue: RunQueue instance for creating/monitoring runs
        sse_manager: SSEManager for broadcasting events

    Returns:
        HookResult with success, action, and optional transformed parameters
    """
    from services.run_queue import RunCreate, RunType, RunStatus

    start_time = datetime.now(timezone.utc)
    hook_session_id = _generate_hook_session_id()

    # Emit hook_start event
    hook_start_event = Event(
        event_type=HookEventType.HOOK_START.value,
        session_id=run.session_id,
        timestamp=start_time.isoformat(),
        tool_name=f"hook:on_run_start:{hook_config.agent_name}",
        tool_input={
            "hook_session_id": hook_session_id,
            "hook_agent": hook_config.agent_name,
        },
    )
    insert_event(hook_start_event)
    await sse_manager.broadcast(
        StreamEventType.EVENT,
        {"data": hook_start_event.model_dump()},
        session_id=run.session_id,
    )

    if DEBUG:
        print(f"[DEBUG] Starting on_run_start hook for run {run.run_id} with agent {hook_config.agent_name}", flush=True)

    try:
        # Create session for hook agent
        now = datetime.now(timezone.utc).isoformat()
        create_session(
            session_id=hook_session_id,
            timestamp=now,
            status="pending",
            agent_name=hook_config.agent_name,
            parent_session_id=run.session_id,  # Link to main run's session
        )

        # Create and queue run for hook agent
        # Design decision: Pass only the raw parameters from the original run.
        # The hook agent receives exactly the same parameters the main agent would
        # receive, allowing it to validate/transform them without needing metadata.
        # Run context (session_id, run_id, agent_name) is intentionally not passed.
        hook_run_create = RunCreate(
            type=RunType.START_SESSION,
            session_id=hook_session_id,
            agent_name=hook_config.agent_name,
            parameters=run.parameters,  # Raw parameters only
            parent_session_id=run.session_id,
        )

        hook_run = run_queue.add_run(hook_run_create)

        if DEBUG:
            print(f"[DEBUG] Created hook run {hook_run.run_id} for session {hook_session_id}", flush=True)

        # Poll for completion with timeout
        timeout_seconds = hook_config.timeout_seconds
        poll_interval = 0.5
        elapsed = 0.0

        while elapsed < timeout_seconds:
            # Check hook run status
            current_run = run_queue.get_run(hook_run.run_id)
            if not current_run:
                raise Exception(f"Hook run {hook_run.run_id} disappeared")

            if current_run.status == RunStatus.COMPLETED:
                # Hook completed - get result
                result = get_session_result(hook_session_id)
                action, parameters, block_reason = _parse_on_run_start_output(result)

                duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

                if action == HookAction.BLOCK:
                    # Emit hook_blocked event
                    event = Event(
                        event_type=HookEventType.HOOK_BLOCKED.value,
                        session_id=run.session_id,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        tool_name=f"hook:on_run_start:{hook_config.agent_name}",
                        tool_output={"block_reason": block_reason},
                    )
                    insert_event(event)
                    await sse_manager.broadcast(StreamEventType.EVENT, {"data": event.model_dump()}, session_id=run.session_id)

                    if DEBUG:
                        print(f"[DEBUG] Hook blocked run: {block_reason}", flush=True)

                    return HookResult(
                        success=True,
                        action=HookAction.BLOCK,
                        block_reason=block_reason,
                        duration_ms=duration_ms,
                    )
                else:
                    # Emit hook_complete event
                    event = Event(
                        event_type=HookEventType.HOOK_COMPLETE.value,
                        session_id=run.session_id,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        tool_name=f"hook:on_run_start:{hook_config.agent_name}",
                        tool_output={"action": "continue", "parameters_transformed": parameters is not None},
                    )
                    insert_event(event)
                    await sse_manager.broadcast(StreamEventType.EVENT, {"data": event.model_dump()}, session_id=run.session_id)

                    if DEBUG:
                        params_info = "with transformed params" if parameters else "with original params"
                        print(f"[DEBUG] Hook completed: continue {params_info}", flush=True)

                    return HookResult(
                        success=True,
                        action=HookAction.CONTINUE,
                        parameters=parameters,
                        duration_ms=duration_ms,
                    )

            elif current_run.status == RunStatus.FAILED:
                # Hook failed
                error = current_run.error or "Hook agent failed"
                duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

                # Emit hook_failed event
                event = Event(
                    event_type=HookEventType.HOOK_FAILED.value,
                    session_id=run.session_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    tool_name=f"hook:on_run_start:{hook_config.agent_name}",
                    error=error,
                )
                insert_event(event)
                await sse_manager.broadcast(StreamEventType.EVENT, {"data": event.model_dump()}, session_id=run.session_id)

                if DEBUG:
                    print(f"[DEBUG] Hook failed: {error}", flush=True)

                # Apply on_error policy
                if hook_config.on_error == HookOnError.BLOCK:
                    return HookResult(
                        success=False,
                        action=HookAction.BLOCK,
                        error=error,
                        block_reason=f"Hook failed: {error}",
                        duration_ms=duration_ms,
                    )
                else:
                    # Continue despite failure
                    return HookResult(
                        success=False,
                        action=HookAction.CONTINUE,
                        error=error,
                        duration_ms=duration_ms,
                    )

            elif current_run.status == RunStatus.STOPPED:
                # Hook was stopped
                duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                error = "Hook was stopped"

                if hook_config.on_error == HookOnError.BLOCK:
                    return HookResult(
                        success=False,
                        action=HookAction.BLOCK,
                        error=error,
                        block_reason=error,
                        duration_ms=duration_ms,
                    )
                else:
                    return HookResult(
                        success=False,
                        action=HookAction.CONTINUE,
                        error=error,
                        duration_ms=duration_ms,
                    )

            # Still running - wait and poll again
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout reached
        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        error = f"Hook timed out after {timeout_seconds}s"

        # Emit hook_timeout event
        event = Event(
            event_type=HookEventType.HOOK_TIMEOUT.value,
            session_id=run.session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tool_name=f"hook:on_run_start:{hook_config.agent_name}",
            error=error,
        )
        insert_event(event)
        await sse_manager.broadcast(StreamEventType.EVENT, {"data": event.model_dump()}, session_id=run.session_id)

        if DEBUG:
            print(f"[DEBUG] Hook timed out after {timeout_seconds}s", flush=True)

        # Apply on_error policy for timeout
        if hook_config.on_error == HookOnError.BLOCK:
            return HookResult(
                success=False,
                action=HookAction.BLOCK,
                error=error,
                block_reason=error,
                duration_ms=duration_ms,
            )
        else:
            return HookResult(
                success=False,
                action=HookAction.CONTINUE,
                error=error,
                duration_ms=duration_ms,
            )

    except Exception as e:
        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        error = str(e)

        # Emit hook_failed event
        event = Event(
            event_type=HookEventType.HOOK_FAILED.value,
            session_id=run.session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tool_name=f"hook:on_run_start:{hook_config.agent_name}",
            error=error,
        )
        insert_event(event)
        await sse_manager.broadcast(StreamEventType.EVENT, {"data": event.model_dump()}, session_id=run.session_id)

        if DEBUG:
            print(f"[DEBUG] Hook exception: {error}", flush=True)

        # Apply on_error policy
        if hook_config.on_error == HookOnError.BLOCK:
            return HookResult(
                success=False,
                action=HookAction.BLOCK,
                error=error,
                block_reason=f"Hook error: {error}",
                duration_ms=duration_ms,
            )
        else:
            return HookResult(
                success=False,
                action=HookAction.CONTINUE,
                error=error,
                duration_ms=duration_ms,
            )


async def execute_on_run_finish_hook(
    hook_config: HookAgentConfig,
    run: Any,  # Run model from run_queue
    agent_name: str,
    result_text: Optional[str],
    result_data: Optional[dict],
    status: str,
    error: Optional[str],
    run_queue: Any,  # RunQueue instance
    sse_manager: Any,  # SSEManager instance
) -> None:
    """
    Execute on_run_finish hook fire-and-forget.

    This function creates a hook session and run, then returns immediately.
    The hook execution continues in the background.

    Args:
        hook_config: Hook configuration specifying the hook agent
        run: The main run that completed
        agent_name: Name of the main agent that ran
        result_text: Text result from the run (if any)
        result_data: Structured data result from the run (if any)
        status: Final status of the run
        error: Error message if run failed
        run_queue: RunQueue instance for creating runs
        sse_manager: SSEManager for broadcasting events
    """
    from services.run_queue import RunCreate, RunType

    hook_session_id = _generate_hook_session_id()
    now = datetime.now(timezone.utc).isoformat()

    # Emit hook_start event
    hook_start_event = Event(
        event_type=HookEventType.HOOK_START.value,
        session_id=run.session_id,
        timestamp=now,
        tool_name=f"hook:on_run_finish:{hook_config.agent_name}",
        tool_input={
            "hook_session_id": hook_session_id,
            "hook_agent": hook_config.agent_name,
        },
    )
    insert_event(hook_start_event)
    await sse_manager.broadcast(
        StreamEventType.EVENT,
        {"data": hook_start_event.model_dump()},
        session_id=run.session_id,
    )

    if DEBUG:
        print(f"[DEBUG] Starting on_run_finish hook for run {run.run_id} with agent {hook_config.agent_name} (fire-and-forget)", flush=True)

    try:
        # Create session for hook agent
        create_session(
            session_id=hook_session_id,
            timestamp=now,
            status="pending",
            agent_name=hook_config.agent_name,
            parent_session_id=run.session_id,  # Link to main run's session
        )

        # Create and queue run for hook agent (fire-and-forget)
        # Design decision: Pass the RESULT of the completed run, not the input parameters.
        # Priority order:
        #   1. result_data (structured output) - passed directly as parameters
        #   2. result_text (text output) - wrapped as {"prompt": result_text}
        # This allows the hook agent to observe/process what the main agent produced.
        if result_data is not None:
            # Structured output takes priority - pass directly
            hook_parameters = result_data
        elif result_text is not None:
            # Text output - wrap as prompt for autonomous agent compatibility
            hook_parameters = {"prompt": result_text}
        else:
            # No result available (edge case) - pass empty dict
            hook_parameters = {}

        hook_run_create = RunCreate(
            type=RunType.START_SESSION,
            session_id=hook_session_id,
            agent_name=hook_config.agent_name,
            parameters=hook_parameters,
            parent_session_id=run.session_id,
        )

        hook_run = run_queue.add_run(hook_run_create)

        if DEBUG:
            print(f"[DEBUG] Created fire-and-forget hook run {hook_run.run_id} for session {hook_session_id}", flush=True)

    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Failed to create on_run_finish hook: {e}", flush=True)

        # Emit hook_failed event for fire-and-forget (best effort)
        event = Event(
            event_type=HookEventType.HOOK_FAILED.value,
            session_id=run.session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tool_name=f"hook:on_run_finish:{hook_config.agent_name}",
            error=str(e),
        )
        insert_event(event)
        # Fire-and-forget: don't await broadcast, don't propagate error
        asyncio.create_task(
            sse_manager.broadcast(StreamEventType.EVENT, {"data": event.model_dump()}, session_id=run.session_id)
        )
