from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import json
import os

from database import init_db, insert_session, insert_event, get_sessions, get_events, update_session_status
from models import Event

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
    title="Agent Orchestrator Observability",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/events")
async def receive_event(event: Event):
    """Receive events from hook scripts and broadcast to WebSocket clients"""

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

@app.get("/events/{session_id}")
async def list_events(session_id: str):
    """Get events for a specific session"""
    return {"events": get_events(session_id)}

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
