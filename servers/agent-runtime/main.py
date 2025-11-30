from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import json
import os

from database import (
    init_db, insert_session, insert_event, get_sessions, get_events,
    update_session_status, update_session_metadata, delete_session,
    create_session, get_session_by_id, get_session_result
)
from models import Event, SessionMetadataUpdate, SessionCreate
from datetime import datetime, timezone

# Debug logging toggle - set DEBUG_LOGGING=true to enable verbose output
DEBUG = os.getenv("DEBUG_LOGGING", "").lower() in ("true", "1", "yes")

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
    version="0.1.0",
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

    try:
        new_session = create_session(
            session_id=session.session_id,
            session_name=session.session_name,
            timestamp=timestamp,
            project_dir=session.project_dir,
            agent_name=session.agent_name
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
        agent_name=metadata.agent_name
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # Bind to all interfaces for Docker
        port=8765,
        reload=True,
        log_level="info"
    )
