"""
Minimal MCP Server

HTTP-based MCP server with simple tools for testing.
Records all tool invocations for assertions.

Tools:
- echo: Returns the input message
- get_time: Returns current timestamp
- add_numbers: Adds two numbers
- fail_on_purpose: Always returns an error

MCP Protocol:
- Uses JSON-RPC 2.0 over HTTP
- POST / with JSON-RPC request
- Supports: tools/list, tools/call
"""

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, UTC
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any


@dataclass
class ToolCall:
    """Recorded tool call."""
    timestamp: str
    tool_name: str
    arguments: dict
    result: Any = None
    error: str | None = None


# Tool definitions in MCP format
MCP_TOOLS = [
    {
        "name": "echo",
        "description": "Returns the input message back",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to echo back"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "get_time",
        "description": "Returns the current timestamp in ISO format",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "add_numbers",
        "description": "Adds two numbers together",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "fail_on_purpose",
        "description": "Always returns an error (for testing error handling)",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "store_data",
        "description": "Stores arbitrary data and returns confirmation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key to store data under"
                },
                "value": {
                    "type": "string",
                    "description": "Value to store"
                }
            },
            "required": ["key", "value"]
        }
    }
]


class MinimalMCPServer:
    """
    Minimal MCP server for testing.

    Usage:
        mcp = MinimalMCPServer()
        mcp.start()
        url = mcp.url  # e.g., "http://127.0.0.1:54322"

        # Run executor tests with MCP...

        calls = mcp.get_tool_calls()
        mcp.stop()
    """

    def __init__(self, port: int = 0):
        """
        Initialize MCP server.

        Args:
            port: Port to listen on (0 = random available port)
        """
        self._port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._tool_calls: list[ToolCall] = []
        self._stored_data: dict[str, str] = {}
        self._lock = threading.Lock()

    @property
    def url(self) -> str:
        """Get the MCP server URL."""
        if self._server is None:
            raise RuntimeError("MCP server not started")
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    @property
    def port(self) -> int:
        """Get the MCP server port."""
        if self._server is None:
            raise RuntimeError("MCP server not started")
        return self._server.server_address[1]

    def start(self) -> str:
        """Start the MCP server. Returns the URL."""
        handler = self._create_handler()
        self._server = HTTPServer(("127.0.0.1", self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()
        return self.url

    def stop(self):
        """Stop the MCP server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def get_tool_calls(self) -> list[ToolCall]:
        """Get all recorded tool calls."""
        with self._lock:
            return list(self._tool_calls)

    def get_tool_calls_by_name(self, name: str) -> list[ToolCall]:
        """Get tool calls for a specific tool."""
        with self._lock:
            return [c for c in self._tool_calls if c.tool_name == name]

    def get_stored_data(self) -> dict[str, str]:
        """Get all data stored via store_data tool."""
        with self._lock:
            return dict(self._stored_data)

    def clear(self):
        """Clear all recorded calls and stored data."""
        with self._lock:
            self._tool_calls.clear()
            self._stored_data.clear()

    def _record_tool_call(self, call: ToolCall):
        """Record a tool call (thread-safe)."""
        with self._lock:
            self._tool_calls.append(call)

    def _store_data(self, key: str, value: str):
        """Store data (thread-safe)."""
        with self._lock:
            self._stored_data[key] = value

    def _execute_tool(self, name: str, arguments: dict) -> tuple[Any, str | None]:
        """
        Execute a tool and return (result, error).

        Returns:
            Tuple of (result, error_message). One will be None.
        """
        if name == "echo":
            message = arguments.get("message", "")
            return message, None

        elif name == "get_time":
            return datetime.now(UTC).isoformat(), None

        elif name == "add_numbers":
            a = arguments.get("a", 0)
            b = arguments.get("b", 0)
            return a + b, None

        elif name == "fail_on_purpose":
            return None, "This tool always fails (for testing)"

        elif name == "store_data":
            key = arguments.get("key", "")
            value = arguments.get("value", "")
            self._store_data(key, value)
            return f"Stored '{key}'", None

        else:
            return None, f"Unknown tool: {name}"

    def _create_handler(self):
        """Create request handler with access to MCP server instance."""
        mcp = self

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

            def _jsonrpc_response(self, id: Any, result: Any = None, error: dict | None = None):
                """Build JSON-RPC 2.0 response."""
                response = {"jsonrpc": "2.0", "id": id}
                if error:
                    response["error"] = error
                else:
                    response["result"] = result
                return response

            def do_POST(self):
                body = self._read_body()

                if not body:
                    self._send_json({"error": "No body"}, 400)
                    return

                # JSON-RPC 2.0 request
                jsonrpc = body.get("jsonrpc")
                method = body.get("method")
                params = body.get("params", {})
                req_id = body.get("id")

                if jsonrpc != "2.0":
                    self._send_json(
                        self._jsonrpc_response(req_id, error={
                            "code": -32600,
                            "message": "Invalid Request: jsonrpc must be '2.0'"
                        })
                    )
                    return

                # Handle MCP methods
                if method == "initialize":
                    # MCP initialization
                    self._send_json(self._jsonrpc_response(req_id, result={
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {
                            "name": "test-mcp-server",
                            "version": "1.0.0"
                        },
                        "capabilities": {
                            "tools": {}
                        }
                    }))

                elif method == "notifications/initialized":
                    # Client notification, no response needed for notifications
                    # But we send acknowledgment anyway
                    self._send_json(self._jsonrpc_response(req_id, result={}))

                elif method == "tools/list":
                    # List available tools
                    self._send_json(self._jsonrpc_response(req_id, result={
                        "tools": MCP_TOOLS
                    }))

                elif method == "tools/call":
                    # Call a tool
                    tool_name = params.get("name", "")
                    arguments = params.get("arguments", {})

                    result, error = mcp._execute_tool(tool_name, arguments)

                    # Record the call
                    mcp._record_tool_call(ToolCall(
                        timestamp=datetime.now(UTC).isoformat(),
                        tool_name=tool_name,
                        arguments=arguments,
                        result=result,
                        error=error,
                    ))

                    if error:
                        # Return error as content (MCP style)
                        self._send_json(self._jsonrpc_response(req_id, result={
                            "content": [
                                {"type": "text", "text": f"Error: {error}"}
                            ],
                            "isError": True
                        }))
                    else:
                        # Return result as content
                        result_text = str(result) if result is not None else ""
                        self._send_json(self._jsonrpc_response(req_id, result={
                            "content": [
                                {"type": "text", "text": result_text}
                            ]
                        }))

                elif method == "ping":
                    # Health check
                    self._send_json(self._jsonrpc_response(req_id, result={}))

                else:
                    # Unknown method
                    self._send_json(self._jsonrpc_response(req_id, error={
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }))

        return Handler


# Convenience for testing the MCP server directly
if __name__ == "__main__":
    mcp = MinimalMCPServer(port=9999)
    print(f"Starting minimal MCP server on {mcp.start()}")
    print(f"Available tools: {[t['name'] for t in MCP_TOOLS]}")
    try:
        input("Press Enter to stop...")
    finally:
        print(f"Tool calls: {mcp.get_tool_calls()}")
        mcp.stop()
