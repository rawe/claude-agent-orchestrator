"""
Fake Runner Gateway

HTTP server that simulates the Runner Gateway for testing.
Records all calls for assertions and returns configurable responses.

Endpoints:
- POST /bind          - Bind executor to session
- POST /events        - Add event to session
- PATCH /metadata     - Update session metadata
- GET /sessions/{id}  - Get session (for resume)
"""

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse


@dataclass
class GatewayCall:
    """Recorded gateway call."""
    timestamp: str
    method: str
    path: str
    body: dict | None = None
    response_code: int = 200
    response_body: dict | None = None


@dataclass
class SessionState:
    """State for a session (used for resume tests)."""
    session_id: str
    executor_session_id: str | None = None
    project_dir: str | None = None
    agent_name: str | None = None
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_resumed_at: str | None = None


class FakeRunnerGateway:
    """
    Fake Runner Gateway server for testing.

    Usage:
        gateway = FakeRunnerGateway()
        gateway.start()
        url = gateway.url  # e.g., "http://127.0.0.1:54321"

        # Run executor tests...

        calls = gateway.get_calls()
        gateway.stop()
    """

    def __init__(self, port: int = 0):
        """
        Initialize fake gateway.

        Args:
            port: Port to listen on (0 = random available port)
        """
        self._port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._calls: list[GatewayCall] = []
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.Lock()

    @property
    def url(self) -> str:
        """Get the gateway URL."""
        if self._server is None:
            raise RuntimeError("Gateway not started")
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    @property
    def port(self) -> int:
        """Get the gateway port."""
        if self._server is None:
            raise RuntimeError("Gateway not started")
        return self._server.server_address[1]

    def start(self) -> str:
        """Start the gateway server. Returns the URL."""
        handler = self._create_handler()
        self._server = HTTPServer(("127.0.0.1", self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()
        return self.url

    def stop(self):
        """Stop the gateway server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def get_calls(self) -> list[GatewayCall]:
        """Get all recorded calls."""
        with self._lock:
            return list(self._calls)

    def get_calls_by_path(self, path: str) -> list[GatewayCall]:
        """Get calls matching a path prefix."""
        with self._lock:
            return [c for c in self._calls if c.path.startswith(path)]

    def get_bind_calls(self) -> list[GatewayCall]:
        """Get all /bind calls."""
        return self.get_calls_by_path("/bind")

    def get_event_calls(self) -> list[GatewayCall]:
        """Get all /events calls."""
        return self.get_calls_by_path("/events")

    def get_events_for_session(self, session_id: str) -> list[dict]:
        """Get all events for a specific session."""
        events = []
        for call in self.get_event_calls():
            if call.body and call.body.get("session_id") == session_id:
                events.append(call.body)
        return events

    def get_session(self, session_id: str) -> SessionState | None:
        """Get session state."""
        with self._lock:
            return self._sessions.get(session_id)

    def set_session(self, session: SessionState):
        """Pre-configure a session (for resume tests)."""
        with self._lock:
            self._sessions[session.session_id] = session

    def clear(self):
        """Clear all recorded calls and sessions."""
        with self._lock:
            self._calls.clear()
            self._sessions.clear()

    def _record_call(self, call: GatewayCall):
        """Record a call (thread-safe)."""
        with self._lock:
            self._calls.append(call)

    def _get_or_create_session(self, session_id: str) -> SessionState:
        """Get or create a session (thread-safe)."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionState(session_id=session_id)
            return self._sessions[session_id]

    def _update_session(self, session_id: str, **kwargs) -> SessionState:
        """Update session fields (thread-safe)."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
            return session

    def _create_handler(self):
        """Create request handler with access to gateway instance."""
        gateway = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Suppress default logging
                pass

            def _send_json(self, data: dict, status: int = 200):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def _read_body(self) -> dict | None:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)
                    return json.loads(body.decode())
                return None

            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path

                # GET /sessions/{session_id}
                if path.startswith("/sessions/"):
                    session_id = path.split("/")[-1]
                    session = gateway.get_session(session_id)

                    if session:
                        response = {
                            "session": {
                                "session_id": session.session_id,
                                "executor_session_id": session.executor_session_id,
                                "project_dir": session.project_dir,
                                "agent_name": session.agent_name,
                                "status": session.status,
                            }
                        }
                        gateway._record_call(GatewayCall(
                            timestamp=datetime.now(UTC).isoformat(),
                            method="GET",
                            path=path,
                            response_code=200,
                            response_body=response,
                        ))
                        self._send_json(response)
                    else:
                        gateway._record_call(GatewayCall(
                            timestamp=datetime.now(UTC).isoformat(),
                            method="GET",
                            path=path,
                            response_code=404,
                        ))
                        self._send_json({"error": "Session not found"}, 404)
                else:
                    self._send_json({"error": "Not found"}, 404)

            def do_POST(self):
                parsed = urlparse(self.path)
                path = parsed.path
                body = self._read_body()

                # POST /bind
                if path == "/bind":
                    session_id = body.get("session_id")
                    executor_session_id = body.get("executor_session_id")
                    project_dir = body.get("project_dir")

                    session = gateway._get_or_create_session(session_id)
                    gateway._update_session(
                        session_id,
                        executor_session_id=executor_session_id,
                        project_dir=project_dir,
                        status="running",
                    )

                    response = {
                        "session": {
                            "session_id": session_id,
                            "executor_session_id": executor_session_id,
                        }
                    }
                    gateway._record_call(GatewayCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                        response_code=200,
                        response_body=response,
                    ))
                    self._send_json(response)

                # POST /events
                elif path == "/events":
                    session_id = body.get("session_id")
                    gateway._record_call(GatewayCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                        response_code=200,
                    ))
                    self._send_json({"status": "ok"})

                else:
                    self._send_json({"error": "Not found"}, 404)

            def do_PATCH(self):
                parsed = urlparse(self.path)
                path = parsed.path
                body = self._read_body()

                # PATCH /metadata
                if path == "/metadata":
                    session_id = body.get("session_id")
                    last_resumed_at = body.get("last_resumed_at")
                    executor_session_id = body.get("executor_session_id")

                    updates = {}
                    if last_resumed_at:
                        updates["last_resumed_at"] = last_resumed_at
                    if executor_session_id:
                        updates["executor_session_id"] = executor_session_id

                    gateway._update_session(session_id, **updates)

                    response = {"session": {"session_id": session_id}}
                    gateway._record_call(GatewayCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="PATCH",
                        path=path,
                        body=body,
                        response_code=200,
                        response_body=response,
                    ))
                    self._send_json(response)

                else:
                    self._send_json({"error": "Not found"}, 404)

        return Handler


# Convenience for testing the gateway directly
if __name__ == "__main__":
    gateway = FakeRunnerGateway(port=8765)
    print(f"Starting fake gateway on {gateway.start()}")
    try:
        input("Press Enter to stop...")
    finally:
        gateway.stop()
