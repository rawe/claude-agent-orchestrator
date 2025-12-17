# Backend Implementation TODO

This document lists all backend endpoints and features required by the unified frontend that are **not yet implemented**.

---

## Status Legend
- ❌ **Not Implemented** - Needs to be built
- ✅ **Implemented** - Already exists and working
- 🔧 **Needs Modification** - Exists but needs changes

---

## 1. Observability Backend (Port 8765)

### Existing Endpoints ✅
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/events` | POST | ✅ | Receive and broadcast events |
| `/sessions` | GET | ✅ | List all sessions |
| `/events/{session_id}` | GET | ✅ | Get events for session |
| `/sessions/{session_id}/metadata` | PATCH | ✅ | Update session metadata |
| `/sessions/{session_id}` | DELETE | ✅ | Delete session and events |
| `/ws` | WebSocket | ✅ | Real-time updates |

### New Endpoints Required ❌

#### 1.1 Stop Running Session
```
POST /sessions/{session_id}/stop
```
**Purpose:** Gracefully stop a running agent session

**Request Body:** None required

**Response:**
```json
{
  "success": true,
  "session_id": "string",
  "message": "Session stopped successfully"
}
```

**Implementation Notes:**
- This requires integration with the Claude SDK session management
- The backend needs to signal the Python CLI process to stop
- May require a new communication channel (e.g., file-based signal, process management)
- Should broadcast `session_updated` WebSocket event with status changed to `stopped`

**Complexity:** HIGH - Requires process management integration

---

### Schema Changes Required 🔧

#### 1.2 Session Status Extension
The current session status is only `running` | `finished`. Need to add:
- `stopped` - Session was manually terminated

**Database Migration:**
```sql
-- Update status column to allow new values
-- No actual migration needed if status is TEXT type
-- Just ensure Python code accepts 'stopped' as valid
```

**Backend Code Changes:**
- Update Session model to accept `stopped` status
- Update status validation logic
- When session is stopped via new endpoint, set status to `stopped`

---

## 2. Document Server Extensions (Port 8766)

### Existing Endpoints ✅
| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | ✅ |
| `/documents` | POST | ✅ |
| `/documents` | GET | ✅ |
| `/documents/{id}/metadata` | GET | ✅ |
| `/documents/{id}` | GET | ✅ |
| `/documents/{id}` | DELETE | ✅ |

### New Endpoints Required ❌

#### 3.1 Get All Tags
```
GET /documents/tags
```

**Purpose:** Get all unique tags across all documents with counts

**Response:**
```json
{
  "tags": [
    { "name": "ai", "count": 15 },
    { "name": "review", "count": 8 },
    { "name": "config", "count": 3 }
  ]
}
```

**Implementation:**
- Query all documents
- Aggregate tags
- Return sorted by count (descending)

**Complexity:** LOW

#### 3.2 Update Document Metadata
```
PATCH /documents/{id}
```

**Purpose:** Update tags and/or description of existing document

**Request:**
```json
{
  "tags": ["ai", "review", "updated"],
  "description": "Updated description"
}
```

**Response:** Full DocumentResponse object

**Implementation Notes:**
- Only update provided fields
- Validate tag format (alphanumeric + hyphens)
- Update `updated_at` timestamp

**Complexity:** LOW

---

## 3. Data Model Alignment

### 3.1 Session Model Changes

**Current:**
```python
{
  "session_id": str,
  "session_name": str,
  "status": "running" | "finished",
  "created_at": str,
  "project_dir": str | None,
  "agent_name": str | None
}
```

**Required:**
```python
{
  "session_id": str,
  "session_name": str,
  "status": "running" | "finished" | "stopped",  # Add stopped
  "created_at": str,
  "modified_at": str,  # Add this field (last activity/resumption)
  "project_dir": str | None,
  "agent_name": str | None
}
```

**Changes:**
- Add `modified_at` field (or rename existing if present)
- Add `stopped` status option

### 3.2 Document Model Alignment

**Current field:** `content_type`
**Design field:** `mime_type`

**Decision:** Keep `content_type` in backend, frontend will map to `mime_type` for display.

---

## 4. WebSocket Events

### Existing Events ✅
- `init` - Initial state with all sessions
- `event` - New event received
- `session_updated` - Session metadata updated
- `session_deleted` - Session deleted

### Potentially Needed Events 🔧

#### 4.1 Session Stopped Event
When session is stopped via new `/stop` endpoint:
```json
{
  "type": "session_updated",
  "session": {
    "session_id": "...",
    "status": "stopped",
    ...
  }
}
```

This should work with existing `session_updated` event type.

---

## 5. Implementation Priority

### Phase 1: Minimum for Frontend Demo
1. ❌ `GET /documents/tags` - Easy, enables tag filtering
2. ❌ `PATCH /documents/{id}` - Easy, enables metadata updates (V1 shows but doesn't edit)

### Phase 2: Session Control
3. 🔧 Add `stopped` status to session model
4. ❌ `POST /sessions/{id}/stop` - Complex, requires process management

---

## 6. Configuration

### Environment Variables

```bash
# Agent Coordinator (unified service - sessions + agent blueprints)
AGENT_ORCHESTRATOR_PROJECT_DIR=/path/to/project
```

### Frontend Environment Variables

```bash
VITE_AGENT_ORCHESTRATOR_API_URL=http://localhost:8765  # Sessions + Agent blueprints
VITE_DOCUMENT_SERVER_URL=http://localhost:8766  # Document store
```

---

## 7. Notes for Frontend Development

While these backend features are being implemented, the frontend will:

1. **Sessions Tab:**
   - Works with existing backend ✅
   - Stop button shown but disabled/mocked until backend ready
   - Status mapping: `running` → Running, `finished` → Finished, `stopped` → Stopped

2. **Documents Tab:**
   - Works with existing backend ✅
   - Tag filter: Will fetch all documents and compute tags client-side until `/tags` endpoint ready
   - Metadata editing: Disabled in V1 anyway

3. **Agent Manager Tab:**
   - Uses Agent Coordinator API at port 8765
   - All CRUD operations functional

---

**Document Version:** 1.0
**Created:** 2025-01-24
**Last Updated:** 2025-01-24
