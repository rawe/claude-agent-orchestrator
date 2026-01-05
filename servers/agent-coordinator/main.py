from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import json
import os
import asyncio
import uuid as uuid_module

from database import (
    init_db, insert_session, insert_event, get_sessions, get_events,
    update_session_status, update_session_metadata, delete_session,
    create_session, get_session_by_id, get_session_result,
    update_session_parent, bind_session_executor, get_session_affinity,
    SessionAlreadyExistsError
)
from auth import validate_startup_config, verify_api_key, AUTH_ENABLED, AuthConfigError
from models import (
    Event, SessionMetadataUpdate, SessionCreate, SessionBind,
    Agent, AgentCreate, AgentUpdate, AgentStatusUpdate, RunnerDemands,
    ExecutionMode, StreamEventType, SessionEventType,
    Capability, CapabilityCreate, CapabilityUpdate, CapabilitySummary
)
from openapi_config import (
    API_TITLE, API_DESCRIPTION, API_VERSION, API_CONTACT, API_LICENSE,
    OPENAPI_TAGS, SECURITY_SCHEMES,
    OkResponse, ErrorDetail, SessionResponse, SessionListResponse,
    SessionCreateResponse, SessionAffinityResponse, SessionResultResponse,
    SessionStatusResponse, SessionDeleteResponse, EventListResponse,
    RunResponse, RunCreateResponse, RunListResponse,
    RunnerRegisterResponse, RunnerInfoResponse, RunnerListResponse, RunnerPollResponse,
    HealthResponse
)
import agent_storage
from agent_storage import CapabilityResolutionError, MissingCapabilityError, MCPServerConflictError
import capability_storage
from validation import validate_agent_name, validate_capability_name
from datetime import datetime, timezone

# Initialize database BEFORE run_queue (which loads from DB on init)
init_db()

# Import run queue types and init function
from services.run_queue import init_run_queue, RunCreate, Run, RunStatus, RunType
# Import runner registry and other services
from services.runner_registry import runner_registry, RunnerInfo, DuplicateRunnerError
from services.stop_command_queue import stop_command_queue
from services.sse_manager import sse_manager, SSEConnection
from services import callback_processor

# Debug logging toggle - set DEBUG_LOGGING=true to enable verbose output
DEBUG = os.getenv("DEBUG_LOGGING", "").lower() in ("true", "1", "yes")

# Runner configuration
RUNNER_POLL_TIMEOUT = int(os.getenv("RUNNER_POLL_TIMEOUT", "30"))
RUNNER_HEARTBEAT_INTERVAL = int(os.getenv("RUNNER_HEARTBEAT_INTERVAL", "60"))
# Lifecycle thresholds (ADR-012)
RUNNER_STALE_THRESHOLD = int(os.getenv("RUNNER_STALE_THRESHOLD", "120"))  # 2 minutes
RUNNER_REMOVE_THRESHOLD = int(os.getenv("RUNNER_REMOVE_THRESHOLD", "600"))  # 10 minutes
RUNNER_LIFECYCLE_INTERVAL = int(os.getenv("RUNNER_LIFECYCLE_INTERVAL", "30"))  # Check every 30s
# Run demand timeout (ADR-011)
RUN_NO_MATCH_TIMEOUT = int(os.getenv("RUN_NO_MATCH_TIMEOUT", "300"))  # 5 minutes

# Run recovery mode (Phase 5)
# - "none": Load as-is (may have stale claimed/running runs)
# - "stale": Recover runs older than 5 minutes (default)
# - "all": Aggressively recover all non-terminal runs
RUN_RECOVERY_MODE = os.getenv("RUN_RECOVERY_MODE", "stale")

# OpenAPI documentation toggle
# Set DOCS_ENABLED=true to enable /docs, /redoc, and /openapi.json (disabled by default for security)
DOCS_ENABLED = os.getenv("DOCS_ENABLED", "false").lower() in ("true", "1", "yes")

# Initialize run_queue with recovery mode now that env vars are loaded
run_queue = init_run_queue(recovery_mode=RUN_RECOVERY_MODE)


async def update_session_status_and_broadcast(session_id: str, status: str) -> dict | None:
    """Update session status in DB and broadcast to SSE clients.

    Args:
        session_id: The session ID to update
        status: New status ('running', 'stopping', 'stopped', 'finished')

    Returns:
        Updated session dict, or None if session not found
    """
    update_session_status(session_id, status)
    updated_session = get_session_by_id(session_id)
    if not updated_session:
        return None

    # Broadcast to SSE clients
    await sse_manager.broadcast(StreamEventType.SESSION_UPDATED, {"session": updated_session}, session_id=session_id)

    if DEBUG:
        print(f"[DEBUG] Session {session_id} status updated to '{status}', broadcasted to clients", flush=True)

    return updated_session


async def runner_lifecycle_task():
    """Background task to update runner lifecycle states.

    Runs periodically to mark stale runners and remove old ones.
    """
    while True:
        await asyncio.sleep(RUNNER_LIFECYCLE_INTERVAL)
        try:
            stale_ids, removed_ids = runner_registry.update_lifecycle(
                stale_threshold_seconds=RUNNER_STALE_THRESHOLD,
                remove_threshold_seconds=RUNNER_REMOVE_THRESHOLD,
            )
            if DEBUG:
                if stale_ids:
                    print(f"[DEBUG] Runners marked stale: {stale_ids}", flush=True)
                if removed_ids:
                    print(f"[DEBUG] Runners removed: {removed_ids}", flush=True)
                    # Cleanup stop command queue for removed runners
                    for runner_id in removed_ids:
                        stop_command_queue.unregister_runner(runner_id)
        except Exception as e:
            print(f"[ERROR] Runner lifecycle task error: {e}", flush=True)


