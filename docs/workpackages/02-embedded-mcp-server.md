# Work Package 2: Embedded MCP Server Library

## Introduction

Create a self-contained MCP server library that runs embedded within the Agent Runner. This server acts as a facade to the Coordinator API - it receives MCP tool calls from Claude and forwards them to the Coordinator. It does NOT spawn executors. The server binds to a dynamic port and its URL is used for placeholder resolution (from Work Package 1).

**Reference:** `docs/architecture/mcp-runner-integration-mvp.md`

**Prerequisite:** Work Package 1 must be completed first.

## What To Do

1. **Create library structure** - See MVP section "Directory Structure" (lines 339-365)
   - New directory: `lib/agent_orchestrator_mcp/`

2. **Implement `MCPServer`** - See MVP section "MCPServer (`agent_orchestrator_mcp/server.py`)" (lines 369-409)
   - FastMCP HTTP server on dynamic port (`127.0.0.1:0`)
   - `start()` returns assigned port, exposes `.url` property
   - `stop()` for graceful shutdown

3. **Implement `CoordinatorClient`** - See MVP section "CoordinatorClient (`agent_orchestrator_mcp/coordinator_client.py`)" (lines 411-452)
   - Async HTTP client with Auth0 token injection
   - Methods for runs, sessions, and agents API

4. **Implement all 7 MCP tools** - See MVP section "MCP Tools (`agent_orchestrator_mcp/tools.py`)" (lines 500-518)
   - Extract context from HTTP headers (`X-Agent-Session-Id`, `X-Agent-Tags`, `X-Additional-Demands`)

5. **Integrate into Runner startup** - See MVP section "Agent Runner Startup" (lines 612-641)
   - Start MCP server after Auth0 client init
   - Pass `mcp_server.url` to `RunExecutor`

## Files

| Action | Path |
|--------|------|
| CREATE | `servers/agent-runner/lib/agent_orchestrator_mcp/__init__.py` |
| CREATE | `servers/agent-runner/lib/agent_orchestrator_mcp/server.py` |
| CREATE | `servers/agent-runner/lib/agent_orchestrator_mcp/coordinator_client.py` |
| CREATE | `servers/agent-runner/lib/agent_orchestrator_mcp/tools.py` |
| CREATE | `servers/agent-runner/lib/agent_orchestrator_mcp/context.py` |
| CREATE | `servers/agent-runner/lib/agent_orchestrator_mcp/constants.py` |
| CREATE | `servers/agent-runner/lib/agent_orchestrator_mcp/schemas.py` |
| MODIFY | `servers/agent-runner/agent-runner` (main entry point) |

## TODO Checklist

- [ ] Create `lib/agent_orchestrator_mcp/` directory structure
- [ ] Implement `MCPServer` with dynamic port binding (`host="127.0.0.1", port=0`)
- [ ] Implement `CoordinatorClient` with async HTTP methods and Auth0 token injection
- [ ] Implement `list_agent_blueprints` tool (filters by `X-Agent-Tags`)
- [ ] Implement `list_agent_sessions` tool
- [ ] Implement `start_agent_session` tool (sync/async_poll/async_callback modes)
- [ ] Implement `resume_agent_session` tool
- [ ] Implement `get_agent_session_status` tool
- [ ] Implement `get_agent_session_result` tool
- [ ] Implement `delete_all_agent_sessions` tool
- [ ] Implement HTTP header context extraction (`X-Agent-Session-Id`, `X-Agent-Tags`, `X-Additional-Demands`)
- [ ] Add MCP server startup to Runner main (after Auth0, before executor creation)
- [ ] Pass `mcp_server.url` to `RunExecutor` for placeholder resolution
- [ ] Implement graceful shutdown on Runner exit

## Testing Checklist

- [ ] Unit: MCP server starts and binds to dynamic port
- [ ] Unit: `mcp_server.url` returns correct `http://127.0.0.1:<port>` format
- [ ] Unit: `CoordinatorClient` injects Bearer token when Auth0 configured
- [ ] Unit: Each of the 7 MCP tools responds correctly (mock Coordinator)
- [ ] Unit: Header context extraction parses `X-Agent-Tags`, `X-Agent-Session-Id`
- [ ] Integration: Runner starts with embedded MCP server
- [ ] Integration: Blueprint placeholders resolve to embedded MCP server URL
- [ ] Integration: Claude (in executor) calls MCP tool -> forwarded to Coordinator
- [ ] Integration: Full flow - start child session via MCP -> Coordinator creates run -> Runner executes
- [ ] Integration: Remove standalone MCP server dependency - all tests use embedded server

## Documentation Updates

Update the following documentation to reflect the embedded MCP server:

| File | What to Update |
|------|----------------|
| `servers/agent-runner/README.md` | Add new section "Embedded MCP Server" describing: dynamic port binding, facade to Coordinator, 7 MCP tools available. Update "Architecture" diagram (lines 103-121) to show MCP server component |
| `docs/ARCHITECTURE.md` | Update "Agent Runner Architecture" section (lines 202-260): add embedded MCP server to diagram, note that executors no longer call Agent Blueprints API directly (remove from lines 253-254), update component interactions table |
| `docs/ARCHITECTURE.md` | Update "Component Interactions" diagram (lines 114-164): show MCP server as part of Runner, update flow arrows |
| `docs/ARCHITECTURE.md` | Update "Interaction Summary" table (lines 168-182): change "Executors -> Agent Coordinator Proxy" row to note executors use embedded MCP for orchestration tools |
