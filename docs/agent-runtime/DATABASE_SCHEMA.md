# Database Schema

SQLite database schema used by the Agent Runtime server.

## Database Location

`.agent-orchestrator/observability.db`

## Tables

### Sessions Table

Stores agent session metadata and status.

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    session_name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    project_dir TEXT,
    agent_name TEXT
);
```

**Columns:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `session_id` | TEXT | NO | Primary key. Unique identifier for the session (from Claude SDK) |
| `session_name` | TEXT | NO | Human-readable session name |
| `status` | TEXT | NO | Session status: `running`, `finished`, `error` |
| `created_at` | TEXT | NO | ISO 8601 timestamp when session was created |
| `project_dir` | TEXT | YES | Absolute path to the project directory |
| `agent_name` | TEXT | YES | Name of the agent definition used for this session |

**Indexes:**
- Primary key index on `session_id`

### Events Table

Stores all events that occur during agent sessions (tool calls, messages, etc).

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    tool_name TEXT,
    tool_input TEXT,
    tool_output TEXT,
    error TEXT,
    exit_code INTEGER,
    reason TEXT,
    role TEXT,
    content TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

**Columns:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Auto-incrementing primary key |
| `session_id` | TEXT | NO | Foreign key to `sessions.session_id` |
| `event_type` | TEXT | NO | Event type: `session_start`, `pre_tool`, `post_tool`, `message`, `session_stop` |
| `timestamp` | TEXT | NO | ISO 8601 timestamp when event occurred |
| `tool_name` | TEXT | YES | Name of the tool (for tool-related events) |
| `tool_input` | TEXT | YES | JSON string of tool input parameters |
| `tool_output` | TEXT | YES | JSON string of tool output/response |
| `error` | TEXT | YES | Error message (if tool execution failed) |
| `exit_code` | INTEGER | YES | Exit code (for session_stop events) |
| `reason` | TEXT | YES | Reason for session stop (e.g., "completed", "error") |
| `role` | TEXT | YES | Message role: `user`, `assistant` (for message events) |
| `content` | TEXT | YES | JSON array of message content blocks |

**Indexes:**
- Primary key index on `id`
- Composite index on `(session_id, timestamp DESC)` for efficient event queries

## Event Types

### session_start
- Sent when a new agent session begins
- Fields: `session_id`, `event_type`, `timestamp`

### pre_tool
- Sent before a tool is executed
- Fields: `session_id`, `event_type`, `timestamp`, `tool_name`, `tool_input`

### post_tool
- Sent after a tool completes execution
- Fields: `session_id`, `event_type`, `timestamp`, `tool_name`, `tool_input`, `tool_output`, `error`

### message
- Sent for user and assistant messages
- Fields: `session_id`, `event_type`, `timestamp`, `role`, `content`

### session_stop
- Sent when a session ends
- Fields: `session_id`, `event_type`, `timestamp`, `exit_code`, `reason`

## JSON Fields

Several columns store JSON-encoded data:

### tool_input / tool_output
JSON object with tool parameters or results:
```json
{
  "file_path": "/path/to/file.py",
  "content": "..."
}
```

### content
JSON array of message content blocks:
```json
[
  {
    "type": "text",
    "text": "The task has been completed"
  }
]
```

## Database Operations

### Initialization
- Database is initialized on first backend startup via `init_db()` in `backend/database.py`
- Tables are created with `CREATE TABLE IF NOT EXISTS`
- Indexes are created with `CREATE INDEX IF NOT EXISTS`

### Session Lifecycle
1. **Session Start**: Insert session with `status='running'`
2. **Events**: Insert events as they occur during execution
3. **Session End**: Update session `status='finished'` or `status='error'`

### Conflict Resolution
When resuming a session:
```sql
INSERT INTO sessions (session_id, session_name, status, created_at)
VALUES (?, ?, 'running', ?)
ON CONFLICT(session_id) DO UPDATE SET status = 'running'
```
This preserves existing metadata (project_dir, agent_name) when resuming.

## Related Documentation

- **`BACKEND_API.md`** - Backend HTTP API endpoints
- **`DATA_MODELS.md`** - Pydantic models and validation
- **`FRONTEND_API.md`** - Frontend data fetching patterns