async def run_timeout_task():
    """Background task to fail runs that have timed out waiting for a matching runner.

    Runs periodically to check for pending runs that have exceeded their timeout.
    See ADR-011 for demand matching and timeout behavior.
    """
    while True:
        await asyncio.sleep(RUNNER_LIFECYCLE_INTERVAL)  # Check at same interval as lifecycle
        try:
            failed_runs = run_queue.fail_timed_out_runs()
            for run in failed_runs:
                if DEBUG:
                    print(f"[DEBUG] Run {run.run_id} timed out waiting for matching runner", flush=True)

                run_failed_data = {
                    "run_id": run.run_id,
                    "error": run.error,
                    "session_id": run.session_id,
                }

                # Broadcast to SSE clients
                await sse_manager.broadcast(StreamEventType.RUN_FAILED, run_failed_data, session_id=run.session_id)
        except Exception as e:
            print(f"[ERROR] Run timeout task error: {e}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    # Validate auth configuration before starting
    try:
        validate_startup_config()
    except AuthConfigError as e:
        print(f"[FATAL] {e}", flush=True)
        raise SystemExit(1)

    if not AUTH_ENABLED:
        print("[WARNING] Authentication is DISABLED. Do not use in production!", flush=True)

    # Note: init_db() and run_queue initialization happen at module import time
    # (with recovery based on RUN_RECOVERY_MODE env var)

    # Start runner lifecycle background task
    lifecycle_task = asyncio.create_task(runner_lifecycle_task())
    # Start run timeout background task (ADR-011)
    timeout_task = asyncio.create_task(run_timeout_task())

    yield

    # Cancel background tasks
    lifecycle_task.cancel()
    timeout_task.cancel()
    try:
        await lifecycle_task
    except asyncio.CancelledError:
        pass
    try:
        await timeout_task
    except asyncio.CancelledError:
        pass

    # Clear all SSE connections (they will close on their own when clients disconnect)
    sse_manager.clear_all()


def custom_openapi():
    """Custom OpenAPI schema with security schemes."""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        routes=app.routes,
        tags=OPENAPI_TAGS,
        contact=API_CONTACT,
        license_info=API_LICENSE,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = SECURITY_SCHEMES
    # Apply security globally (can be overridden per-operation)
    openapi_schema["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    contact=API_CONTACT,
    license_info=API_LICENSE,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)],
    # Disable docs endpoints when DOCS_ENABLED=false (for production)
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
)

# Override OpenAPI schema to include security schemes (only if docs enabled)
if DOCS_ENABLED:
    app.openapi = custom_openapi

# Enable CORS for frontend
# CORS_ORIGINS must be set via environment variable
# Use "*" to allow all origins (default for local development)
# Use comma-separated list for production: "https://app.example.com,https://admin.example.com"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/events", tags=["Events (Legacy)"], response_model=OkResponse)
async def receive_event(event: Event):
    """Receive events from hook scripts and broadcast to SSE clients.

    Events are posted using session_id (coordinator-generated).

    **DEPRECATION NOTE**: This endpoint will be removed once all clients migrate to
    `POST /sessions/{session_id}/events` for event posting.
    """

    # Debug: Log incoming event
    if DEBUG:
        print(f"[DEBUG] Received event: type={event.event_type}, session_id={event.session_id}", flush=True)
        print(f"[DEBUG] Event data: {event.model_dump()}", flush=True)

    try:
        # Update database
        if event.event_type == SessionEventType.SESSION_START.value:
            insert_session(event.session_id, event.timestamp)
            if DEBUG:
                print(f"[DEBUG] Inserted session: {event.session_id}", flush=True)
        elif event.event_type == SessionEventType.SESSION_STOP.value:
            # Update session status to finished
            update_session_status(event.session_id, "finished")
            if DEBUG:
                print(f"[DEBUG] Updated session status to finished: {event.session_id}", flush=True)

        insert_event(event)
        if DEBUG:
            print(f"[DEBUG] Inserted event successfully", flush=True)

        # Broadcast to SSE clients
        event_data = {"data": event.model_dump()}
        await sse_manager.broadcast(StreamEventType.EVENT, event_data, session_id=event.session_id)

        return {"ok": True}

    except Exception as e:
        print(f"[ERROR] Failed to process event: {e}", flush=True)
        print(f"[ERROR] Event that failed: {event.model_dump()}", flush=True)
        raise

@app.get("/sessions", tags=["Sessions"], response_model=SessionListResponse)
async def list_sessions():
    """Get all sessions.

    Returns all sessions with their current status and metadata.
    """
    return {"sessions": get_sessions()}


