# Phase 2: Session Client Library

## Overall Context

We are migrating the Agent Orchestrator from file-based session storage to database-backed storage via the **Agent Session Manager** service. The Python commands (`ao-*`) in `plugins/agent-orchestrator/skills/agent-orchestrator/commands/` need a client to talk to the backend API.

**Key principle:** No "observability" naming. The new client is `session_client.py`, not `observability_client.py`.

## This Phase's Goal

Create the session client library and update configuration. This provides the interface that commands will use in Phase 3.

## Prerequisites

- Phase 1 complete (backend API endpoints exist)

## Reference

Read these sections in `analysis.md`:
- "Naming Decisions" - configuration changes, env var naming
- "Phase 2: Create Session Client" - client interface specification

## Tasks

### 1. Update Configuration

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/config.py`

Remove:
- `ENV_OBSERVABILITY_ENABLED` constant
- `ENV_OBSERVABILITY_URL` constant
- `DEFAULT_OBSERVABILITY_URL` constant
- `observability_enabled` from `Config` dataclass
- `observability_url` from `Config` dataclass
- All observability-related loading logic in `load_config()`

Add:
```python
ENV_SESSION_MANAGER_URL = "AGENT_ORCHESTRATOR_SESSION_MANAGER_URL"
DEFAULT_SESSION_MANAGER_URL = "http://127.0.0.1:8765"
```

Add to `Config` dataclass:
```python
session_manager_url: str
```

Update `load_config()` to load the new env var with default.

### 2. Create Session Client

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/session_client.py`

Create new file with `SessionClient` class:

```python
"""
Session Client

HTTP client for Agent Session Manager API.
Replaces file-based session operations with API calls.
"""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC


class SessionClientError(Exception):
    """Base exception for session client errors."""
    pass


class SessionNotFoundError(SessionClientError):
    """Session does not exist."""
    pass


class SessionClient:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def create_session(
        self,
        session_id: str,
        session_name: str,
        project_dir: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new session with full metadata."""
        # POST /sessions
        pass

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details. Raises SessionNotFoundError if not found."""
        # GET /sessions/{session_id}
        pass

    def get_status(self, session_id: str) -> str:
        """Get session status: 'running', 'finished', or 'not_existent'."""
        # GET /sessions/{session_id}/status
        pass

    def get_result(self, session_id: str) -> str:
        """Get session result. Raises if not finished or not found."""
        # GET /sessions/{session_id}/result
        pass

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        # GET /sessions
        pass

    def add_event(self, session_id: str, event: Dict[str, Any]) -> None:
        """Add event to session. Handles session_stop specially on server."""
        # POST /sessions/{session_id}/events
        pass

    def update_session(
        self,
        session_id: str,
        session_name: Optional[str] = None,
        last_resumed_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update session metadata."""
        # PATCH /sessions/{session_id}
        pass

    def delete_session(self, session_id: str) -> bool:
        """Delete session and events. Returns True if deleted, False if not found."""
        # DELETE /sessions/{session_id}
        pass
```

Implementation notes:
- Use `httpx` for HTTP calls (already a dependency)
- Timeout default 5 seconds
- Raise `SessionNotFoundError` on 404 responses
- Raise `SessionClientError` on other errors
- Return parsed JSON responses

### 3. Add Helper Function

Add module-level helper for simple use:

```python
def get_client(base_url: str) -> SessionClient:
    """Get a SessionClient instance."""
    return SessionClient(base_url)
```

## Success Criteria

1. `config.py` has no "observability" references
2. `Config` dataclass has `session_manager_url` field
3. `session_client.py` exists with all methods implemented
4. Client methods handle errors gracefully
5. Existing commands still work (not migrated yet, but config doesn't break them)

## Verification

```python
# Test client manually
import sys
sys.path.insert(0, 'plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib')

from session_client import SessionClient

client = SessionClient("http://localhost:8765")

# Should work if Phase 1 is complete
session = client.create_session("test-456", "test-session", "/tmp", None)
print(session)

status = client.get_status("test-456")
print(f"Status: {status}")

sessions = client.list_sessions()
print(f"Sessions: {len(sessions)}")

client.delete_session("test-456")
```

## Notes

- Do NOT update commands yet - that's Phase 3
- Do NOT remove `observability.py` yet - that's Phase 4
- The old observability code must still work during migration

## Guidelines

- **Follow the instructions above** - do not add features beyond what is specified
- **Embrace KISS** - keep implementations simple and straightforward
- **Embrace YAGNI** - do not build for hypothetical future requirements
- **Ask if there is any confusion** before proceeding with implementation
