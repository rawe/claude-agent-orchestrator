# Package 10: Thin Client Commands

## Goal
Refactor ao-* commands from SDK-heavy scripts to thin HTTP clients calling Agent Runtime.

## What Changes

| Component | Before | After |
|-----------|--------|-------|
| ao-* commands | ~200+ LOC, import SDK | ~50 LOC, HTTP calls only |
| `commands/lib/claude_client.py` | Core SDK logic | Deleted |
| `commands/lib/session.py` | Session management | Deleted |

## Command → Endpoint Mapping

| Command | HTTP Call |
|---------|-----------|
| `ao-new` | POST `/sessions` |
| `ao-resume` | POST `/sessions/{name}/resume` |
| `ao-status` | GET `/sessions/{name}/status` |
| `ao-get-result` | GET `/sessions/{name}/result` |
| `ao-list-sessions` | GET `/sessions` |
| `ao-list-agents` | GET `{AGENT_REGISTRY_URL}/agents` |
| `ao-show-config` | GET `/sessions/{name}` |
| `ao-clean` | DELETE `/sessions` |

## Steps

1. **Refactor each command**
   - Replace SDK imports with HTTP client (httpx or requests)
   - Call Agent Runtime endpoints instead of SDK directly
   - Keep CLI argument parsing unchanged

2. **Update ao-new**
   - POST to `/sessions` with session_name, blueprint, prompt, project_dir

3. **Update ao-resume**
   - POST to `/sessions/{name}/resume` with prompt

4. **Update ao-status, ao-get-result, ao-list-sessions, ao-show-config**
   - Simple GET requests to corresponding endpoints

5. **Update ao-list-agents**
   - GET request to Agent Registry `/agents`

6. **Update ao-clean**
   - DELETE request to `/sessions`

7. **Delete obsolete lib files**
   - Remove `commands/lib/claude_client.py`
   - Remove `commands/lib/session.py`
   - Keep `commands/lib/config.py` (for URL configuration)

8. **Update MCP server**
   - Refactor to use HTTP calls instead of subprocess to commands
   - Now both MCP and CLI are thin clients to same API

## Verification
- All ao-* commands work as before (same CLI interface)
- Commands are significantly smaller (~50 LOC each)
- No SDK dependencies in commands
- MCP server works via HTTP

## References
- CLI spec: See [ARCHITECTURE.md](./ARCHITECTURE.md#cli-commands-thin-clients)
- Endpoint spec: See [ARCHITECTURE.md](./ARCHITECTURE.md#agent-runtime) → Key Endpoints
