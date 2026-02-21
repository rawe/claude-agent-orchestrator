"""
Fake Coordinator - HTTP server implementing the Runner API.

Pattern mirrors FakeRunnerGateway but serves runs to runners.
Used for testing runner components (poller, supervisor, API client)
without a real coordinator.

Endpoints:
- POST /runner/register         - Register runner
- GET  /runner/runs             - Long-poll for next run
- POST /runner/runs/{id}/started    - Mark run started
- POST /runner/runs/{id}/completed  - Mark run completed
- POST /runner/runs/{id}/failed     - Mark run failed
- POST /runner/runs/{id}/stopped    - Mark run stopped
- POST /runner/heartbeat            - Heartbeat
- DELETE /runners/{id}              - Deregister
- POST /runner/sessions/{id}/status - Report session status
- GET  /sessions/{id}               - Get session
- GET  /sessions/{id}/bind          - Bind (forwarded from gateway)
- POST /sessions/{id}/bind          - Bind session
- POST /sessions/{id}/events        - Record events
- PATCH /sessions/{id}/metadata     - Update metadata
"""

import json
import queue
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, UTC
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs


@dataclass
class FakeCall:
    """Recorded API call."""
    timestamp: str
    method: str
    path: str
    body: dict | None = None
    query: dict | None = None
    response_code: int = 200
    response_body: dict | None = None


