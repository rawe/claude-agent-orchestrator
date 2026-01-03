"""
Runner Gateway

Local HTTP server that acts as the interface between executors and the Agent Coordinator.
Executors communicate only with the Runner Gateway, not directly with the Coordinator.

The gateway:
- Handles executor operations locally, enriching with runner-owned data
- Forwards enriched requests to the Agent Coordinator
- Injects Authorization headers using Auth0 M2M tokens when configured
- Is localhost-only for security

Information ownership:
- Runner provides: hostname, executor_profile
- Executor provides: executor_session_id, project_dir

Note: project_dir is per-invocation (each executor instance can have different working
directories), so it's provided by the executor, not the runner.

Routes:
- POST /bind         - Bind executor to session (runner enriches with hostname, executor_profile)
- POST /events       - Add event to session (forwarded to coordinator)
- PATCH /metadata    - Update session metadata (runner enriches if needed)
- /* (other)         - Forward to coordinator as-is (health checks, etc.)

Usage:
    The Agent Runner starts this gateway before spawning executors and sets
    AGENT_ORCHESTRATOR_API_URL to the gateway URL. Executors use session_client
    which calls the gateway endpoints.
"""

import http.server
import json
import logging
import socketserver
import threading
import urllib.request
import urllib.error
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from auth0_client import Auth0M2MClient

logger = logging.getLogger(__name__)


class RunnerGatewayHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the Runner Gateway."""

    # Class-level configuration (set by RunnerGateway before starting)
    coordinator_url: str = ""
    auth0_client: Optional["Auth0M2MClient"] = None

    # Runner-owned data (injected into executor requests)
    hostname: str = ""
    executor_profile: str = ""

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger instead of stderr."""
        logger.debug(f"Gateway: {format % args}")

    def _get_auth_header(self) -> Optional[str]:
        """Get authorization header value from Auth0 M2M client."""
        if self.auth0_client and self.auth0_client.is_configured:
            token = self.auth0_client.get_access_token()
            if token:
                return f"Bearer {token}"
            logger.warning("Auth0 configured but failed to get token")
        return None

    def _read_body(self) -> Optional[bytes]:
        """Read request body if present."""
        content_length = self.headers.get("Content-Length")
        if content_length:
            return self.rfile.read(int(content_length))
        return None

    def _send_json_response(self, status: int, data: dict) -> None:
        """Send a JSON response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _call_coordinator(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
    ) -> tuple[int, dict]:
        """
        Call the Agent Coordinator API.

        Returns:
            Tuple of (status_code, response_dict)
        """
        target_url = f"{self.coordinator_url}{path}"

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        request = urllib.request.Request(target_url, method=method, data=data)

        # Add auth header
        auth_header = self._get_auth_header()
        if auth_header:
            request.add_header("Authorization", auth_header)

        # Add content-type for JSON
        if data:
            request.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = response.read()
                return response.status, json.loads(response_body) if response_body else {}
        except urllib.error.HTTPError as e:
            error_body = e.read()
            try:
                return e.code, json.loads(error_body)
            except json.JSONDecodeError:
                return e.code, {"detail": error_body.decode("utf-8", errors="replace")}
        except urllib.error.URLError as e:
            logger.error(f"Failed to connect to coordinator: {e}")
            return 502, {"detail": f"Failed to connect to Agent Coordinator: {e.reason}"}

    # =========================================================================
    # Runner-handled routes
    # =========================================================================

    def _handle_bind(self) -> None:
        """
        Handle POST /bind - Bind executor to session.

        Executor sends: {session_id, executor_session_id, project_dir?}
        Runner enriches with: hostname, executor_profile
        Forwards to: POST /sessions/{session_id}/bind
        """
        body = self._read_body()
        if not body:
            self._send_json_response(400, {"detail": "Request body required"})
            return

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            self._send_json_response(400, {"detail": f"Invalid JSON: {e}"})
            return

        # Validate required fields from executor
        session_id = data.get("session_id")
        executor_session_id = data.get("executor_session_id")

        if not session_id:
            self._send_json_response(400, {"detail": "session_id required"})
            return
        if not executor_session_id:
            self._send_json_response(400, {"detail": "executor_session_id required"})
            return

        # Build enriched payload with runner-owned data
        enriched_payload = {
            "executor_session_id": executor_session_id,
            "hostname": self.hostname,
            "executor_profile": self.executor_profile,
        }

        # Add project_dir if provided by executor (per-invocation, not runner-owned)
        project_dir = data.get("project_dir")
        if project_dir:
            enriched_payload["project_dir"] = project_dir

        logger.debug(
            f"Bind session {session_id}: executor_session_id={executor_session_id}, "
            f"hostname={self.hostname}, executor_profile={self.executor_profile}"
        )

        # Forward to coordinator
        status, response = self._call_coordinator(
            "POST",
            f"/sessions/{session_id}/bind",
            enriched_payload,
        )

        self._send_json_response(status, response)

    def _handle_events(self) -> None:
        """
        Handle POST /events - Add event to session.

        Executor sends: {session_id, event_type, ...event_data}
        Forwards to: POST /sessions/{session_id}/events

        Future: Could batch events, add runner context, etc.
        """
        body = self._read_body()
        if not body:
            self._send_json_response(400, {"detail": "Request body required"})
            return

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            self._send_json_response(400, {"detail": f"Invalid JSON: {e}"})
            return

        session_id = data.get("session_id")
        if not session_id:
            self._send_json_response(400, {"detail": "session_id required"})
            return

        # Forward event to coordinator (session_id is in both path and body)
        status, response = self._call_coordinator(
            "POST",
            f"/sessions/{session_id}/events",
            data,
        )

        self._send_json_response(status, response)

    def _handle_metadata(self) -> None:
        """
        Handle PATCH /metadata - Update session metadata.

        Executor sends: {session_id, last_resumed_at?, ...}
        Runner can enrich with: hostname, executor_profile if needed
        Forwards to: PATCH /sessions/{session_id}/metadata
        """
        body = self._read_body()
        if not body:
            self._send_json_response(400, {"detail": "Request body required"})
            return

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            self._send_json_response(400, {"detail": f"Invalid JSON: {e}"})
            return

        session_id = data.get("session_id")
        if not session_id:
            self._send_json_response(400, {"detail": "session_id required"})
            return

        # Build payload (remove session_id as it's in the path)
        payload = {k: v for k, v in data.items() if k != "session_id"}

        # Forward to coordinator
        status, response = self._call_coordinator(
            "PATCH",
            f"/sessions/{session_id}/metadata",
            payload,
        )

        self._send_json_response(status, response)

    # =========================================================================
    # HTTP method handlers
    # =========================================================================

    def do_GET(self) -> None:
        """Handle GET requests - forward to coordinator."""
        self._forward_to_coordinator("GET")

    def do_POST(self) -> None:
        """Handle POST requests - route or forward."""
        # Runner-handled routes
        if self.path == "/bind":
            return self._handle_bind()
        if self.path == "/events":
            return self._handle_events()

        # Forward everything else to coordinator
        self._forward_to_coordinator("POST")

    def do_PATCH(self) -> None:
        """Handle PATCH requests - route or forward."""
        if self.path == "/metadata":
            return self._handle_metadata()

        self._forward_to_coordinator("PATCH")

    def do_DELETE(self) -> None:
        """Handle DELETE requests - forward to coordinator."""
        self._forward_to_coordinator("DELETE")

    def do_PUT(self) -> None:
        """Handle PUT requests - forward to coordinator."""
        self._forward_to_coordinator("PUT")

    def _forward_to_coordinator(self, method: str) -> None:
        """Forward the request to the coordinator as-is."""
        try:
            # Build target URL
            target_url = f"{self.coordinator_url}{self.path}"

            # Read request body if present
            body = self._read_body()

            # Create request
            request = urllib.request.Request(target_url, method=method, data=body)

            # Add authorization header
            auth_header = self._get_auth_header()
            if auth_header:
                request.add_header("Authorization", auth_header)

            # Forward content-type if present
            content_type = self.headers.get("Content-Type")
            if content_type:
                request.add_header("Content-Type", content_type)

            # Make request to coordinator
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    response_body = response.read()

                    # Send success response
                    self.send_response(response.status)
                    for header, value in response.getheaders():
                        # Skip hop-by-hop headers
                        if header.lower() not in (
                            "transfer-encoding",
                            "connection",
                            "keep-alive",
                        ):
                            self.send_header(header, value)
                    self.end_headers()
                    self.wfile.write(response_body)

            except urllib.error.HTTPError as e:
                # Forward error response from coordinator
                error_body = e.read()
                self.send_response(e.code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(error_body)

        except urllib.error.URLError as e:
            # Connection error to coordinator
            logger.error(f"Gateway failed to connect to coordinator: {e}")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_response = json.dumps({
                "detail": f"Failed to connect to Agent Coordinator: {e.reason}"
            })
            self.wfile.write(error_response.encode("utf-8"))

        except Exception as e:
            # Unexpected error
            logger.error(f"Gateway error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_response = json.dumps({"detail": str(e)})
            self.wfile.write(error_response.encode("utf-8"))


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """HTTP server that handles each request in a new thread."""

    # Allow rapid server restarts
    allow_reuse_address = True

    # Set daemon threads so server doesn't block shutdown
    daemon_threads = True


class RunnerGateway:
    """
    Runner Gateway - Interface between executors and Agent Coordinator.

    Provides a local HTTP endpoint that executors use for all coordinator
    communication. The gateway enriches requests with runner-owned data
    (hostname, project_dir, executor_profile) before forwarding.

    This ensures executors only send data they own (executor_session_id),
    while the runner provides the rest.
    """

    def __init__(
        self,
        coordinator_url: str,
        auth0_client: Optional["Auth0M2MClient"] = None,
        hostname: str = "",
        executor_profile: str = "",
    ):
        """
        Initialize the gateway.

        Args:
            coordinator_url: Base URL of Agent Coordinator (e.g., http://localhost:8765)
            auth0_client: Auth0 M2M client for OIDC authentication
            hostname: Machine hostname (runner-owned)
            executor_profile: Executor profile name (runner-owned)
        """
        self.coordinator_url = coordinator_url.rstrip("/")
        self.auth0_client = auth0_client
        self.hostname = hostname
        self.executor_profile = executor_profile
        self._server: Optional[ThreadedHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._port: int = 0

    @property
    def port(self) -> int:
        """Get the port the gateway is listening on."""
        return self._port

    @property
    def url(self) -> str:
        """Get the local URL for the gateway."""
        return f"http://127.0.0.1:{self._port}"

    def start(self) -> int:
        """
        Start the gateway server.

        Returns:
            The port number the gateway is listening on.
        """
        # Configure handler with coordinator details, auth, and runner data
        RunnerGatewayHandler.coordinator_url = self.coordinator_url
        RunnerGatewayHandler.auth0_client = self.auth0_client
        RunnerGatewayHandler.hostname = self.hostname
        RunnerGatewayHandler.executor_profile = self.executor_profile

        # Bind to port 0 to get a dynamic port assignment
        self._server = ThreadedHTTPServer(("127.0.0.1", 0), RunnerGatewayHandler)
        self._port = self._server.server_address[1]

        # Start server in background thread
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="runner-gateway",
        )
        self._thread.start()

        logger.info(f"Runner Gateway started on port {self._port}")
        logger.debug(f"  Forwarding to: {self.coordinator_url}")
        logger.debug(f"  Runner data: hostname={self.hostname}, profile={self.executor_profile}")

        return self._port

    def stop(self) -> None:
        """Stop the gateway server."""
        if self._server:
            self._server.shutdown()
            self._server = None

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        if self._port:
            logger.info("Runner Gateway stopped")
            self._port = 0
