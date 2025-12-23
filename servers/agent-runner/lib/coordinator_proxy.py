"""
Agent Coordinator Proxy

Local HTTP proxy server that forwards executor requests to the Agent Coordinator
with proper authentication. This allows executors to communicate without needing
direct access to authentication credentials.

The proxy:
- Binds to a dynamic port (127.0.0.1:0) to support multiple runners on same machine
- Forwards all HTTP requests to the Agent Coordinator
- Injects Authorization headers using Auth0 M2M tokens when configured
- Is localhost-only for security

Usage:
    The Agent Runner starts this proxy before spawning executors and sets
    AGENT_ORCHESTRATOR_API_URL to the proxy URL. This is transparent to
    executors - they use the same environment variable without knowing
    they're communicating via a proxy.
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


class CoordinatorProxyHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler that proxies requests to Agent Coordinator."""

    # Class-level configuration (set by CoordinatorProxy before starting)
    coordinator_url: str = ""
    auth0_client: Optional["Auth0M2MClient"] = None

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger instead of stderr."""
        logger.debug(f"Proxy: {format % args}")

    def _get_auth_header(self) -> Optional[str]:
        """Get authorization header value from Auth0 M2M client."""
        if self.auth0_client and self.auth0_client.is_configured:
            token = self.auth0_client.get_access_token()
            if token:
                return f"Bearer {token}"
            logger.warning("Auth0 configured but failed to get token")

        # No auth header when Auth0 is not configured
        return None

    def do_GET(self) -> None:
        """Handle GET requests."""
        self._proxy_request("GET")

    def do_POST(self) -> None:
        """Handle POST requests."""
        self._proxy_request("POST")

    def do_PATCH(self) -> None:
        """Handle PATCH requests."""
        self._proxy_request("PATCH")

    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        self._proxy_request("DELETE")

    def do_PUT(self) -> None:
        """Handle PUT requests."""
        self._proxy_request("PUT")

    def _proxy_request(self, method: str) -> None:
        """Proxy the request to the coordinator."""
        try:
            # Build target URL
            target_url = f"{self.coordinator_url}{self.path}"

            # Read request body if present
            content_length = self.headers.get("Content-Length")
            body = None
            if content_length:
                body = self.rfile.read(int(content_length))

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
            logger.error(f"Proxy failed to connect to coordinator: {e}")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_response = json.dumps({
                "detail": f"Failed to connect to Agent Coordinator: {e.reason}"
            })
            self.wfile.write(error_response.encode("utf-8"))

        except Exception as e:
            # Unexpected error
            logger.error(f"Proxy error: {e}")
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


class CoordinatorProxy:
    """
    Agent Coordinator Proxy server for executor communication.

    Provides a local HTTP endpoint that forwards requests to the Agent Coordinator
    with proper authentication. Executors connect to this proxy instead of the
    coordinator directly.

    Supports multiple runners on the same machine by binding to a dynamic port.
    """

    def __init__(
        self,
        coordinator_url: str,
        auth0_client: Optional["Auth0M2MClient"] = None,
    ):
        """
        Initialize the proxy.

        Args:
            coordinator_url: Base URL of Agent Coordinator (e.g., http://localhost:8765)
            auth0_client: Auth0 M2M client for OIDC authentication
        """
        self.coordinator_url = coordinator_url.rstrip("/")
        self.auth0_client = auth0_client
        self._server: Optional[ThreadedHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._port: int = 0

    @property
    def port(self) -> int:
        """Get the port the proxy is listening on."""
        return self._port

    @property
    def url(self) -> str:
        """Get the local URL for the proxy."""
        return f"http://127.0.0.1:{self._port}"

    def start(self) -> int:
        """
        Start the proxy server.

        Returns:
            The port number the proxy is listening on.
        """
        # Configure handler with coordinator details and auth
        CoordinatorProxyHandler.coordinator_url = self.coordinator_url
        CoordinatorProxyHandler.auth0_client = self.auth0_client

        # Bind to port 0 to get a dynamic port assignment
        self._server = ThreadedHTTPServer(("127.0.0.1", 0), CoordinatorProxyHandler)
        self._port = self._server.server_address[1]

        # Start server in background thread
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="coordinator-proxy",
        )
        self._thread.start()

        logger.info(f"Agent Coordinator Proxy started on port {self._port}")
        logger.debug(f"  Forwarding to: {self.coordinator_url}")

        return self._port

    def stop(self) -> None:
        """Stop the proxy server."""
        if self._server:
            self._server.shutdown()
            self._server = None

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        if self._port:
            logger.info("Agent Coordinator Proxy stopped")
            self._port = 0
