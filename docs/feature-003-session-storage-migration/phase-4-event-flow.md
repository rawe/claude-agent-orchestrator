# Phase 4: Event Flow Migration

## Overall Context

We are migrating the Agent Orchestrator from file-based session storage to database-backed storage via the **Agent Session Manager** service. This final phase updates the core session execution flow in `claude_client.py` and removes the old `observability.py`.

**Key change:** Session is created via API when `SystemMessage` is received (not via `session_start` event).

## This Phase's Goal

Update the session execution flow to:
1. Create session via `POST /sessions` (not `session_start` event)
2. Send events via `POST /sessions/{id}/events`
3. Remove old `observability.py` module
4. Update `ao-new` and `ao-resume` commands

## Prerequisites

- Phase 1 complete (backend API exists)
- Phase 2 complete (SessionClient exists)
- Phase 3 complete (other commands migrated)

## Reference

Read these sections in `analysis.md`:
- "Event Type Consolidation" - new vs old flow diagram
- "Phase 4: Event Capture" - code example for new flow

## Tasks

### 1. Update claude_client.py

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/claude_client.py`

**Remove:**
- All imports from `observability.py`
- `observability_enabled` parameter
- `observability_url` parameter
- Calls to `set_observability_url()`
- `user_prompt_hook` registration (it sent `session_start`)

**Add:**
- Import `SessionClient` from `session_client.py`
- `session_manager_url` parameter

**Change the flow:**

```python
async def run_claude_session(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    session_name: Optional[str] = None,
    sessions_dir: Optional[Path] = None,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
    session_manager_url: str = "http://127.0.0.1:8765",  # NEW
    agent_name: Optional[str] = None,
) -> tuple[str, str]:

    from session_client import SessionClient
    client = SessionClient(session_manager_url)

    # ... SDK setup ...

    async with ClaudeSDKClient(options=options) as sdk_client:
        await sdk_client.query(prompt)

        session_created = False

        async for message in sdk_client.receive_response():
            # Write to .jsonl file (backup)
            # ...

            # On SystemMessage: CREATE SESSION via API
            if isinstance(message, SystemMessage) and message.subtype == 'init':
                session_id = message.data.get('session_id')

                if not resume_session_id:  # New session
                    client.create_session(
                        session_id=session_id,
                        session_name=session_name,
                        project_dir=str(project_dir),
                        agent_name=agent_name
                    )
                    session_created = True
                else:  # Resume - update last_resumed_at
                    client.update_session(
                        session_id=session_id,
                        last_resumed_at=datetime.now(UTC).isoformat()
                    )

                # Also update file metadata (backup)
                if session_name and sessions_dir:
                    from session import update_session_id
                    update_session_id(session_name, session_id, sessions_dir)

            # On ResultMessage: send assistant message event
            if isinstance(message, ResultMessage):
                if session_id is None:
                    session_id = message.session_id

                result = message.result

                # Send assistant message to API
                client.add_event(session_id, {
                    "event_type": "message",
                    "session_id": session_id,
                    "session_name": session_name or session_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "role": "assistant",
                    "content": [{"type": "text", "text": result}]
                })

        # After loop: send session_stop
        client.add_event(session_id, {
            "event_type": "session_stop",
            "session_id": session_id,
            "session_name": session_name or session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "exit_code": 0,
            "reason": "completed"
        })

    return session_id, result
```

### 2. Update SDK Hooks

Keep only these hooks (they send events, not create session):
- `post_tool_hook` - sends `post_tool` events

Remove or disable:
- `user_prompt_hook` - no longer sends `session_start`

Update hooks to use SessionClient:

```python
# In claude_client.py or separate hooks module
_session_client: Optional[SessionClient] = None
_current_session_id: Optional[str] = None

def set_session_context(client: SessionClient, session_id: str):
    global _session_client, _current_session_id
    _session_client = client
    _current_session_id = session_id

async def post_tool_hook(input_data, tool_use_id, context):
    if _session_client and _current_session_id:
        _session_client.add_event(_current_session_id, {
            "event_type": "post_tool",
            "session_id": _current_session_id,
            "session_name": _current_session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "tool_name": input_data.get("tool_name"),
            "tool_input": input_data.get("tool_input"),
            "tool_output": input_data.get("tool_response"),
            "error": input_data.get("error"),
        })
    return {}
```

### 3. Update ao-new

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/ao-new`

Changes:
- Remove `observability_enabled` and `observability_url` from `run_session_sync()` call
- Add `session_manager_url=config.session_manager_url`
- Keep file-based metadata save as backup

```python
session_id, result = run_session_sync(
    prompt=final_prompt,
    session_file=session_file,
    project_dir=config.project_dir,
    session_name=session_name,
    sessions_dir=config.sessions_dir,
    mcp_servers=mcp_servers,
    session_manager_url=config.session_manager_url,  # NEW
    agent_name=agent_name,
)
```

### 4. Update ao-resume

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/ao-resume`

Similar changes:
- Use SessionClient to get session info instead of file
- Pass `session_manager_url` to `run_session_sync()`
- Keep file operations as backup

### 5. Delete observability.py

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/observability.py`

Delete this file entirely. All its functionality is replaced by:
- Session creation → `SessionClient.create_session()`
- Event sending → `SessionClient.add_event()`
- Metadata update → `SessionClient.update_session()`

### 6. Update run_session_sync

Update the sync wrapper to pass through new parameter:

```python
def run_session_sync(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    session_name: Optional[str] = None,
    sessions_dir: Optional[Path] = None,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
    session_manager_url: str = "http://127.0.0.1:8765",  # NEW
    agent_name: Optional[str] = None,
) -> tuple[str, str]:
    return asyncio.run(
        run_claude_session(
            # ... all params including session_manager_url ...
        )
    )
```

## Success Criteria

1. `ao-new` creates session via API, not `session_start` event
2. `ao-resume` updates session via API
3. Events sent via `POST /sessions/{id}/events`
4. `observability.py` is deleted
5. No "observability" references in any command code
6. .jsonl files still written (backup)
7. .meta.json files still written (backup)
8. Frontend receives events via WebSocket (unchanged)

## Verification

```bash
# Start backend
cd agent-orchestrator-observability/backend && uv run python main.py &

# Watch WebSocket for events (in another terminal)
websocat ws://localhost:8765/ws

# Run ao-new
cd plugins/agent-orchestrator/skills/agent-orchestrator/commands
echo "What is 2+2?" | ./ao-new test-math

# Check session was created via API
curl http://localhost:8765/sessions | jq '.sessions[] | select(.session_name == "test-math")'

# Check events exist
curl http://localhost:8765/sessions/<session_id>/events | jq .

# Check result
./ao-get-result test-math

# Cleanup
./ao-clean test-math
```

## Rollback Plan

If issues arise, the file-based backup ensures data isn't lost:
- .meta.json contains session metadata
- .jsonl contains full event stream
- Commands can fall back to file parsing if API fails

## Final Cleanup

After verification:
1. Remove deprecated `POST /events` endpoint from backend (or keep for external integrations)
2. Remove `PATCH /sessions/{id}/metadata` endpoint (use `PATCH /sessions/{id}`)
3. Update any documentation referencing old endpoints

## Guidelines

- **Follow the instructions above** - do not add features beyond what is specified
- **Embrace KISS** - keep implementations simple and straightforward
- **Embrace YAGNI** - do not build for hypothetical future requirements
- **Ask if there is any confusion** before proceeding with implementation
