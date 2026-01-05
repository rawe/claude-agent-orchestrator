"""
Embedded MCP Server for Agent Orchestrator.

Provides a FastMCP HTTP server that acts as a facade to the Agent Coordinator.
The server runs embedded within the Agent Runner on a dynamic port.

Key features:
- FastMCP HTTP server with 7 orchestration tools
- Dynamic port binding (127.0.0.1:0)
- Programmatic start/stop lifecycle
- HTTP header extraction for context (X-Agent-Session-Id, X-Agent-Tags)
- Auth0 token injection for Coordinator API calls
"""

import asyncio
import json
import logging
import socket
import threading
from typing import Optional, TYPE_CHECKING

from mcp.server.fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_headers

from .constants import (
    DEFAULT_HOST,
    HEADER_SESSION_ID,
    HEADER_AGENT_TAGS,
    HEADER_ADDITIONAL_DEMANDS,
)
from .schemas import RequestContext
from .coordinator_client import CoordinatorClient
from .tools import AgentOrchestratorTools, ToolError

if TYPE_CHECKING:
    from auth0_client import Auth0M2MClient

logger = logging.getLogger(__name__)


class MCPServer:
    """
    Embedded MCP server - facade to Agent Coordinator.

    Runs FastMCP HTTP server on dynamic port.
    Forwards MCP tool calls to Coordinator API.
    Does NOT spawn executors.
    """

    def __init__(
        self,
        coordinator_url: str,
        auth0_client: Optional["Auth0M2MClient"] = None,
        port: Optional[int] = None,
    ):
        """Initialize MCPServer.

        Args:
            coordinator_url: Agent Coordinator API URL
            auth0_client: Auth0 client for authenticated API calls
            port: Optional fixed port. If None, a random available port is used.
        """
        self._coordinator_url = coordinator_url
        self._auth0_client = auth0_client
        self._specified_port: Optional[int] = port  # None = random, int = fixed
        self._port: int = 0
        self._host: str = DEFAULT_HOST
        self._server_thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._mcp: Optional[FastMCP] = None

        # Create coordinator client and tools
        # IMPORTANT: We pass the auth0_client by reference to share token cache
        # This ensures we reuse the same M2M token from the parent Agent Runner
        self._client = CoordinatorClient(
            base_url=coordinator_url,
            auth0_client=auth0_client,  # Shared instance - token cache is reused
        )
        self._tools = AgentOrchestratorTools(self._client)

    @property
    def port(self) -> int:
        """Port the server is listening on (0 if not started)."""
        return self._port

    @property
    def url(self) -> str:
        """Full URL including MCP path: http://127.0.0.1:<port>/mcp"""
        if self._port == 0:
            return ""
        # FastMCP uses /mcp as the streamable HTTP endpoint path
        return f"http://{self._host}:{self._port}/mcp"

    def _register_tools(self) -> None:
        """Register MCP tools with the FastMCP server."""

        @self._mcp.tool(
            description="List available agent blueprints. Blueprints are filtered by the X-Agent-Tags header if present."
        )
        async def list_agent_blueprints(ctx: Context) -> list[dict]:
            """List available agent blueprints."""
            req_ctx = self._extract_context(ctx)
            try:
                return await self._tools.list_agent_blueprints(req_ctx)
            except ToolError as e:
                return [{"error": str(e)}]

        @self._mcp.tool(
            description="List all agent sessions."
        )
        async def list_agent_sessions(ctx: Context) -> list[dict]:
            """List all agent sessions."""
            req_ctx = self._extract_context(ctx)
            try:
                return await self._tools.list_agent_sessions(req_ctx)
            except ToolError as e:
                return [{"error": str(e)}]

        @self._mcp.tool(
            description="""Start a new agent session.

Args:
    prompt: Initial prompt for the session
    agent_name: Agent blueprint name (optional)
    project_dir: Optional project directory path
    mode: Execution mode - "sync" (wait for result), "async_poll" (return immediately, poll status), or "async_callback" (return immediately, receive callback)

Returns:
    For sync: {"session_id": "...", "result": "..."}
    For async: {"session_id": "...", "status": "pending"}
"""
        )
        async def start_agent_session(
            prompt: str,
            ctx: Context,
            agent_name: Optional[str] = None,
            project_dir: Optional[str] = None,
            mode: str = "sync",
        ) -> dict:
            """Start a new agent session."""
            req_ctx = self._extract_context(ctx)
            try:
                return await self._tools.start_agent_session(
                    ctx=req_ctx,
                    agent_name=agent_name,
                    prompt=prompt,
                    project_dir=project_dir,
                    mode=mode,
                )
            except ToolError as e:
                return {"error": str(e)}

        @self._mcp.tool(
            description="""Resume an existing agent session.

Args:
    session_id: ID of the session to resume
    prompt: Continuation prompt
    mode: Execution mode - "sync", "async_poll", or "async_callback"

Returns:
    For sync: {"session_id": "...", "result": "..."}
    For async: {"session_id": "...", "status": "pending"}
"""
        )
        async def resume_agent_session(
            session_id: str,
            prompt: str,
            ctx: Context,
            mode: str = "sync",
        ) -> dict:
            """Resume an existing agent session."""
            req_ctx = self._extract_context(ctx)
            try:
                return await self._tools.resume_agent_session(
                    ctx=req_ctx,
                    session_id=session_id,
                    prompt=prompt,
                    mode=mode,
                )
            except ToolError as e:
                return {"error": str(e)}

        @self._mcp.tool(
            description="Get the status of an agent session. Returns: running, finished, or not_existent."
        )
        async def get_agent_session_status(session_id: str, ctx: Context) -> dict:
            """Get the status of an agent session."""
            req_ctx = self._extract_context(ctx)
            try:
                return await self._tools.get_agent_session_status(req_ctx, session_id)
            except ToolError as e:
                return {"error": str(e)}

        @self._mcp.tool(
            description="Get the result of a completed agent session."
        )
        async def get_agent_session_result(session_id: str, ctx: Context) -> dict:
            """Get the result of a completed agent session."""
            req_ctx = self._extract_context(ctx)
            try:
                return await self._tools.get_agent_session_result(req_ctx, session_id)
            except ToolError as e:
                return {"error": str(e)}

        @self._mcp.tool(
            description="Delete all agent sessions. Use with caution."
        )
        async def delete_all_agent_sessions(ctx: Context) -> dict:
            """Delete all agent sessions."""
            req_ctx = self._extract_context(ctx)
            try:
                return await self._tools.delete_all_agent_sessions(req_ctx)
            except ToolError as e:
                return {"error": str(e)}

    def _extract_context(self, ctx: Context) -> RequestContext:
        """Extract request context from FastMCP Context.

        Uses FastMCP's get_http_headers() to access HTTP headers.
        Headers are returned with lowercase keys.
        """
        http_headers = get_http_headers()

        # Extract parent session ID (for callbacks)
        parent_session_id = http_headers.get(HEADER_SESSION_ID.lower())

        # Extract tags (for blueprint filtering)
        tags = http_headers.get(HEADER_AGENT_TAGS.lower())

        # Extract additional demands (JSON)
        additional_demands = {}
        demands_str = http_headers.get(HEADER_ADDITIONAL_DEMANDS.lower())
        if demands_str:
            try:
                additional_demands = json.loads(demands_str)
                if not isinstance(additional_demands, dict):
                    logger.warning(
                        f"Invalid {HEADER_ADDITIONAL_DEMANDS} header: expected object"
                    )
                    additional_demands = {}
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse {HEADER_ADDITIONAL_DEMANDS}: {e}")

        return RequestContext(
            parent_session_id=parent_session_id,
            tags=tags,
            additional_demands=additional_demands,
        )

    def _find_available_port(self) -> int:
        """Find an available port by binding to port 0."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self._host, 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def _check_port_available(self, port: int) -> bool:
        """Check if a specific port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self._host, port))
                return True
        except OSError:
            return False

    def start(self) -> int:
        """Start server on specified or dynamic port. Returns assigned port."""
        if self._server_thread is not None:
            raise RuntimeError("Server already started")

        # Determine port: use specified port or find available one
        if self._specified_port is not None:
            if not self._check_port_available(self._specified_port):
                raise RuntimeError(
                    f"MCP server port {self._specified_port} is already in use"
                )
            self._port = self._specified_port
        else:
            self._port = self._find_available_port()

        # Create FastMCP server with the assigned port
        self._mcp = FastMCP(
            "Agent Orchestrator",
            host=self._host,
            port=self._port,
            log_level="WARNING",  # Reduce noise
        )

        # Register tools
        self._register_tools()

        # Create stop event
        self._stop_event = threading.Event()

        # Create server in background thread
        self._server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="mcp-server",
        )
        self._server_thread.start()

        # Wait a moment for server to start
        import time
        time.sleep(0.5)

        logger.info(f"Embedded MCP server started on port {self._port}")
        logger.debug(f"  URL: {self.url}")

        return self._port

    def _run_server(self) -> None:
        """Run the server (called in background thread)."""
        # Suppress websockets deprecation warnings
        #
        # Root cause: FastMCP uses uvicorn for HTTP transport. Uvicorn eagerly imports
        # the websockets library even when only serving HTTP (no WebSocket usage).
        # In websockets 14.0 (Nov 2024), the legacy API was deprecated, but uvicorn
        # hasn't migrated yet. This causes noisy warnings on startup.
        #
        # Two warning sources:
        # 1. websockets/legacy/__init__.py - "websockets.legacy is deprecated"
        # 2. uvicorn/protocols/websockets/websockets_impl.py - "WebSocketServerProtocol is deprecated"
        #
        # We don't use WebSockets at all - FastMCP's streamable-http is pure HTTP.
        # This suppression can be removed once uvicorn updates their websockets usage.
        # Track: https://github.com/encode/uvicorn/issues
        #
        # Must be set HERE (in the server thread) because uvicorn imports websockets
        # lazily when starting, and warnings filters must be set before the import.
        import warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning, message=r".*websockets.*")

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Run FastMCP with streamable HTTP transport
            # Host and port are already configured in FastMCP constructor
            loop.run_until_complete(self._mcp.run_streamable_http_async())
        except Exception as e:
            if not self._stop_event.is_set():
                logger.error(f"MCP server error: {e}")
        finally:
            # Cleanup
            loop.run_until_complete(self._client.close())
            loop.close()

    def stop(self) -> None:
        """Stop the server gracefully."""
        if self._stop_event:
            self._stop_event.set()

        # The server thread is daemon, so it will be stopped when the main thread exits
        # For cleaner shutdown, we could add signal handling, but for now this is sufficient

        if self._server_thread:
            # Give thread a moment to notice stop
            self._server_thread.join(timeout=1.0)
            self._server_thread = None

        if self._port:
            logger.info("Embedded MCP server stopped")
            self._port = 0
