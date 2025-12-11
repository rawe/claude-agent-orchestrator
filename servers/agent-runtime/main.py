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
    create_session, get_session_by_id, get_session_result, get_session_by_name,
    update_session_parent
)
from models import (
    Event, SessionMetadataUpdate, SessionCreate,
    Agent, AgentCreate, AgentUpdate, AgentStatusUpdate
)
import agent_storage
from validation import validate_agent_name
from datetime import datetime, timezone

# Import job queue and launcher registry services
from services.job_queue import job_queue, JobCreate, Job, JobStatus
from services.launcher_registry import launcher_registry, LauncherInfo
from services import callback_processor

# Debug logging toggle - set DEBUG_LOGGING=true to enable verbose output
DEBUG = os.getenv("DEBUG_LOGGING", "").lower() in ("true", "1", "yes")

# Launcher configuration
LAUNCHER_POLL_TIMEOUT = int(os.getenv("LAUNCHER_POLL_TIMEOUT", "30"))
LAUNCHER_HEARTBEAT_INTERVAL = int(os.getenv("LAUNCHER_HEARTBEAT_INTERVAL", "60"))
LAUNCHER_HEARTBEAT_TIMEOUT = int(os.getenv("LAUNCHER_HEARTBEAT_TIMEOUT", "120"))

# WebSocket connections (in-memory set)
connections: set[WebSocket] = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    init_db()
    yield
    # Close all connections
    for ws in connections.copy():
        try:
            await ws.close()
        except:
            pass

