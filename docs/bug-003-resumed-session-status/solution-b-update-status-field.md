# Solution B: Add Status Field to update_session

## Approach

Extend `session_client.update_session()` to accept a `status` parameter, then update the status to `"running"` when resuming a session.

## Implementation

### Step 1: Extend SessionClient

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/session_client.py`

```diff
  def update_session(
      self,
      session_id: str,
      session_name: Optional[str] = None,
-     last_resumed_at: Optional[str] = None
+     last_resumed_at: Optional[str] = None,
+     status: Optional[str] = None
  ) -> Dict[str, Any]:
      """Update session metadata."""
      payload = {}
      if session_name is not None:
          payload["session_name"] = session_name
      if last_resumed_at is not None:
          payload["last_resumed_at"] = last_resumed_at
+     if status is not None:
+         payload["status"] = status

      response = requests.patch(
          f"{self.base_url}/sessions/{session_id}/metadata",
          json=payload,
          timeout=10
      )
      response.raise_for_status()
      return response.json()
```

### Step 2: Update Backend Endpoint

**File:** `agent-orchestrator-observability/backend/main.py`

```diff
  class SessionMetadataUpdate(BaseModel):
      session_name: Optional[str] = None
      last_resumed_at: Optional[str] = None
+     status: Optional[str] = None

  @app.patch("/sessions/{session_id}/metadata")
  async def update_metadata(session_id: str, metadata: SessionMetadataUpdate):
      # ... existing code ...
+     if metadata.status is not None:
+         session["status"] = metadata.status
      # ... broadcast session_updated ...
```

### Step 3: Use in Resume Flow

**File:** `plugins/agent-orchestrator/skills/agent-orchestrator/commands/lib/claude_client.py`

```diff
  else:
      # Resume: update last_resumed_at and status
      session_client.update_session(
          session_id=session_id,
-         last_resumed_at=datetime.now(UTC).isoformat()
+         last_resumed_at=datetime.now(UTC).isoformat(),
+         status="running"
      )
```

## Frontend Handling

No changes needed. The existing `session_updated` handler in `useSessions.ts:42-45` will receive the updated session with `status: "running"`:

```typescript
else if (message.type === 'session_updated' && message.session) {
    setSessions((prev) =>
      prev.map((s) => (s.session_id === message.session!.session_id ? message.session! : s))
    );
}
```

## Pros

- **Direct status update** - Status is explicitly set, not inferred from events
- **Flexible API** - Can update status in other contexts too
- **No new event types** - Uses existing WebSocket message

## Cons

- **More changes required** - Needs updates in 3 files
- **No event record** - Resume isn't recorded in session events timeline
- **Status validation** - Should validate allowed status values

## Recommendation

**Alternative option.** More comprehensive but requires more changes. Consider if you want status updates to be separate from events.
