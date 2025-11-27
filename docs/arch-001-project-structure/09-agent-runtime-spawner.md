# Package 09: Agent Runtime Spawner

## Goal
Add agent spawning capability to Agent Runtime server, moving Claude Agent SDK logic from commands into the server.

## What Changes

| Component | Before | After |
|-----------|--------|-------|
| Agent Runtime | Passive storage (sessions, events) | Active spawner + storage |
| SDK logic | In `commands/lib/claude_client.py` | In `servers/agent-runtime/spawner.py` |

## Steps

1. **Create spawner module**
   - Create `servers/agent-runtime/spawner.py`
   - Extract SDK logic from `plugins/orchestrator/skills/orchestrator/commands/lib/claude_client.py`
   - Extract session management from `commands/lib/session.py`

2. **Add new endpoints to Agent Runtime**
   - `POST /sessions` - create session AND spawn agent
   - `POST /sessions/{id}/resume` - resume session with new prompt
   - Integrate with existing session storage

3. **Implement async streaming**
   - Handle SDK message streaming
   - Persist events to database while streaming
   - Broadcast to WebSocket clients

4. **Add Agent Registry integration**
   - Query blueprint from Agent Registry when `--agent` specified
   - Apply blueprint configuration to spawned agent

5. **Update dependencies**
   - Add Claude Agent SDK to `servers/agent-runtime/pyproject.toml`

## Note
Existing ao-* commands continue to work unchanged. They still use their own SDK logic. Package 10 will convert them to thin clients.

## Verification
- New endpoints work via curl/httpie
- Agent spawns and runs correctly
- Events stream to WebSocket
- Results stored and retrievable
- Old ao-* commands still work (not yet converted)

## References
- Component details: See [ARCHITECTURE.md](./ARCHITECTURE.md#agent-runtime)
- Endpoint spec: See [ARCHITECTURE.md](./ARCHITECTURE.md#agent-runtime) → Key Endpoints
