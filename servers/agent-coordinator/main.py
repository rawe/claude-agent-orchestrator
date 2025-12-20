from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import json
import os
import asyncio

from database import (
    init_db, insert_session, insert_event, get_sessions, get_events,
    update_session_status, update_session_metadata, delete_session,
    create_session, get_session_by_id, get_session_result,
    update_session_parent, bind_session_executor, get_session_affinity
)
from models import (
    Event, SessionMetadataUpdate, SessionCreate, SessionBind,
    Agent, AgentCreate, AgentUpdate, AgentStatusUpdate, RunnerDemands,
    ExecutionMode
)
import agent_storage
from validation import validate_agent_name
from datetime import datetime, timezone

# Import run queue and runner registry services
from services.run_queue import run_queue, RunCreate, Run, RunStatus, RunType
from services.runner_registry import runner_registry, RunnerInfo
from services.stop_command_queue import stop_command_queue
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

# WebSocket connections (in-memory set)
connections: set[WebSocket] = set()


async def update_session_status_and_broadcast(session_id: str, status: str) -> dict | None:
    """Update session status in DB and broadcast to WebSocket clients.

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

    message = json.dumps({"type": "session_updated", "session": updated_session})
    for ws in connections.copy():
        try:
            await ws.send_text(message)
        except:
            connections.discard(ws)

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
                # Broadcast run failure to WebSocket clients
                message = json.dumps({
                    "type": "run_failed",
                    "run_id": run.run_id,
                    "error": run.error,
                    "session_id": run.session_id,
                })
                for ws in connections.copy():
                    try:
                        await ws.send_text(message)
                    except:
                        connections.discard(ws)
        except Exception as e:
            print(f"[ERROR] Run timeout task error: {e}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    init_db()

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

    # Close all WebSocket connections
    for ws in connections.copy():
        try:
            await ws.close()
        except:
            pass

app = FastAPI(
    title="Agent Coordinator",
    description="Unified service for agent session management and agent blueprint registry",
    version="0.3.0",  # Bumped for ADR-010
    lifespan=lifespan
)

# Enable CORS for frontend
# Allow multiple origins: old frontend (5173), new unified frontend (3000), and custom via env
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/events")
async def receive_event(event: Event):
    """Receive events from hook scripts and broadcast to WebSocket clients

    Events are posted using session_id (coordinator-generated).
    
    DEPRECATION NOTE: The session_start event handling below will be removed
    once all clients migrate to POST /sessions for session creation.
    The session_stop handling will also migrate to POST /sessions/{id}/events.
    Keep backward compatibility during migration.
    """

    # Debug: Log incoming event
    if DEBUG:
        print(f"[DEBUG] Received event: type={event.event_type}, session_id={event.session_id}", flush=True)
        print(f"[DEBUG] Event data: {event.model_dump()}", flush=True)

    try:
        # Update database
        if event.event_type == "session_start":
            insert_session(event.session_id, event.timestamp)
            if DEBUG:
                print(f"[DEBUG] Inserted session: {event.session_id}", flush=True)
        elif event.event_type == "session_stop":
            # Update session status to finished
            update_session_status(event.session_id, "finished")
            if DEBUG:
                print(f"[DEBUG] Updated session status to finished: {event.session_id}", flush=True)

        insert_event(event)
        if DEBUG:
            print(f"[DEBUG] Inserted event successfully", flush=True)

        # Broadcast to all connected clients
        message = json.dumps({"type": "event", "data": event.model_dump()})
        broadcast_count = 0
        for ws in connections.copy():
            try:
                await ws.send_text(message)
                broadcast_count += 1
            except:
                connections.discard(ws)

        if DEBUG:
            print(f"[DEBUG] Broadcasted to {broadcast_count} WebSocket clients", flush=True)

        return {"ok": True}

    except Exception as e:
        print(f"[ERROR] Failed to process event: {e}", flush=True)
        print(f"[ERROR] Event that failed: {event.model_dump()}", flush=True)
        raise

@app.get("/sessions")
async def list_sessions():
    """Get all sessions"""
    return {"sessions": get_sessions()}


@app.post("/sessions")
async def create_session_endpoint(session: SessionCreate):
    """Create a new session with full metadata.

    session_id is coordinator-generated and must be provided.
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

    # Broadcast to WebSocket clients
    message = json.dumps({"type": "session_created", "session": new_session})
    for ws in connections.copy():
        try:
            await ws.send_text(message)
        except:
            connections.discard(ws)

    return {"ok": True, "session": new_session}