app = FastAPI(
    title="Agent Runtime",
    description="Unified service for agent session management and agent blueprint registry",
    version="0.2.0",
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

    DEPRECATION NOTE: The session_start event handling below will be removed
    once all clients migrate to POST /sessions for session creation.
    The session_stop handling will also migrate to POST /sessions/{id}/events.
    Keep backward compatibility during migration.
    """

    # Debug: Log incoming event
    if DEBUG:
        print(f"[DEBUG] Received event: type={event.event_type}, session_id={event.session_id}", flush=True)
        print(f"[DEBUG] Event data: {event.dict()}", flush=True)

    try:
        # Update database
        if event.event_type == "session_start":
            insert_session(event.session_id, event.session_name, event.timestamp)
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
        message = json.dumps({"type": "event", "data": event.dict()})
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
        print(f"[ERROR] Event that failed: {event.dict()}", flush=True)
        raise

@app.get("/sessions")
async def list_sessions():
    """Get all sessions"""
    return {"sessions": get_sessions()}


@app.post("/sessions")
async def create_session_endpoint(session: SessionCreate):
    """Create a new session with full metadata"""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Determine parent_session_name: prefer job's value over request's value
    parent_session_name = session.parent_session_name

    # Check if there's a running/claimed job for this session_name
    job = job_queue.get_job_by_session_name(session.session_name)
    if job and job.parent_session_name:
        parent_session_name = job.parent_session_name
        if DEBUG:
            print(f"[DEBUG] Session {session.session_name} inheriting parent {parent_session_name} from job {job.job_id}", flush=True)

    try:
        new_session = create_session(
            session_id=session.session_id,
            session_name=session.session_name,
            timestamp=timestamp,
            project_dir=session.project_dir,
            agent_name=session.agent_name,
            parent_session_name=parent_session_name,
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


@app.get("/sessions/by-name/{session_name}")
async def get_session_by_name_endpoint(session_name: str):
    """Get session by session_name"""
    session = get_session_by_name(session_name)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session}


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
        session_name = updated_session.get("session_name")
        parent_session_name = updated_session.get("parent_session_name")

        if parent_session_name:
            # This is a child session completing - notify parent
            parent_session = get_session_by_name(parent_session_name)
            parent_status = parent_session["status"] if parent_session else "not_found"

            # Get the child's result
            child_result = get_session_result(session_id)

            if DEBUG:
                print(f"[DEBUG] Child '{session_name}' completed, parent '{parent_session_name}' status={parent_status}", flush=True)

            callback_processor.on_child_completed(
                child_session_name=session_name,
                parent_session_name=parent_session_name,
                parent_status=parent_status,
                child_result=child_result,
            )

        # Check if this session has pending child callbacks to flush
        project_dir = updated_session.get("project_dir")
        flushed = callback_processor.on_session_stopped(session_name, project_dir)
        if flushed > 0 and DEBUG:
            print(f"[DEBUG] Flushed {flushed} pending callbacks for '{session_name}'", flush=True)

    # Broadcast event to WebSocket clients
    message = json.dumps({"type": "event", "data": event.dict()})
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
    """Update session metadata (name, project_dir, agent_name)"""

    # Verify session exists
    sessions = get_sessions()
    if not any(s['session_id'] == session_id for s in sessions):
        raise HTTPException(status_code=404, detail="Session not found")

    # Update metadata
    update_session_metadata(
        session_id=session_id,
        session_name=metadata.session_name,
        project_dir=metadata.project_dir,
        agent_name=metadata.agent_name,
        last_resumed_at=metadata.last_resumed_at
    )

    # Broadcast update to WebSocket clients
    updated_sessions = get_sessions()
    updated_session = next(s for s in updated_sessions if s['session_id'] == session_id)

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
# Launcher API Routes (for Agent Launcher communication)
# ==============================================================================

class LauncherRegisterRequest(BaseModel):
    """Request body for launcher registration with metadata."""
    hostname: str | None = None
    project_dir: str | None = None


class LauncherRegisterResponse(BaseModel):
    """Response from launcher registration."""
    launcher_id: str
    poll_endpoint: str
    poll_timeout_seconds: int
    heartbeat_interval_seconds: int


class LauncherIdRequest(BaseModel):
    """Request body containing launcher_id."""
    launcher_id: str


class JobCompletedRequest(BaseModel):
    """Request body for job completion."""
    launcher_id: str
    status: str = "success"


class JobFailedRequest(BaseModel):
    """Request body for job failure."""
    launcher_id: str
    error: str


@app.post("/launcher/register")
async def register_launcher(request: LauncherRegisterRequest | None = None):
    """Register a new launcher instance.

    Accepts optional metadata about the launcher (hostname, project_dir).
    Returns launcher_id and configuration for polling.
    """
    # Handle both empty body and JSON body
    hostname = request.hostname if request else None
    project_dir = request.project_dir if request else None

    launcher = launcher_registry.register_launcher(
        hostname=hostname,
        project_dir=project_dir,
    )

    if DEBUG:
        print(f"[DEBUG] Registered new launcher: {launcher.launcher_id}", flush=True)
        if hostname:
            print(f"[DEBUG]   hostname: {hostname}", flush=True)
        if project_dir:
            print(f"[DEBUG]   project_dir: {project_dir}", flush=True)

    return LauncherRegisterResponse(
        launcher_id=launcher.launcher_id,
        poll_endpoint="/launcher/jobs",
        poll_timeout_seconds=LAUNCHER_POLL_TIMEOUT,
        heartbeat_interval_seconds=LAUNCHER_HEARTBEAT_INTERVAL,
    )


@app.get("/launcher/jobs")
async def poll_for_jobs(launcher_id: str = Query(..., description="The registered launcher ID")):
    """Long-poll for available jobs.

    Holds the connection open for up to LAUNCHER_POLL_TIMEOUT seconds,
    returning immediately if a job is available.
    Returns 204 No Content if no jobs available after timeout.
    Returns {"deregistered": true} if launcher has been deregistered.
    """
    # Check if launcher has been deregistered
    if launcher_registry.is_deregistered(launcher_id):
        # Confirm deregistration and remove from registry
        launcher_registry.confirm_deregistered(launcher_id)
        if DEBUG:
            print(f"[DEBUG] Launcher {launcher_id} deregistered, signaling shutdown", flush=True)
        return {"deregistered": True}

    # Verify launcher is registered
    if not launcher_registry.get_launcher(launcher_id):
        raise HTTPException(status_code=401, detail="Launcher not registered")

    # Poll for jobs with timeout
    poll_interval = 0.5  # Check every 500ms
    elapsed = 0.0

    while elapsed < LAUNCHER_POLL_TIMEOUT:
        # Check for deregistration during polling
        if launcher_registry.is_deregistered(launcher_id):
            launcher_registry.confirm_deregistered(launcher_id)
            if DEBUG:
                print(f"[DEBUG] Launcher {launcher_id} deregistered during poll, signaling shutdown", flush=True)
            return {"deregistered": True}

        job = job_queue.claim_job(launcher_id)
        if job:
            if DEBUG:
                print(f"[DEBUG] Launcher {launcher_id} claimed job {job.job_id}", flush=True)
            return {"job": job.model_dump()}

        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    # No jobs available after timeout
    return Response(status_code=204)


@app.post("/launcher/jobs/{job_id}/started")
async def report_job_started(job_id: str, request: LauncherIdRequest):
    """Report that job execution has started."""
    # Verify launcher
    if not launcher_registry.get_launcher(request.launcher_id):
        raise HTTPException(status_code=401, detail="Launcher not registered")

    # Get job first to access parent_session_name
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update job status to running
    job = job_queue.update_job_status(job_id, JobStatus.RUNNING)

    # Link job's parent_session_name to session (for resume case where session already exists)
    if job.parent_session_name:
        session = get_session_by_name(job.session_name)
        if session:
            # Session exists (resume case) - update parent
            update_session_parent(session["session_id"], job.parent_session_name)
            if DEBUG:
                print(f"[DEBUG] Updated session {job.session_name} parent to {job.parent_session_name}", flush=True)
        # If session doesn't exist yet (start case), POST /sessions will pick up parent from job

    if DEBUG:
        print(f"[DEBUG] Job {job_id} started by launcher {request.launcher_id}", flush=True)

    return {"ok": True}


@app.post("/launcher/jobs/{job_id}/completed")
async def report_job_completed(job_id: str, request: JobCompletedRequest):
    """Report that job completed successfully."""
    # Verify launcher
    if not launcher_registry.get_launcher(request.launcher_id):
        raise HTTPException(status_code=401, detail="Launcher not registered")

    job = job_queue.update_job_status(job_id, JobStatus.COMPLETED)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if DEBUG:
        print(f"[DEBUG] Job {job_id} completed by launcher {request.launcher_id}", flush=True)

    return {"ok": True}


@app.post("/launcher/jobs/{job_id}/failed")
async def report_job_failed(job_id: str, request: JobFailedRequest):
    """Report that job execution failed."""
    # Verify launcher
    if not launcher_registry.get_launcher(request.launcher_id):
        raise HTTPException(status_code=401, detail="Launcher not registered")

    job = job_queue.update_job_status(job_id, JobStatus.FAILED, error=request.error)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if DEBUG:
        print(f"[DEBUG] Job {job_id} failed: {request.error}", flush=True)

    return {"ok": True}


@app.post("/launcher/heartbeat")
async def launcher_heartbeat(request: LauncherIdRequest):
    """Keep launcher registration alive."""
    if not launcher_registry.heartbeat(request.launcher_id):
        raise HTTPException(status_code=401, detail="Launcher not registered")

    return {"ok": True}


class LauncherWithStatus(BaseModel):
    """Launcher info with computed status fields."""
    launcher_id: str
    registered_at: str
    last_heartbeat: str
    hostname: str | None = None
    project_dir: str | None = None
    status: str  # "online", "stale", or "offline"
    seconds_since_heartbeat: float


@app.get("/launchers")
async def list_launchers():
    """List all registered launchers with their status.

    Returns all launchers with status:
    - "online": heartbeat within last 2 minutes
    - "stale": no heartbeat for 2+ minutes (connection may be lost)
    - "offline": launcher has deregistered or been removed
    """
    launchers = launcher_registry.get_all_launchers()
    result = []

    for launcher in launchers:
        seconds = launcher_registry.get_seconds_since_heartbeat(launcher.launcher_id)
        if seconds is None:
            continue  # Shouldn't happen, but skip if it does

        # Determine status based on heartbeat age
        if seconds < LAUNCHER_HEARTBEAT_TIMEOUT:
            status = "online"
        else:
            status = "stale"

        result.append(LauncherWithStatus(
            launcher_id=launcher.launcher_id,
            registered_at=launcher.registered_at,
            last_heartbeat=launcher.last_heartbeat,
            hostname=launcher.hostname,
            project_dir=launcher.project_dir,
            status=status,
            seconds_since_heartbeat=seconds,
        ))

    return {"launchers": result}


@app.delete("/launchers/{launcher_id}")
async def deregister_launcher(
    launcher_id: str,
    self_initiated: bool = Query(False, alias="self", description="True if launcher is deregistering itself"),
):
    """Deregister a launcher.

    Two modes:
    - External (dashboard): Marks launcher for deregistration, signals on next poll
    - Self-initiated (launcher shutdown): Immediately removes from registry

    Args:
        launcher_id: The launcher to deregister
        self_initiated: If true, launcher is deregistering itself (immediate removal)
    """
    # Check if launcher exists
    if not launcher_registry.get_launcher(launcher_id):
        raise HTTPException(status_code=404, detail="Launcher not found")

    if self_initiated:
        # Launcher is shutting down gracefully - remove immediately
        launcher_registry.remove_launcher(launcher_id)
        if DEBUG:
            print(f"[DEBUG] Launcher {launcher_id} self-deregistered (graceful shutdown)", flush=True)
        return {"ok": True, "message": "Launcher deregistered", "initiated_by": "self"}
    else:
        # External request (dashboard) - mark for deregistration, signal on next poll
        launcher_registry.mark_deregistered(launcher_id)
        if DEBUG:
            print(f"[DEBUG] Launcher {launcher_id} marked for deregistration (external request)", flush=True)
        return {"ok": True, "message": "Launcher marked for deregistration", "initiated_by": "external"}


# ==============================================================================
# Jobs API Routes (for creating and querying jobs)
# ==============================================================================

@app.post("/jobs")
async def create_job(job_create: JobCreate):
    """Create a new job for the launcher to execute.

    Used by Dashboard and future ao-start to queue work.
    """
    job = job_queue.add_job(job_create)

    if DEBUG:
        print(f"[DEBUG] Created job {job.job_id}: type={job.type}, session={job.session_name}", flush=True)

    return {"job_id": job.job_id, "status": job.status}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status and details."""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job.model_dump()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # Bind to all interfaces for Docker
        port=8765,
        reload=True,
        log_level="info"
    )
