# Agent Orchestrator API Mode

The Agent Orchestrator MCP Server can run in API mode, exposing both the MCP protocol and a REST API with OpenAPI documentation.

> **Note:** This documentation covers the **standalone server** for external clients (Claude Desktop, Claude Code, custom applications). For agents running within the framework, the MCP server is embedded in the Agent Runner.

## Quick Start

### Using Make (Recommended)

From the project root directory:

```bash
# Start the API server (uses configuration from .env)
make start-ao-api

# Stop the API server
make stop-ao-api
```

**Configuration** (in `.env` file):
```bash
# Optional: customize host and port (defaults shown)
AGENT_ORCHESTRATOR_MCP_HOST=127.0.0.1
AGENT_ORCHESTRATOR_MCP_PORT=9500

# Optional: set default project directory for agent sessions
AGENT_ORCHESTRATOR_PROJECT_DIR=/path/to/your/project
```

**Output:**
```
Starting Agent Orchestrator API server (REST + MCP)...
Configuration:
  Host: 127.0.0.1
  Port: 9500
  Project Dir: <not set, uses tool parameter>

API server started (PID: 12345)

Endpoints:
  MCP Protocol:  http://127.0.0.1:9500/mcp
  REST API:      http://127.0.0.1:9500/api
  API Docs:      http://127.0.0.1:9500/api/docs
  ReDoc:         http://127.0.0.1:9500/api/redoc
```

### Using Direct Command

```bash
# Start the server in API mode (default port 8080)
uv run --script agent-orchestrator-mcp.py --api-mode

# Start on a custom port
uv run --script agent-orchestrator-mcp.py --api-mode --port 9000

# Start accessible from network
uv run --script agent-orchestrator-mcp.py --api-mode --host 0.0.0.0 --port 8080
```

## Available Endpoints

When running in API mode, the following endpoints are available:

| Endpoint | Description |
|----------|-------------|
| `http://localhost:8080/` | Redirects to API documentation |
| `http://localhost:8080/api/docs` | Swagger UI (interactive documentation) |
| `http://localhost:8080/api/redoc` | ReDoc (alternative documentation) |
| `http://localhost:8080/api/openapi.json` | OpenAPI 3.1 specification |
| `http://localhost:8080/mcp` | MCP protocol endpoint |

## API Documentation

Once the server is running, open your browser to view the interactive API documentation:

- **Swagger UI**: `http://localhost:8080/api/docs` - Interactive API explorer with "Try it out" functionality
- **ReDoc**: `http://localhost:8080/api/redoc` - Clean, readable API reference

The OpenAPI specification is available at `http://localhost:8080/api/openapi.json` for code generation tools.

## REST API Reference

### Blueprints

#### List Agent Blueprints
```
GET /api/blueprints
```

Returns all available agent blueprints that can be used to create sessions.

**Response:**
```json
{
  "total": 3,
  "blueprints": [
    {
      "name": "web-researcher",
      "description": "Conducts iterative web research..."
    }
  ]
}
```

### Sessions

#### List Sessions
```
GET /api/sessions
```

Returns all agent sessions (running, completed, or initializing).

**Response:**
```json
{
  "total": 2,
  "sessions": [
    {
      "name": "my-session",
      "session_id": "uuid-string",
      "project_dir": "/path/to/project"
    }
  ]
}
```

#### Start New Session
```
POST /api/sessions
Content-Type: application/json

{
  "session_name": "my-new-session",
  "prompt": "Research the latest AI developments",
  "agent_blueprint_name": "web-researcher",
  "project_dir": "/optional/path",
  "async_mode": false
}
```

**Parameters:**
- `session_name` (required): Unique identifier (alphanumeric, dash, underscore; max 60 chars)
- `prompt` (required): Task description for the agent
- `agent_blueprint_name` (optional): Blueprint to use
- `project_dir` (optional): Absolute path to project directory
- `async_mode` (optional): If `true`, returns immediately while session runs in background

**Response (sync mode):**
```json
{
  "result": "Agent output text..."
}
```

**Response (async mode):**
```json
{
  "session_name": "my-new-session",
  "status": "running",
  "message": "Session started in background"
}
```

#### Resume Session
```
POST /api/sessions/{session_name}/resume
Content-Type: application/json

{
  "prompt": "Continue with the next step",
  "async_mode": false
}
```

#### Get Session Status
```
GET /api/sessions/{session_name}/status?wait_seconds=0
```

**Query Parameters:**
- `wait_seconds` (optional, 0-300): Delay before checking status (for polling)

**Response:**
```json
{
  "status": "running" | "finished" | "not_existent"
}
```

#### Get Session Result
```
GET /api/sessions/{session_name}/result
```

Retrieves the final output from a completed session. Returns error if session is still running.

**Response:**
```json
{
  "result": "Final agent output..."
}
```

#### Delete All Sessions
```
DELETE /api/sessions
```

Permanently deletes all sessions and their data.

## Writing a Client

### Python Example

```python
import requests

BASE_URL = "http://localhost:8080"

# List available blueprints
blueprints = requests.get(f"{BASE_URL}/api/blueprints").json()
print(f"Available blueprints: {[b['name'] for b in blueprints['blueprints']]}")

# Start a session (synchronous - waits for completion)
response = requests.post(f"{BASE_URL}/api/sessions", json={
    "session_name": "my-research",
    "prompt": "What are the latest developments in AI?",
    "agent_blueprint_name": "web-researcher"
})
print(response.json()["result"])
```