@dataclass
class RunReport:
    """Status report for a run."""
    type: str  # started, completed, failed, stopped
    runner_id: str
    run_id: str
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class FakeCoordinator:
    """
    Fake HTTP server implementing the Runner API.

    Usage:
        coordinator = FakeCoordinator()
        coordinator.start()

        # Queue a run for the poller
        coordinator.enqueue_run({
            "run": {
                "run_id": "run_001",
                "type": "start_session",
                "session_id": "ses_001",
                "parameters": {"prompt": "hello"},
            }
        })

        # ... runner claims and executes ...

        # Check what was reported
        assert coordinator.get_final_status("run_001") == "completed"

        coordinator.stop()
    """

    def __init__(self, poll_timeout: float = 0.5):
        self._poll_timeout = poll_timeout
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

        # Pre-queued poll responses (consumed by GET /runner/runs)
        self._poll_queue: queue.Queue = queue.Queue()

        # Recorded calls for assertions
        self._calls: list[FakeCall] = []
        self._lock = threading.Lock()

        # Run status tracking
        self._run_reports: dict[str, list[RunReport]] = {}

        # Session status tracking
        self._session_statuses: dict[str, list[dict]] = {}

        # Registration tracking
        self._registered_runners: dict[str, dict] = {}

        # Heartbeat tracking
        self._heartbeats: list[dict] = []

        # Registration config
        self._runner_id = "lnch_test12345"
        self._poll_timeout_seconds = 1
        self._heartbeat_interval_seconds = 60

        # Configurable error responses
        self._register_error: tuple[int, dict] | None = None

        # Events and bind tracking (for gateway forwarding tests)
        self._bind_calls: list[dict] = []
        self._event_calls: list[dict] = []
        self._metadata_calls: list[dict] = []

    def configure_registration(
        self,
        runner_id: str = "lnch_test12345",
        poll_timeout_seconds: int = 1,
        heartbeat_interval_seconds: int = 60,
    ):
        """Configure registration response."""
        self._runner_id = runner_id
        self._poll_timeout_seconds = poll_timeout_seconds
        self._heartbeat_interval_seconds = heartbeat_interval_seconds

    def set_register_error(self, status_code: int, response: dict):
        """Configure registration to return an error."""
        self._register_error = (status_code, response)

    def clear_register_error(self):
        """Clear registration error."""
        self._register_error = None

    def enqueue_run(self, run_data: dict):
        """Queue a run response for the next poll."""
        self._poll_queue.put(("run", run_data))

    def enqueue_stop_sessions(self, session_ids: list[str]):
        """Queue stop commands for the next poll."""
        self._poll_queue.put(("stop", {"stop_sessions": session_ids}))

    def enqueue_deregistered(self):
        """Queue a deregistration signal for the next poll."""
        self._poll_queue.put(("deregistered", {"deregistered": True}))

    def enqueue_script_sync(self, sync: list[str] = None, remove: list[str] = None):
        """Queue script sync commands for the next poll."""
        data = {}
        if sync:
            data["sync_scripts"] = sync
        if remove:
            data["remove_scripts"] = remove
        self._poll_queue.put(("scripts", data))

    def get_calls(self) -> list[FakeCall]:
        """Get all recorded calls."""
        with self._lock:
            return list(self._calls)

    def get_calls_by_path(self, path_prefix: str) -> list[FakeCall]:
        """Get calls matching a path prefix."""
        with self._lock:
            return [c for c in self._calls if c.path.startswith(path_prefix)]

    def get_run_reports(self, run_id: str) -> list[RunReport]:
        """Get all status reports for a run."""
        with self._lock:
            return list(self._run_reports.get(run_id, []))

    def get_final_status(self, run_id: str) -> str | None:
        """Get final status reported for a run."""
        reports = self.get_run_reports(run_id)
        terminal = [r for r in reports if r.type in ("completed", "failed", "stopped")]
        return terminal[-1].type if terminal else None

    def get_session_statuses(self, session_id: str) -> list[dict]:
        """Get all session status reports."""
        with self._lock:
            return list(self._session_statuses.get(session_id, []))

    def get_heartbeats(self) -> list[dict]:
        """Get all heartbeat calls."""
        with self._lock:
            return list(self._heartbeats)

    def get_registered_runners(self) -> dict[str, dict]:
        """Get all registered runners."""
        with self._lock:
            return dict(self._registered_runners)

    def get_bind_calls(self) -> list[dict]:
        """Get all bind calls forwarded from gateway."""
        with self._lock:
            return list(self._bind_calls)

    def get_event_calls(self) -> list[dict]:
        """Get all event calls."""
        with self._lock:
            return list(self._event_calls)

    def get_metadata_calls(self) -> list[dict]:
        """Get all metadata calls."""
        with self._lock:
            return list(self._metadata_calls)

    def clear(self):
        """Clear all recorded state."""
        with self._lock:
            self._calls.clear()
            self._run_reports.clear()
            self._session_statuses.clear()
            self._registered_runners.clear()
            self._heartbeats.clear()
            self._bind_calls.clear()
            self._event_calls.clear()
            self._metadata_calls.clear()
        # Drain poll queue
        while not self._poll_queue.empty():
            try:
                self._poll_queue.get_nowait()
            except queue.Empty:
                break

    @property
    def url(self) -> str:
        if self._server is None:
            raise RuntimeError("Server not started")
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def start(self) -> str:
        """Start server, return URL."""
        handler = self._create_handler()
        self._server = HTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()
        return self.url

    def stop(self):
        """Stop server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _record_call(self, call: FakeCall):
        with self._lock:
            self._calls.append(call)

    def _record_run_report(self, report: RunReport):
        with self._lock:
            if report.run_id not in self._run_reports:
                self._run_reports[report.run_id] = []
            self._run_reports[report.run_id].append(report)

    def _create_handler(self):
        coordinator = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress logging

            def _send_json(self, data: dict, status: int = 200):
                body = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_empty(self, status: int = 204):
                self.send_response(status)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def _read_body(self) -> dict | None:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)
                    return json.loads(body.decode())
                return None

            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path
                query = parse_qs(parsed.query)

                # GET /runner/runs - long-poll
                if path == "/runner/runs":
                    runner_id = query.get("runner_id", [None])[0]
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="GET",
                        path=path,
                        query={"runner_id": runner_id},
                    ))

                    try:
                        msg_type, data = coordinator._poll_queue.get(
                            timeout=coordinator._poll_timeout
                        )
                        self._send_json(data)
                    except queue.Empty:
                        self._send_empty(204)
                    return

                # GET /sessions/{id}
                m = re.match(r"^/sessions/([^/]+)$", path)
                if m:
                    session_id = m.group(1)
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="GET",
                        path=path,
                    ))
                    self._send_json({"session": {"session_id": session_id, "status": "running"}})
                    return

                # GET /sessions/{id}/affinity
                m = re.match(r"^/sessions/([^/]+)/affinity$", path)
                if m:
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="GET",
                        path=path,
                    ))
                    self._send_json({"affinity": {}})
                    return

                self._send_json({"error": "Not found"}, 404)

            def do_POST(self):
                parsed = urlparse(self.path)
                path = parsed.path
                body = self._read_body()

                # POST /runner/register
                if path == "/runner/register":
                    if coordinator._register_error:
                        status, resp = coordinator._register_error
                        coordinator._record_call(FakeCall(
                            timestamp=datetime.now(UTC).isoformat(),
                            method="POST",
                            path=path,
                            body=body,
                            response_code=status,
                            response_body=resp,
                        ))
                        self._send_json(resp, status)
                        return

                    runner_id = coordinator._runner_id
                    with coordinator._lock:
                        coordinator._registered_runners[runner_id] = body or {}

                    response = {
                        "runner_id": runner_id,
                        "poll_endpoint": f"/runner/runs?runner_id={runner_id}",
                        "poll_timeout_seconds": coordinator._poll_timeout_seconds,
                        "heartbeat_interval_seconds": coordinator._heartbeat_interval_seconds,
                    }
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                        response_code=200,
                        response_body=response,
                    ))
                    self._send_json(response)
                    return

                # POST /runner/heartbeat
                if path == "/runner/heartbeat":
                    with coordinator._lock:
                        coordinator._heartbeats.append(body or {})
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                    ))
                    self._send_json({"status": "ok"})
                    return

                # POST /runner/runs/{id}/started
                m = re.match(r"^/runner/runs/([^/]+)/started$", path)
                if m:
                    run_id = m.group(1)
                    coordinator._record_run_report(RunReport(
                        type="started",
                        runner_id=(body or {}).get("runner_id", ""),
                        run_id=run_id,
                        data=body or {},
                    ))
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                    ))
                    self._send_json({"status": "ok"})
                    return

                # POST /runner/runs/{id}/completed
                m = re.match(r"^/runner/runs/([^/]+)/completed$", path)
                if m:
                    run_id = m.group(1)
                    coordinator._record_run_report(RunReport(
                        type="completed",
                        runner_id=(body or {}).get("runner_id", ""),
                        run_id=run_id,
                        data=body or {},
                    ))
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                    ))
                    self._send_json({"status": "ok"})
                    return

                # POST /runner/runs/{id}/failed
                m = re.match(r"^/runner/runs/([^/]+)/failed$", path)
                if m:
                    run_id = m.group(1)
                    coordinator._record_run_report(RunReport(
                        type="failed",
                        runner_id=(body or {}).get("runner_id", ""),
                        run_id=run_id,
                        data=body or {},
                    ))
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                    ))
                    self._send_json({"status": "ok"})
                    return

                # POST /runner/runs/{id}/stopped
                m = re.match(r"^/runner/runs/([^/]+)/stopped$", path)
                if m:
                    run_id = m.group(1)
                    coordinator._record_run_report(RunReport(
                        type="stopped",
                        runner_id=(body or {}).get("runner_id", ""),
                        run_id=run_id,
                        data=body or {},
                    ))
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                    ))
                    self._send_json({"status": "ok"})
                    return

                # POST /runner/sessions/{id}/status
                m = re.match(r"^/runner/sessions/([^/]+)/status$", path)
                if m:
                    session_id = m.group(1)
                    with coordinator._lock:
                        if session_id not in coordinator._session_statuses:
                            coordinator._session_statuses[session_id] = []
                        coordinator._session_statuses[session_id].append(body or {})
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                    ))
                    self._send_json({"status": "ok"})
                    return

                # POST /sessions/{id}/bind (from gateway forwarding)
                m = re.match(r"^/sessions/([^/]+)/bind$", path)
                if m:
                    session_id = m.group(1)
                    with coordinator._lock:
                        coordinator._bind_calls.append({"session_id": session_id, **(body or {})})
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                    ))
                    self._send_json({"session": {"session_id": session_id, "status": "running"}})
                    return

                # POST /sessions/{id}/events (from gateway forwarding)
                m = re.match(r"^/sessions/([^/]+)/events$", path)
                if m:
                    session_id = m.group(1)
                    with coordinator._lock:
                        coordinator._event_calls.append({"session_id": session_id, **(body or {})})
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="POST",
                        path=path,
                        body=body,
                    ))
                    self._send_json({"status": "ok"})
                    return

                self._send_json({"error": "Not found"}, 404)

            def do_PATCH(self):
                parsed = urlparse(self.path)
                path = parsed.path
                body = self._read_body()

                # PATCH /sessions/{id}/metadata
                m = re.match(r"^/sessions/([^/]+)/metadata$", path)
                if m:
                    session_id = m.group(1)
                    with coordinator._lock:
                        coordinator._metadata_calls.append({"session_id": session_id, **(body or {})})
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="PATCH",
                        path=path,
                        body=body,
                    ))
                    self._send_json({"session": {"session_id": session_id}})
                    return

                self._send_json({"error": "Not found"}, 404)

            def do_DELETE(self):
                parsed = urlparse(self.path)
                path = parsed.path
                query = parse_qs(parsed.query)

                # DELETE /runners/{id}
                m = re.match(r"^/runners/([^/]+)$", path)
                if m:
                    runner_id = m.group(1)
                    is_self = query.get("self", [""])[0] == "true"
                    with coordinator._lock:
                        coordinator._registered_runners.pop(runner_id, None)
                    coordinator._record_call(FakeCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        method="DELETE",
                        path=path,
                        query={"self": str(is_self).lower()},
                    ))
                    self._send_json({"status": "ok"})
                    return

                self._send_json({"error": "Not found"}, 404)

        return Handler