@app.post("/sessions", tags=["Sessions"], status_code=201)
async def create_session_endpoint(session: SessionCreate):
    """Create a new session with full metadata.

    The `session_id` is coordinator-generated and must be provided.
    This is typically called by the runner after receiving a run.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Determine parent_session_id: prefer run's value over request's value
    parent_session_id = session.parent_session_id

    # Check if there's a running/claimed run for this session_id
    run = run_queue.get_run_by_session_id(session.session_id)
    if run and run.parent_session_id:
        parent_session_id = run.parent_session_id
        if DEBUG:
            print(f"[DEBUG] Session {session.session_id} inheriting parent {parent_session_id} from run {run.run_id}", flush=True)

    try:
        new_session = create_session(
            session_id=session.session_id,
            timestamp=timestamp,
            project_dir=session.project_dir,
            agent_name=session.agent_name,
            parent_session_id=parent_session_id,
        )
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=409, detail="Session already exists")
        raise

    # Broadcast to SSE clients
    await sse_manager.broadcast(StreamEventType.SESSION_CREATED, {"session": new_session}, session_id=session.session_id)

    return {"ok": True, "session": new_session}


@app.post("/sessions/{session_id}/bind", tags=["Sessions"])
async def bind_session_endpoint(session_id: str, binding: SessionBind):
    """Bind executor information to a session after framework starts.

    Called by executor after it gets the framework's session ID.
    Updates session status to 'running' and stores affinity information
    for resume routing. See ADR-010 for details.
    """
    result = bind_session_executor(
        session_id=session_id,
        executor_session_id=binding.executor_session_id,
        hostname=binding.hostname,
        executor_profile=binding.executor_profile,
        project_dir=binding.project_dir,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if DEBUG:
        print(f"[DEBUG] Session {session_id} bound to executor {binding.executor_session_id}", flush=True)

    # Broadcast to SSE clients
    await sse_manager.broadcast(StreamEventType.SESSION_UPDATED, {"session": result}, session_id=session_id)

    return {"ok": True, "session": result}


@app.get("/sessions/{session_id}", tags=["Sessions"])
async def get_session_endpoint(session_id: str):
    """Get single session details."""
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session}


@app.get("/sessions/{session_id}/status", tags=["Sessions"], response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """Get session status: running, finished, or not_existent.

    Quick status check without full session details.
    """
    session = get_session_by_id(session_id)
    if session is None:
        return {"status": "not_existent"}
    return {"status": session["status"]}


@app.get("/sessions/{session_id}/result", tags=["Sessions"])
async def get_session_result_endpoint(session_id: str):
    """Get result text from last assistant message.

    Only available for sessions with status 'finished'.
    """
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] != "finished":
        raise HTTPException(status_code=400, detail="Session not finished")

    result = get_session_result(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No result found")

    return {"result": result}


@app.get("/sessions/{session_id}/affinity", tags=["Sessions"], response_model=SessionAffinityResponse)
async def get_session_affinity_endpoint(session_id: str):
    """Get session affinity information for resume routing.

    Returns hostname, project_dir, executor_profile needed to route
    resume requests to the correct runner. See ADR-010 and ADR-011.
    """
    affinity = get_session_affinity(session_id)
    if affinity is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"affinity": affinity}


async def _stop_run(run: Run) -> dict:
    """Shared logic for stopping a run.

    Args:
        run: The run to stop (must be in stoppable state: PENDING, CLAIMED, or RUNNING)

    Returns:
        Response dict with ok, run_id, session_id, status

    Raises:
        HTTPException if run cannot be stopped
    """
    result = {
        "ok": True,
        "run_id": run.run_id,
        "session_id": run.session_id,
    }

    # Handle PENDING runs - not yet claimed by any runner
    if run.status == RunStatus.PENDING:
        # Just mark as stopped directly - no runner to signal
        run_queue.update_run_status(run.run_id, RunStatus.STOPPED)
        result["status"] = "stopped"
        result["message"] = "Run cancelled before execution"

        if DEBUG:
            print(f"[DEBUG] Pending run {run.run_id} cancelled (session={run.session_id})", flush=True)

        # Update session status if exists
        session = get_session_by_id(run.session_id)
        if session:
            await update_session_status_and_broadcast(run.session_id, "stopped")

        return result

    # Handle CLAIMED or RUNNING runs - need to signal the runner
    if run.status not in (RunStatus.CLAIMED, RunStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Run cannot be stopped (status: {run.status})"
        )

    if not run.runner_id:
        raise HTTPException(status_code=400, detail="Run not claimed by any runner")

    # Queue the stop command (wakes up the runner's poll immediately)
    if not stop_command_queue.add_stop(run.runner_id, run.run_id):
        raise HTTPException(status_code=500, detail="Failed to queue stop command")

    # Update run status to STOPPING
    run_queue.update_run_status(run.run_id, RunStatus.STOPPING)
    result["status"] = "stopping"

    if DEBUG:
        print(f"[DEBUG] Stop requested for run {run.run_id} (session={run.session_id}, runner={run.runner_id})", flush=True)

    # Update session status to 'stopping' and broadcast to WebSocket clients
    session = get_session_by_id(run.session_id)
    if session:
        await update_session_status_and_broadcast(run.session_id, "stopping")

    return result


@app.post("/sessions/{session_id}/stop", tags=["Sessions"])
async def stop_session(session_id: str):
    """Stop a running session by signaling its runner.

    Finds the active run for this session and queues a stop command.
    The runner will receive the stop command on its next poll and terminate the process.

    This endpoint is idempotent and handles various states:
    - If session is 'stopping', returns success (already stopping)
    - If session is 'stopped' or 'finished', returns appropriate message
    - If no active run found but session exists, updates status accordingly
    """
    # Get session
    session = get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_status = session["status"]

    # Handle already-stopped states
    if session_status == "stopping":
        return {
            "ok": True,
            "session_id": session_id,
            "status": "stopping",
            "message": "Session is already being stopped"
        }

    if session_status in ("stopped", "finished"):
        return {
            "ok": True,
            "session_id": session_id,
            "status": session_status,
            "message": f"Session already {session_status}"
        }

    # Find the run for this session (check by session_id)
    run = run_queue.get_run_by_session_id(session_id)

    if not run:
        # No active run - session might have finished or never started properly
        # Update session status to reflect reality
        if session_status == "running":
            await update_session_status_and_broadcast(session_id, "stopped")
        return {
            "ok": True,
            "session_id": session_id,
            "status": "stopped",
            "message": "No active run found - session marked as stopped"
        }

    # Check if run is in a stoppable state
    if run.status not in (RunStatus.PENDING, RunStatus.CLAIMED, RunStatus.RUNNING):
        # Run already completed/stopped/failed
        if session_status == "running":
            await update_session_status_and_broadcast(session_id, "stopped")
        return {
            "ok": True,
            "session_id": session_id,
            "run_id": run.run_id,
            "status": "stopped",
            "message": f"Run already in {run.status} state - session marked as stopped"
        }

    return await _stop_run(run)


@app.get("/sessions/{session_id}/events", tags=["Sessions"], response_model=EventListResponse)
async def get_session_events(session_id: str):
    """Get events for a specific session."""
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"events": get_events(session_id)}


@app.post("/sessions/{session_id}/events", tags=["Sessions"], response_model=OkResponse, status_code=201)
async def add_session_event(session_id: str, event: Event):
    """Add event to session.

    Handles special event types like `session_stop` which updates session status to 'finished'
    and triggers callback processing for async_callback mode sessions.
    """
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Ensure the event's session_id matches the URL
    if event.session_id != session_id:
        raise HTTPException(status_code=400, detail="Event session_id must match URL session_id")

    # Insert event
    insert_event(event)

    # Handle session_stop special case: update status to finished
    if event.event_type == SessionEventType.SESSION_STOP.value:
        update_session_status(session_id, "finished")

        # Get updated session and broadcast session_updated
        updated_session = get_session_by_id(session_id)

        # Broadcast to SSE clients
        await sse_manager.broadcast(StreamEventType.SESSION_UPDATED, {"session": updated_session}, session_id=session_id)

        # Callback processing: handle child completion and pending notifications
        # Check execution_mode to determine if callback should be triggered (ADR-003)
        # parent_session_id is always set for hierarchy tracking, but callbacks only
        # trigger when execution_mode == ASYNC_CALLBACK
        parent_session_id = updated_session.get("parent_session_id")
        execution_mode = updated_session.get("execution_mode", "sync")

        if parent_session_id and execution_mode == ExecutionMode.ASYNC_CALLBACK.value:
            # This is a child session with callback mode - notify parent
            parent_session = get_session_by_id(parent_session_id)
            parent_status = parent_session["status"] if parent_session else "not_found"

            # Get the child's result
            child_result = get_session_result(session_id)

            if DEBUG:
                print(f"[DEBUG] Child '{session_id}' completed (mode=async_callback), parent '{parent_session_id}' status={parent_status}", flush=True)

            callback_processor.on_child_completed(
                child_session_id=session_id,
                parent_session=parent_session,
                child_result=child_result,
            )

        # Check if this session has pending child callbacks to flush
        flushed = callback_processor.on_session_stopped(session_id)
        if flushed > 0 and DEBUG:
            print(f"[DEBUG] Flushed {flushed} pending callbacks for '{session_id}'", flush=True)

    # Broadcast event to SSE clients
    event_data = {"data": event.model_dump()}
    await sse_manager.broadcast(StreamEventType.EVENT, event_data, session_id=session_id)

    return {"ok": True}


@app.get("/events/{session_id}", tags=["Events (Legacy)"], response_model=EventListResponse)
async def list_events(session_id: str):
    """Get events for a specific session.

    **DEPRECATION NOTE**: Prefer `GET /sessions/{session_id}/events`.
    """
    return {"events": get_events(session_id)}

@app.patch("/sessions/{session_id}/metadata", tags=["Sessions"])
async def update_metadata(session_id: str, metadata: SessionMetadataUpdate):
    """Update session metadata (project_dir, agent_name, executor fields)."""

    # Verify session exists
    session = get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update metadata
    update_session_metadata(
        session_id=session_id,
        project_dir=metadata.project_dir,
        agent_name=metadata.agent_name,
        last_resumed_at=metadata.last_resumed_at,
        executor_session_id=metadata.executor_session_id,
        executor_profile=metadata.executor_profile,
        hostname=metadata.hostname,
    )

    # Get updated session
    updated_session = get_session_by_id(session_id)

    # Broadcast to SSE clients
    await sse_manager.broadcast(StreamEventType.SESSION_UPDATED, {"session": updated_session}, session_id=session_id)

    return {"ok": True, "session": updated_session}


@app.delete("/sessions/{session_id}", tags=["Sessions"])
async def delete_session_endpoint(session_id: str):
    """Delete a session and all its events and runs."""

    # Delete from database (cascade deletes runs and events)
    result = delete_session(session_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Clean up in-memory run cache
    runs_removed_from_cache = run_queue.remove_runs_for_session(session_id)

    # Broadcast to SSE clients
    await sse_manager.broadcast(
        StreamEventType.SESSION_DELETED,
        {
            "session_id": session_id,
            "runs_deleted": result["runs_count"],
        },
        session_id=session_id
    )

    return {
        "ok": True,
        "session_id": session_id,
        "deleted": result,
        "runs_removed_from_cache": runs_removed_from_cache
    }


# ==============================================================================
# SSE Endpoint (ADR-013)
# ==============================================================================

@app.get("/sse/sessions", tags=["SSE"])
async def sse_sessions(
    request: Request,
    session_id: Optional[str] = Query(None, description="Filter to single session"),
    created_by: Optional[str] = Query(None, description="Filter by session creator"),
    include_init: bool = Query(True, description="Include initial state on connect"),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
):
    """SSE endpoint for real-time session updates.

    Returns a `text/event-stream` response with Server-Sent Events.

    **Event Types:**
    - `init`: Initial state with all matching sessions
    - `session_created`: New session created
    - `session_updated`: Session state changed
    - `session_deleted`: Session removed
    - `event`: Session event (tool call, message, etc.)
    - `run_failed`: Run timeout or failure

    **Reconnection:** Use the `Last-Event-ID` header to resume from last event.
    See ADR-013 for design rationale.
    """
    connection_id = str(uuid_module.uuid4())

    async def event_generator():
        """Generate SSE events for this connection."""
        # Register this connection
        conn = SSEConnection(
            connection_id=connection_id,
            session_id_filter=session_id,
            created_by_filter=created_by,
        )
        sse_manager.register(conn)

        try:
            # Send initial state unless resuming or explicitly disabled
            if include_init and not last_event_id:
                # Get filtered sessions (no auth = admin = all sessions)
                sessions = get_sessions()

                # Apply session_id filter if provided
                if session_id:
                    sessions = [s for s in sessions if s.get("session_id") == session_id]

                event_id = await sse_manager.generate_event_id(StreamEventType.INIT)
                yield sse_manager.format_event(event_id, StreamEventType.INIT, {"sessions": sessions})

            # Stream events from the queue with heartbeat
            heartbeat_interval = 30  # seconds
            while True:
                try:
                    # Check for client disconnect
                    if await request.is_disconnected():
                        break

                    # Wait for event with timeout (for heartbeat)
                    event = await asyncio.wait_for(
                        conn.queue.get(),
                        timeout=heartbeat_interval
                    )
                    yield event

                except asyncio.TimeoutError:
                    # Send heartbeat comment to keep connection alive
                    yield ": heartbeat\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            # Cleanup connection on disconnect
            sse_manager.unregister(connection_id)
            if DEBUG:
                print(f"[DEBUG] SSE connection {connection_id} closed", flush=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# ==============================================================================
# Agent Registry Routes (merged from agent-registry service)
# ==============================================================================

@app.get("/health", tags=["Health"], response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/agents", tags=["Agents"], response_model=list[Agent], response_model_exclude_none=True)
def list_agents(
    tags: Optional[str] = Query(
        default=None,
        description="Comma-separated tags. Returns agents that have ALL specified tags (AND logic). No tags = all agents."
    )
):
    """
    List all agents, optionally filtered by tags.

    - No tags parameter: Returns all agents (for management UI)
    - tags=foo: Returns agents with tag "foo"
    - tags=foo,bar: Returns agents with BOTH "foo" AND "bar" tags
    """
    agents = agent_storage.list_agents()

    if tags:
        # Parse comma-separated tags into a set
        required_tags = set(tag.strip() for tag in tags.split(",") if tag.strip())
        if required_tags:
            # Filter: agent must have ALL required tags (subset check)
            agents = [a for a in agents if required_tags.issubset(set(a.tags))]

    return agents


@app.get("/agents/{name}", tags=["Agents"], response_model=Agent, response_model_exclude_none=True)
def get_agent(name: str, raw: bool = Query(False, description="Return raw agent without capability resolution")):
    """
    Get agent by name.

    By default, capabilities are resolved and merged into system_prompt and mcp_servers.
    Use `?raw=true` to get the unresolved agent configuration (for editing).
    """
    try:
        agent = agent_storage.get_agent(name, resolve=not raw)
    except MissingCapabilityError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Capability resolution failed: {e.capability_name} not found"
        )
    except MCPServerConflictError as e:
        raise HTTPException(
            status_code=422,
            detail=f"MCP server name conflict: '{e.server_name}' defined in {', '.join(e.sources)}"
        )

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent


@app.post("/agents", tags=["Agents"], response_model=Agent, status_code=201, response_model_exclude_none=True)
def create_agent(data: AgentCreate):
    """Create a new agent blueprint."""
    try:
        validate_agent_name(data.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        agent = agent_storage.create_agent(data)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.patch("/agents/{name}", tags=["Agents"], response_model=Agent, response_model_exclude_none=True)
def update_agent(name: str, updates: AgentUpdate):
    """Update an existing agent blueprint (partial update)."""
    try:
        agent = agent_storage.update_agent(name, updates)
    except MissingCapabilityError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Capability resolution failed: {e.capability_name} not found"
        )
    except MCPServerConflictError as e:
        raise HTTPException(
            status_code=422,
            detail=f"MCP server name conflict: '{e.server_name}' defined in {', '.join(e.sources)}"
        )
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent


@app.delete("/agents/{name}", tags=["Agents"], status_code=204)
def delete_agent(name: str):
    """Delete an agent blueprint."""
    if not agent_storage.delete_agent(name):
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return None


@app.patch("/agents/{name}/status", tags=["Agents"], response_model=Agent, response_model_exclude_none=True)
def update_agent_status(name: str, data: AgentStatusUpdate):
    """Update agent status (active/inactive)."""
    agent = agent_storage.set_agent_status(name, data.status)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent


# ==============================================================================
# Capability Registry Routes (Capabilities System)
# ==============================================================================

@app.get("/capabilities", tags=["Capabilities"], response_model=list[CapabilitySummary])
def list_capabilities():
    """List all capabilities.

    Returns summary view with metadata (has_text, has_mcp, mcp_server_names).
    """
    return capability_storage.list_capabilities()


@app.get("/capabilities/{name}", tags=["Capabilities"], response_model=Capability, response_model_exclude_none=True)
def get_capability(name: str):
    """Get capability by name with full content."""
    capability = capability_storage.get_capability(name)
    if not capability:
        raise HTTPException(status_code=404, detail=f"Capability not found: {name}")
    return capability


@app.post("/capabilities", tags=["Capabilities"], response_model=Capability, status_code=201, response_model_exclude_none=True)
def create_capability(data: CapabilityCreate):
    """Create a new capability."""
    try:
        validate_capability_name(data.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        capability = capability_storage.create_capability(data)
        return capability
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.patch("/capabilities/{name}", tags=["Capabilities"], response_model=Capability, response_model_exclude_none=True)
def update_capability(name: str, updates: CapabilityUpdate):
    """Update an existing capability (partial update)."""
    capability = capability_storage.update_capability(name, updates)
    if not capability:
        raise HTTPException(status_code=404, detail=f"Capability not found: {name}")
    return capability


def _get_agents_using_capability(capability_name: str) -> list[str]:
    """Get list of agent names that reference a capability."""
    agents = agent_storage.list_agents()
    return [a.name for a in agents if capability_name in a.capabilities]


@app.delete("/capabilities/{name}", tags=["Capabilities"], status_code=204)
def delete_capability(name: str):
    """Delete a capability.

    Fails with 409 Conflict if capability is referenced by any agents.
    """
    # Check if capability exists
    if not capability_storage.get_capability(name):
        raise HTTPException(status_code=404, detail=f"Capability not found: {name}")

    # Check for agent references
    agents_using = _get_agents_using_capability(name)
    if agents_using:
        raise HTTPException(
            status_code=409,
            detail=f"Capability is referenced by agents: {', '.join(agents_using)}"
        )

    capability_storage.delete_capability(name)
    return None


# ==============================================================================
# Runner API Routes (for Agent Runner communication)
# ==============================================================================

class RunnerRegisterRequest(BaseModel):
    """Request body for runner registration.

    All properties are required for deterministic runner_id derivation.
    See ADR-012 for runner identity design.
    Tags are optional capabilities (ADR-011).
    """
    hostname: str
    project_dir: str
    executor_profile: str
    # Executor details (type, command, config)
    executor: Optional[dict] = None
    # Optional capability tags (ADR-011)
    tags: Optional[list[str]] = None
    # If true, only accept runs with at least one matching tag
    require_matching_tags: bool = False


class RunnerRegisterResponse(BaseModel):
    """Response from runner registration."""
    runner_id: str
    poll_endpoint: str
    poll_timeout_seconds: int
    heartbeat_interval_seconds: int


class RunnerIdRequest(BaseModel):
    """Request body containing runner_id."""
    runner_id: str


class RunCompletedRequest(BaseModel):
    """Request body for run completion."""
    runner_id: str
    status: str = "success"


class RunFailedRequest(BaseModel):
    """Request body for run failure."""
    runner_id: str
    error: str


class RunStoppedRequest(BaseModel):
    """Request body for run stopped report."""
    runner_id: str
    signal: str = "SIGTERM"


@app.post("/runner/register", tags=["Runners"], response_model=RunnerRegisterResponse)
async def register_runner(request: RunnerRegisterRequest):
    """Register a runner instance.

    Required properties (hostname, project_dir, executor_profile) are used to
    derive a deterministic runner_id. Registration fails if a runner with
    the same identity is already online (409 Conflict).

    If the existing runner is stale, this is treated as a reconnection.
    Optional tags are capabilities the runner offers (ADR-011).
    """
    try:
        runner = runner_registry.register_runner(
            hostname=request.hostname,
            project_dir=request.project_dir,
            executor_profile=request.executor_profile,
            executor=request.executor,
            tags=request.tags,
            require_matching_tags=request.require_matching_tags,
        )
    except DuplicateRunnerError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_runner",
                "message": str(e),
                "runner_id": e.runner_id,
                "hostname": e.hostname,
                "project_dir": e.project_dir,
                "executor_profile": e.executor_profile,
            }
        )

    # Register with stop command queue for immediate wake-up on stop requests
    stop_command_queue.register_runner(runner.runner_id)

    if DEBUG:
        print(f"[DEBUG] Registered runner: {runner.runner_id}", flush=True)
        print(f"[DEBUG]   hostname: {request.hostname}", flush=True)
        print(f"[DEBUG]   project_dir: {request.project_dir}", flush=True)
        print(f"[DEBUG]   executor_profile: {request.executor_profile}", flush=True)
        if request.executor:
            print(f"[DEBUG]   executor: {request.executor}", flush=True)
        if request.tags:
            print(f"[DEBUG]   tags: {request.tags}", flush=True)
        if request.require_matching_tags:
            print(f"[DEBUG]   require_matching_tags: {request.require_matching_tags}", flush=True)

    return RunnerRegisterResponse(
        runner_id=runner.runner_id,
        poll_endpoint="/runner/runs",
        poll_timeout_seconds=RUNNER_POLL_TIMEOUT,
        heartbeat_interval_seconds=RUNNER_HEARTBEAT_INTERVAL,
    )


@app.get("/runner/runs", tags=["Runners"])
async def poll_for_runs(runner_id: str = Query(..., description="The registered runner ID")):
    """Long-poll for available runs or stop commands.

    Holds connection open for up to 30 seconds, returning immediately if
    a run or stop command is available.

    **Responses:**
    - `{"run": {...}}` - Run to execute
    - `{"stop_runs": [...]}` - Session IDs to stop
    - `{"deregistered": true}` - Runner was deregistered
    - `204 No Content` - Nothing available after timeout

    Only runs whose demands match the runner's capabilities will be claimed.
    See ADR-011 for demand matching logic.
    """
    # Check if runner has been deregistered
    if runner_registry.is_deregistered(runner_id):
        # Confirm deregistration and remove from registry
        runner_registry.confirm_deregistered(runner_id)
        stop_command_queue.unregister_runner(runner_id)
        if DEBUG:
            print(f"[DEBUG] Runner {runner_id} deregistered, signaling shutdown", flush=True)
        return {"deregistered": True}

    # Get runner info (needed for demand matching)
    runner = runner_registry.get_runner(runner_id)
    if not runner:
        raise HTTPException(status_code=401, detail="Runner not registered")

    # Get the event for this runner (for immediate wake-up on stop commands)
    event = stop_command_queue.get_event(runner_id)

    # Poll for runs with timeout
    poll_interval = 0.5  # Check every 500ms
    elapsed = 0.0

    while elapsed < RUNNER_POLL_TIMEOUT:
        # Check for stop commands FIRST (highest priority)
        stop_runs = stop_command_queue.get_and_clear(runner_id)
        if stop_runs:
            if DEBUG:
                print(f"[DEBUG] Runner {runner_id} received stop commands for runs: {stop_runs}", flush=True)
            return {"stop_runs": stop_runs}

        # Check for deregistration during polling
        if runner_registry.is_deregistered(runner_id):
            runner_registry.confirm_deregistered(runner_id)
            stop_command_queue.unregister_runner(runner_id)
            if DEBUG:
                print(f"[DEBUG] Runner {runner_id} deregistered during poll, signaling shutdown", flush=True)
            return {"deregistered": True}

        # Check for new runs (demand matching applied via runner info)
        run = run_queue.claim_run(runner)
        if run:
            if DEBUG:
                print(f"[DEBUG] Runner {runner_id} claimed run {run.run_id}", flush=True)
            return {"run": run.model_dump()}

        # Wait with event for immediate wake-up on stop commands
        if event:
            try:
                await asyncio.wait_for(event.wait(), timeout=poll_interval)
                # Event was set - loop will check stop_runs
            except asyncio.TimeoutError:
                pass
        else:
            await asyncio.sleep(poll_interval)

        elapsed += poll_interval

    # No runs available after timeout
    return Response(status_code=204)


@app.post("/runner/runs/{run_id}/started", tags=["Runners"], response_model=OkResponse)
async def report_run_started(run_id: str, request: RunnerIdRequest):
    """Report that run execution has started."""
    # Verify runner
    if not runner_registry.get_runner(request.runner_id):
        raise HTTPException(status_code=401, detail="Runner not registered")

    # Get run first to access parent_session_id
    run = run_queue.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Update run status to running
    run = run_queue.update_run_status(run_id, RunStatus.RUNNING)

    # Link run's parent_session_id to session (for resume case where session already exists)
    if run.parent_session_id:
        session = get_session_by_id(run.session_id)
        if session:
            # Session exists (resume case) - update parent
            update_session_parent(run.session_id, run.parent_session_id)
            if DEBUG:
                print(f"[DEBUG] Updated session {run.session_id} parent to {run.parent_session_id}", flush=True)
        # If session doesn't exist yet (start case), POST /sessions will pick up parent from run

    if DEBUG:
        print(f"[DEBUG] Run {run_id} started by runner {request.runner_id}", flush=True)

    return {"ok": True}


@app.post("/runner/runs/{run_id}/completed", tags=["Runners"], response_model=OkResponse)
async def report_run_completed(run_id: str, request: RunCompletedRequest):
    """Report that run completed successfully."""
    # Verify runner
    if not runner_registry.get_runner(request.runner_id):
        raise HTTPException(status_code=401, detail="Runner not registered")

    run = run_queue.update_run_status(run_id, RunStatus.COMPLETED)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if DEBUG:
        print(f"[DEBUG] Run {run_id} completed by runner {request.runner_id}", flush=True)

   # TODO: ADD - Move success callback here from POST /sessions/{session_id}/events
    # This will unify callback triggers with failure/stopped callbacks.
    # Implementation pattern (same as report_run_failed and report_run_stopped):
    # TODO: check for correctnes because this was written as pseudo code
    # if run.parent_session_id:
    #     parent_session = get_session_by_id(run.parent_session_id)
    #     parent_status = parent_session["status"] if parent_session else "not_found"
    #     child_session = get_session_by_id(run.session_id)
    #     child_result = get_session_result(child_session["session_id"]) if child_session else None
    #
    #     if DEBUG:
    #         print(f"[DEBUG] Run completed for child '{run.session_name}', notifying parent '{run.parent_session_name}'", flush=True)
    #
    #     callback_processor.on_child_completed(
    #         child_session_id=run.session_id,
    #         parent_session_id=run.parent_session_id,
    #         parent_status=parent_status,
    #         child_result=child_result,
    #     )
    #
    # See: docs/features/agent-callback-architecture.md "Callback Trigger Implementation"
    # END TODO: ADD
    return {"ok": True}


@app.post("/runner/runs/{run_id}/failed", tags=["Runners"], response_model=OkResponse)
async def report_run_failed(run_id: str, request: RunFailedRequest):
    """Report that run execution failed."""
    # Verify runner
    if not runner_registry.get_runner(request.runner_id):
        raise HTTPException(status_code=401, detail="Runner not registered")

    run = run_queue.update_run_status(run_id, RunStatus.FAILED, error=request.error)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if DEBUG:
        print(f"[DEBUG] Run {run_id} failed: {request.error}", flush=True)

    # Notify parent if this was a callback run (ADR-003)
    # Only trigger callback if execution_mode == ASYNC_CALLBACK
    if run.parent_session_id and run.execution_mode == ExecutionMode.ASYNC_CALLBACK:
        parent_session = get_session_by_id(run.parent_session_id)

        if DEBUG:
            parent_status = parent_session["status"] if parent_session else "not_found"
            print(f"[DEBUG] Run failed for child '{run.session_id}' (mode=async_callback), notifying parent '{run.parent_session_id}' status={parent_status}", flush=True)

        callback_processor.on_child_completed(
            child_session_id=run.session_id,
            parent_session=parent_session,
            child_result=None,
            child_failed=True,
            child_error=request.error,
        )

    return {"ok": True}


@app.post("/runner/runs/{run_id}/stopped", tags=["Runners"], response_model=OkResponse)
async def report_run_stopped(run_id: str, request: RunStoppedRequest):
    """Report that run was stopped (terminated by stop command).

    Called by runner after terminating a process in response to a stop command.
    Updates session status to 'stopped' and broadcasts to SSE clients.
    """
    # Verify runner
    if not runner_registry.get_runner(request.runner_id):
        raise HTTPException(status_code=401, detail="Runner not registered")

    run = run_queue.update_run_status(run_id, RunStatus.STOPPED)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if DEBUG:
        print(f"[DEBUG] Run {run_id} stopped by runner {request.runner_id} (signal={request.signal})", flush=True)

    # Notify parent if this was a callback run (treat as failure) (ADR-003)
    # Only trigger callback if execution_mode == ASYNC_CALLBACK
    if run.parent_session_id and run.execution_mode == ExecutionMode.ASYNC_CALLBACK:
        parent_session = get_session_by_id(run.parent_session_id)

        if DEBUG:
            parent_status = parent_session["status"] if parent_session else "not_found"
            print(f"[DEBUG] Run stopped for child '{run.session_id}' (mode=async_callback), notifying parent '{run.parent_session_id}' status={parent_status}", flush=True)

        callback_processor.on_child_completed(
            child_session_id=run.session_id,
            parent_session=parent_session,
            child_result=None,
            child_failed=True,
            child_error="Session was manually stopped",
        )

    # Update session status to 'stopped' and broadcast to WebSocket clients
    session = get_session_by_id(run.session_id)
    if session:
        await update_session_status_and_broadcast(run.session_id, "stopped")

    return {"ok": True}


@app.post("/runner/heartbeat", tags=["Runners"], response_model=OkResponse)
async def runner_heartbeat(request: RunnerIdRequest):
    """Keep runner registration alive."""
    if not runner_registry.heartbeat(request.runner_id):
        raise HTTPException(status_code=401, detail="Runner not registered")

    return {"ok": True}


class RunnerWithStatus(BaseModel):
    """Runner info with status from server."""
    runner_id: str
    registered_at: str
    last_heartbeat: str
    hostname: str
    project_dir: str
    executor_profile: str
    executor: dict = {}  # Executor details (type, command, config)
    tags: list[str] = []  # Capability tags (ADR-011)
    require_matching_tags: bool = False  # If true, only accept runs with matching tags
    status: str  # "online" or "stale"
    seconds_since_heartbeat: float


@app.get("/runners", tags=["Runners"])
async def list_runners():
    """List all registered runners with their status.

    Returns all runners with status (managed by background lifecycle task):
    - `online`: heartbeat within threshold
    - `stale`: no heartbeat for 2+ minutes (connection may be lost)
    """
    runners = runner_registry.get_all_runners()
    result = []

    for runner in runners:
        seconds = runner_registry.get_seconds_since_heartbeat(runner.runner_id)
        if seconds is None:
            continue  # Shouldn't happen, but skip if it does

        result.append(RunnerWithStatus(
            runner_id=runner.runner_id,
            registered_at=runner.registered_at,
            last_heartbeat=runner.last_heartbeat,
            hostname=runner.hostname,
            project_dir=runner.project_dir,
            executor_profile=runner.executor_profile,
            executor=runner.executor,
            tags=runner.tags,
            require_matching_tags=runner.require_matching_tags,
            status=runner.status,
            seconds_since_heartbeat=seconds,
        ))

    return {"runners": result}


@app.delete("/runners/{runner_id}", tags=["Runners"])
async def deregister_runner(
    runner_id: str,
    self_initiated: bool = Query(False, alias="self", description="True if runner is deregistering itself"),
):
    """Deregister a runner.

    **Two modes:**
    - External (dashboard): Marks runner for deregistration, signals on next poll
    - Self-initiated (runner shutdown): Immediately removes from registry
    """
    # Check if runner exists
    if not runner_registry.get_runner(runner_id):
        raise HTTPException(status_code=404, detail="Runner not found")

    if self_initiated:
        # Runner is shutting down gracefully - remove immediately
        runner_registry.remove_runner(runner_id)
        stop_command_queue.unregister_runner(runner_id)
        if DEBUG:
            print(f"[DEBUG] Runner {runner_id} self-deregistered (graceful shutdown)", flush=True)
        return {"ok": True, "message": "Runner deregistered", "initiated_by": "self"}
    else:
        # External request (dashboard) - mark for deregistration, signal on next poll
        runner_registry.mark_deregistered(runner_id)
        if DEBUG:
            print(f"[DEBUG] Runner {runner_id} marked for deregistration (external request)", flush=True)
        return {"ok": True, "message": "Runner marked for deregistration", "initiated_by": "external"}


# ==============================================================================
# Runs API Routes (for creating and querying runs)
# ==============================================================================

@app.post("/runs", tags=["Runs"], response_model=RunCreateResponse, status_code=201)
async def create_run(run_create: RunCreate):
    """Create a new run for the runner to execute.

    If `session_id` is not provided for `start_session`, coordinator generates one (ADR-010).
    For `resume_session`, `session_id` is required.
    Returns both `run_id` and `session_id` in the response.

    For `start_session` runs, a new session is created with status 'pending'.
    For `resume_session` runs, affinity demands ensure the run goes to the same runner.

    Demands are merged from blueprint (if agent_name provided) and additional_demands.
    See ADR-011 for demand matching logic.
    """
    # Validate: resume_session requires session_id
    if run_create.type == RunType.RESUME_SESSION and not run_create.session_id:
        raise HTTPException(status_code=400, detail="session_id is required for resume_session")

    # For start runs, create session FIRST (runs table has FK to sessions)
    if run_create.type == RunType.START_SESSION:
        # Generate session_id if not provided
        from services.run_queue import generate_session_id
        session_id = run_create.session_id or generate_session_id()
        run_create.session_id = session_id  # Ensure run uses same session_id

        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            new_session = create_session(
                session_id=session_id,
                timestamp=timestamp,
                status="pending",
                project_dir=run_create.project_dir,
                agent_name=run_create.agent_name,
                parent_session_id=run_create.parent_session_id,
                execution_mode=run_create.execution_mode.value,
            )
            if DEBUG:
                print(f"[DEBUG] Created pending session {session_id} (mode={run_create.execution_mode.value})", flush=True)
        except SessionAlreadyExistsError as e:
            raise HTTPException(status_code=409, detail=f"Session '{e.session_id}' already exists")
        except Exception:
            raise

    # Create the run (session must exist for FK constraint)
    run = run_queue.add_run(run_create)

    # Broadcast session creation after run is created (so we have run_id)
    if run_create.type == RunType.START_SESSION:
        if DEBUG:
            print(f"[DEBUG] Created run {run.run_id} for session {run.session_id}", flush=True)
        await sse_manager.broadcast(StreamEventType.SESSION_CREATED, {"session": new_session}, session_id=run.session_id)

    # Merge demands from blueprint, affinity, and additional_demands (ADR-011)
    merged_demands = None
    affinity_demands = RunnerDemands()  # Empty defaults - populated for resume runs
    blueprint_demands = RunnerDemands()  # Empty defaults
    additional_demands = RunnerDemands()  # Empty defaults

    # For RESUME_SESSION, look up session affinity and enforce it (ADR-010)
    # This ensures resume runs go to the same runner that owns the session
    if run_create.type == RunType.RESUME_SESSION:
        affinity = get_session_affinity(run_create.session_id)
        if affinity:
            # Create demands from affinity - hostname and executor_profile are required
            affinity_demands = RunnerDemands(
                hostname=affinity.get('hostname'),
                executor_profile=affinity.get('executor_profile'),
            )
            if DEBUG:
                print(f"[DEBUG] Resume run {run.run_id}: enforcing affinity demands "
                      f"hostname={affinity.get('hostname')}, executor_profile={affinity.get('executor_profile')}", flush=True)

    # Load blueprint demands if agent_name provided
    if run_create.agent_name:
        agent = agent_storage.get_agent(run_create.agent_name)
        if agent and agent.demands:
            blueprint_demands = agent.demands

    # Parse additional_demands from request
    if run_create.additional_demands:
        additional_demands = RunnerDemands(**run_create.additional_demands)

    # Merge demands: affinity (mandatory for resume) + blueprint + additional
    # Affinity takes precedence for resume runs
    merged_demands = RunnerDemands.merge(
        RunnerDemands.merge(affinity_demands, blueprint_demands),
        additional_demands
    )

    # Only store and set timeout if there are actual demands
    if not merged_demands.is_empty():
        run_queue.set_run_demands(
            run.run_id,
            merged_demands.model_dump(exclude_none=True),
            timeout_seconds=RUN_NO_MATCH_TIMEOUT,
        )
        if DEBUG:
            print(f"[DEBUG] Run {run.run_id} has demands: {merged_demands.model_dump(exclude_none=True)}", flush=True)

    if DEBUG:
        print(f"[DEBUG] Created run {run.run_id}: type={run.type}, session={run.session_id}", flush=True)

    return {"run_id": run.run_id, "session_id": run.session_id, "status": run.status}


@app.get("/runs", tags=["Runs"], response_model=RunListResponse)
async def list_runs(
    status: Optional[str] = Query(None, description="Filter by status (e.g., 'completed', 'failed', 'pending')"),
):
    """List all runs.

    Returns all runs from cache. Use status parameter to filter.
    """
    runs = run_queue.get_all_runs()
    if status:
        runs = [r for r in runs if r.status.value == status]

    return {"runs": [run.model_dump() for run in runs]}


@app.get("/runs/{run_id}", tags=["Runs"], response_model=RunResponse)
async def get_run(run_id: str):
    """Get run status and details.

    Checks cache first for active runs (fast), then falls back to database
    for completed runs that have been removed from cache.
    """
    run = run_queue.get_run_with_fallback(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return run.model_dump()


@app.post("/runs/{run_id}/stop", tags=["Runs"])
async def stop_run(run_id: str):
    """Stop a running run by signaling its runner.

    Queues a stop command for the runner that will terminate the run's process.
    The runner will receive the stop command on its next poll and terminate the process.
    """
    run = run_queue.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return await _stop_run(run)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # Bind to all interfaces for Docker
        port=8765,
        reload=True,
        log_level="info"
    )