@app.post("/sessions/{session_id}/bind")
async def bind_session_endpoint(session_id: str, binding: SessionBind):
    """Bind executor information to a session after framework starts.

    Called by executor after it gets the framework's session ID.
    Updates session status to 'running'.
    See ADR-010 for details.
    """
    result = bind_session_executor(
        session_id=session_id,
        executor_session_id=binding.executor_session_id,
        hostname=binding.hostname,
        executor_type=binding.executor_type,
        project_dir=binding.project_dir,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if DEBUG:
        print(f"[DEBUG] Session {session_id} bound to executor {binding.executor_session_id}", flush=True)

    # Broadcast to WebSocket clients
    message = json.dumps({"type": "session_updated", "session": result})
    for ws in connections.copy():
        try:
            await ws.send_text(message)
        except:
            connections.discard(ws)

    return {"ok": True, "session": result}


@app.get("/sessions/{session_id}")
async def get_session_endpoint(session_id: str):
    """Get single session details"""
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session}


@app.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get session status: running, finished, or not_existent"""
    session = get_session_by_id(session_id)
    if session is None:
        return {"status": "not_existent"}
    return {"status": session["status"]}


@app.get("/sessions/{session_id}/result")
async def get_session_result_endpoint(session_id: str):
    """Get result text from last assistant message"""
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] != "finished":
        raise HTTPException(status_code=400, detail="Session not finished")

    result = get_session_result(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No result found")

    return {"result": result}


@app.get("/sessions/{session_id}/affinity")
async def get_session_affinity_endpoint(session_id: str):
    """Get session affinity information for resume routing.

    Returns hostname, project_dir, executor_type, executor_session_id
    needed to route resume requests to the correct runner.
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


@app.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a running session by signaling its runner.

    Finds the active run for this session and queues a stop command.
    The runner will receive the stop command on its next poll and terminate the process.

    This endpoint is robust and handles various states:
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


@app.get("/sessions/{session_id}/events")
async def get_session_events(session_id: str):
    """Get events for a specific session"""
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"events": get_events(session_id)}


@app.post("/sessions/{session_id}/events")
async def add_session_event(session_id: str, event: Event):
    """Add event to session (must exist)"""
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Ensure the event's session_id matches the URL
    if event.session_id != session_id:
        raise HTTPException(status_code=400, detail="Event session_id must match URL session_id")

    # Insert event
    insert_event(event)

    # Handle session_stop special case: update status to finished
    if event.event_type == "session_stop":
        update_session_status(session_id, "finished")

        # Get updated session and broadcast session_updated
        updated_session = get_session_by_id(session_id)
        session_message = json.dumps({"type": "session_updated", "session": updated_session})
        for ws in connections.copy():
            try:
                await ws.send_text(session_message)
            except:
                connections.discard(ws)

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
                parent_session_id=parent_session_id,
                parent_status=parent_status,
                child_result=child_result,
            )

        # Check if this session has pending child callbacks to flush
        project_dir = updated_session.get("project_dir")
        flushed = callback_processor.on_session_stopped(session_id, project_dir)
        if flushed > 0 and DEBUG:
            print(f"[DEBUG] Flushed {flushed} pending callbacks for '{session_id}'", flush=True)

    # Broadcast event to WebSocket clients
    message = json.dumps({"type": "event", "data": event.model_dump()})
    for ws in connections.copy():
        try:
            await ws.send_text(message)
        except:
            connections.discard(ws)

    return {"ok": True}


@app.get("/events/{session_id}")
async def list_events(session_id: str):
    """Get events for a specific session"""
    return {"events": get_events(session_id)}

@app.patch("/sessions/{session_id}/metadata")
async def update_metadata(session_id: str, metadata: SessionMetadataUpdate):
    """Update session metadata (project_dir, agent_name, executor fields)"""

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
        executor_type=metadata.executor_type,
        hostname=metadata.hostname,
    )

    # Get updated session
    updated_session = get_session_by_id(session_id)

    # Broadcast update to WebSocket clients
    message = json.dumps({
        "type": "session_updated",
        "session": updated_session
    })

    for ws in connections.copy():
        try:
            await ws.send_text(message)
        except:
            connections.discard(ws)

    return {"ok": True, "session": updated_session}