### Python Example (Async Mode with Polling)

```python
import requests
import time

BASE_URL = "http://localhost:8080"

# Start session in async mode
response = requests.post(f"{BASE_URL}/api/sessions", json={
    "session_name": "long-task",
    "prompt": "Conduct comprehensive research on...",
    "agent_blueprint_name": "web-researcher",
    "async_mode": True
})
print(f"Session started: {response.json()}")

# Poll for completion
while True:
    status = requests.get(
        f"{BASE_URL}/api/sessions/long-task/status",
        params={"wait_seconds": 5}  # Server waits 5s before responding
    ).json()

    print(f"Status: {status['status']}")

    if status["status"] == "finished":
        break
    elif status["status"] == "not_existent":
        raise Exception("Session not found")

# Get result
result = requests.get(f"{BASE_URL}/api/sessions/long-task/result").json()
print(result["result"])
```

### JavaScript/TypeScript Example

```typescript
const BASE_URL = "http://localhost:8080";

async function runAgentSession(prompt: string, blueprint?: string) {
  // Start session
  const startResponse = await fetch(`${BASE_URL}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_name: `session-${Date.now()}`,
      prompt,
      agent_blueprint_name: blueprint,
      async_mode: true,
    }),
  });

  const { session_name } = await startResponse.json();

  // Poll for completion
  while (true) {
    const statusResponse = await fetch(
      `${BASE_URL}/api/sessions/${session_name}/status?wait_seconds=5`
    );
    const { status } = await statusResponse.json();

    if (status === "finished") break;
    if (status === "not_existent") throw new Error("Session not found");
  }

  // Get result
  const resultResponse = await fetch(
    `${BASE_URL}/api/sessions/${session_name}/result`
  );
  return (await resultResponse.json()).result;
}
```

### cURL Examples

```bash
# List blueprints
curl http://localhost:8080/api/blueprints

# Start a session (sync)
curl -X POST http://localhost:8080/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"session_name":"test","prompt":"Hello world","async_mode":false}'

# Check session status
curl http://localhost:8080/api/sessions/test/status

# Get session result
curl http://localhost:8080/api/sessions/test/result

# Delete all sessions
curl -X DELETE http://localhost:8080/api/sessions
```

## Client Considerations

### 1. Long-Running Operations

Agent sessions can take significant time (minutes to hours) depending on the task. For production use:

- **Use async mode** (`async_mode: true`) to avoid HTTP timeouts
- **Implement polling** with `wait_seconds` parameter to reduce API calls
- **Set appropriate timeouts** on your HTTP client (or disable for sync mode)

### 2. Polling Strategy

The `wait_seconds` parameter on `/api/sessions/{name}/status` makes the server wait before responding, reducing round-trips:

| Task Type | Recommended `wait_seconds` |
|-----------|---------------------------|
| Quick tasks | 2-5 seconds |
| Medium tasks | 10-30 seconds |
| Long research tasks | 60+ seconds |

### 3. Error Handling

Handle these common error scenarios:

```python
response = requests.post(f"{BASE_URL}/api/sessions", json={...})

if response.status_code == 400:
    # Bad request (invalid parameters, session name exists, etc.)
    error = response.json()
    print(f"Error: {error['detail']}")
elif response.status_code == 500:
    # Server error
    print("Internal server error")
```

### 4. Session Naming

Session names must be:
- Unique (cannot reuse existing names)
- 1-60 characters long
- Alphanumeric with dashes (`-`) and underscores (`_`) only

**Recommendation:** Use timestamps or UUIDs in session names:
```python
session_name = f"research-{int(time.time())}"
# or
session_name = f"task-{uuid.uuid4().hex[:8]}"
```

### 5. MCP vs REST API

| Use Case | Recommended |
|----------|-------------|
| Claude Desktop integration | MCP endpoint (`/mcp`) |
| Claude CLI integration | MCP endpoint (`/mcp`) |
| Custom application | REST API (`/api/*`) |
| Automation scripts | REST API (`/api/*`) |
| Web frontend | REST API (`/api/*`) |

### 6. Concurrent Sessions

Multiple sessions can run concurrently. Each session:
- Has its own isolated Claude Code context
- Maintains separate conversation history
- Can use different blueprints

### 7. Security Considerations

When exposing the API:
- Use `--host 127.0.0.1` (default) for local-only access
- Use `--host 0.0.0.0` only in trusted networks or behind a reverse proxy
- Consider adding authentication via a reverse proxy (nginx, Caddy, etc.)
- The API does not include built-in authentication

## Comparison: API Mode vs Other Modes

| Mode | Command | Use Case |
|------|---------|----------|
| stdio | `uv run --script agent-orchestrator-mcp.py` | Claude Desktop/CLI integration |
| HTTP | `--http-mode` | MCP-only network access |
| SSE | `--sse-mode` | Legacy MCP clients |
| **API** | `--api-mode` | REST API + MCP combined |

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :8080

# Use a different port
uv run --script agent-orchestrator-mcp.py --api-mode --port 9000
```

### Session Stuck in "running"
```bash
# Check if Claude Code process is running
ps aux | grep claude

# List sessions to verify state
curl http://localhost:8080/api/sessions
```

### Getting Session Result Fails
The session must be in "finished" status before retrieving results. Poll the status endpoint first:
```bash
curl http://localhost:8080/api/sessions/my-session/status
```