@app.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    """Delete a session and all its events"""

    # Delete from database
    result = delete_session(session_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Broadcast deletion to WebSocket clients
    message = json.dumps({
        "type": "session_deleted",
        "session_id": session_id
    })

    for ws in connections.copy():
        try:
            await ws.send_text(message)
        except:
            connections.discard(ws)

    return {
        "ok": True,
        "session_id": session_id,
        "deleted": result
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    connections.add(websocket)

    # Send initial state
    sessions = get_sessions()
    await websocket.send_text(json.dumps({
        "type": "init",
        "sessions": sessions
    }))

    try:
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.discard(websocket)


# ==============================================================================
# Agent Registry Routes (merged from agent-registry service)
# ==============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/agents", response_model=list[Agent], response_model_exclude_none=True)
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


@app.get("/agents/{name}", response_model=Agent, response_model_exclude_none=True)
def get_agent(name: str):
    """Get agent by name."""
    agent = agent_storage.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent


@app.post("/agents", response_model=Agent, status_code=201, response_model_exclude_none=True)
def create_agent(data: AgentCreate):
    """Create a new agent."""
    try:
        validate_agent_name(data.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        agent = agent_storage.create_agent(data)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.patch("/agents/{name}", response_model=Agent, response_model_exclude_none=True)
def update_agent(name: str, updates: AgentUpdate):
    """Update an existing agent (partial update)."""
    agent = agent_storage.update_agent(name, updates)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent


@app.delete("/agents/{name}", status_code=204)
def delete_agent(name: str):
    """Delete an agent."""
    if not agent_storage.delete_agent(name):
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return None


@app.patch("/agents/{name}/status", response_model=Agent, response_model_exclude_none=True)
def update_agent_status(name: str, data: AgentStatusUpdate):
    """Update agent status (active/inactive)."""
    agent = agent_storage.set_agent_status(name, data.status)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent


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
    executor_type: str
    # Optional capability tags (ADR-011)
    tags: Optional[list[str]] = None


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


@app.post("/runner/register")
async def register_runner(request: RunnerRegisterRequest):
    """Register a runner instance.

    Required properties (hostname, project_dir, executor_type) are used to
    derive a deterministic runner_id. If a runner with the same properties
    already exists, this is treated as a reconnection.

    Optional tags are capabilities the runner offers (ADR-011).

    Returns runner_id and configuration for polling.
    """
    runner = runner_registry.register_runner(
        hostname=request.hostname,
        project_dir=request.project_dir,
        executor_type=request.executor_type,
        tags=request.tags,
    )

    # Register with stop command queue for immediate wake-up on stop requests
    stop_command_queue.register_runner(runner.runner_id)

    if DEBUG:
        print(f"[DEBUG] Registered runner: {runner.runner_id}", flush=True)
        print(f"[DEBUG]   hostname: {request.hostname}", flush=True)
        print(f"[DEBUG]   project_dir: {request.project_dir}", flush=True)
        print(f"[DEBUG]   executor_type: {request.executor_type}", flush=True)
        if request.tags:
            print(f"[DEBUG]   tags: {request.tags}", flush=True)

    return RunnerRegisterResponse(
        runner_id=runner.runner_id,
        poll_endpoint="/runner/runs",
        poll_timeout_seconds=RUNNER_POLL_TIMEOUT,
        heartbeat_interval_seconds=RUNNER_HEARTBEAT_INTERVAL,
    )


@app.get("/runner/runs")
async def poll_for_runs(runner_id: str = Query(..., description="The registered runner ID")):
    """Long-poll for available runs or stop commands.

    Holds the connection open for up to RUNNER_POLL_TIMEOUT seconds,
    returning immediately if a run or stop command is available.
    Returns 204 No Content if nothing available after timeout.
    Returns {"deregistered": true} if runner has been deregistered.
    Returns {"stop_runs": [...]} if there are runs to stop.

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


@app.post("/runner/runs/{run_id}/started")
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


@app.post("/runner/runs/{run_id}/completed")
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


@app.post("/runner/runs/{run_id}/failed")
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
        parent_status = parent_session["status"] if parent_session else "not_found"

        if DEBUG:
            print(f"[DEBUG] Run failed for child '{run.session_id}' (mode=async_callback), notifying parent '{run.parent_session_id}'", flush=True)

        callback_processor.on_child_completed(
            child_session_id=run.session_id,
            parent_session_id=run.parent_session_id,
            parent_status=parent_status,
            child_result=None,
            child_failed=True,
            child_error=request.error,
        )

    return {"ok": True}


@app.post("/runner/runs/{run_id}/stopped")
async def report_run_stopped(run_id: str, request: RunStoppedRequest):
    """Report that run was stopped (terminated by stop command).

    Called by runner after terminating a process in response to a stop command.
    Updates session status to 'stopped' and broadcasts to WebSocket clients.
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
        parent_status = parent_session["status"] if parent_session else "not_found"

        if DEBUG:
            print(f"[DEBUG] Run stopped for child '{run.session_id}' (mode=async_callback), notifying parent '{run.parent_session_id}'", flush=True)

        callback_processor.on_child_completed(
            child_session_id=run.session_id,
            parent_session_id=run.parent_session_id,
            parent_status=parent_status,
            child_result=None,
            child_failed=True,
            child_error="Session was manually stopped",
        )

    # Update session status to 'stopped' and broadcast to WebSocket clients
    session = get_session_by_id(run.session_id)
    if session:
        await update_session_status_and_broadcast(run.session_id, "stopped")

    return {"ok": True}


@app.post("/runner/heartbeat")
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
    executor_type: str
    status: str  # "online" or "stale"
    seconds_since_heartbeat: float


@app.get("/runners")
async def list_runners():
    """List all registered runners with their status.

    Returns all runners with status (managed by background lifecycle task):
    - "online": heartbeat within threshold
    - "stale": no heartbeat for 2+ minutes (connection may be lost)
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
            executor_type=runner.executor_type,
            status=runner.status,
            seconds_since_heartbeat=seconds,
        ))

    return {"runners": result}


@app.delete("/runners/{runner_id}")
async def deregister_runner(
    runner_id: str,
    self_initiated: bool = Query(False, alias="self", description="True if runner is deregistering itself"),
):
    """Deregister a runner.

    Two modes:
    - External (dashboard): Marks runner for deregistration, signals on next poll
    - Self-initiated (runner shutdown): Immediately removes from registry

    Args:
        runner_id: The runner to deregister
        self_initiated: If true, runner is deregistering itself (immediate removal)
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

@app.post("/runs")
async def create_run(run_create: RunCreate):
    """Create a new run for the runner to execute.

    If session_id is not provided, coordinator generates one (ADR-010).
    Returns both run_id and session_id in the response.

    Demands are merged from blueprint (if agent_name provided) and additional_demands.
    See ADR-011 for demand matching logic.
    """
    # Create the run (session_id generated if not provided)
    run = run_queue.add_run(run_create)

    # For start runs, create session record immediately with status=pending (ADR-010)
    if run_create.type == RunType.START_SESSION:
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            create_session(
                session_id=run.session_id,
                timestamp=timestamp,
                status="pending",
                project_dir=run_create.project_dir,
                agent_name=run_create.agent_name,
                parent_session_id=run_create.parent_session_id,
                execution_mode=run.execution_mode.value,
            )
            if DEBUG:
                print(f"[DEBUG] Created pending session {run.session_id} for run {run.run_id} (mode={run.execution_mode.value})", flush=True)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                # Session already exists - this shouldn't happen for start runs
                raise HTTPException(
                    status_code=409,
                    detail=f"Session '{run.session_id}' already exists"
                )
            raise

    # Merge demands from blueprint and additional_demands (ADR-011)
    merged_demands = None
    blueprint_demands = RunnerDemands()  # Empty defaults
    additional_demands = RunnerDemands()  # Empty defaults

    # Load blueprint demands if agent_name provided
    if run_create.agent_name:
        agent = agent_storage.get_agent(run_create.agent_name)
        if agent and agent.demands:
            blueprint_demands = agent.demands

    # Parse additional_demands from request
    if run_create.additional_demands:
        additional_demands = RunnerDemands(**run_create.additional_demands)

    # Merge demands (blueprint takes precedence, additional is additive)
    merged_demands = RunnerDemands.merge(blueprint_demands, additional_demands)

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


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get run status and details."""
    run = run_queue.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return run.model_dump()


@app.post("/runs/{run_id}/stop")
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