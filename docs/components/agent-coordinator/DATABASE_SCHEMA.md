# Database Schema

SQLite database schema used by the Agent Coordinator server.

## Database Location

`.agent-orchestrator/observability.db`

## Tables

### Sessions Table

Stores agent session metadata and status.

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    project_dir TEXT,
    agent_name TEXT,
    last_resumed_at TEXT,
    parent_session_id TEXT REFERENCES sessions(session_id) ON DELETE SET NULL,
    executor_session_id TEXT,
    executor_profile TEXT,
    hostname TEXT
);
```

**Columns:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `session_id` | TEXT | NO | Primary key. Coordinator-generated ID (format: `ses_{12-char-hex}`) |
| `status` | TEXT | NO | Session status: `pending`, `running`, `stopping`, `stopped`, `finished` |
| `created_at` | TEXT | NO | ISO 8601 timestamp when session was created |
| `project_dir` | TEXT | YES | Absolute path to the project directory |
| `agent_name` | TEXT | YES | Name of the agent blueprint used for this session |
| `last_resumed_at` | TEXT | YES | ISO 8601 timestamp when session was last resumed |
| `parent_session_id` | TEXT | YES | ID of the parent session (foreign key, for hierarchy tracking) |
| `executor_session_id` | TEXT | YES | Framework's session ID (e.g., Claude SDK UUID) |
| `executor_profile` | TEXT | YES | Profile used by executor (e.g., `coding`) |
| `hostname` | TEXT | YES | Machine hostname where session is running |

**Note:** `execution_mode` is stored in the **runs** table, not sessions. Each run can have a different execution mode, allowing execution behavior to vary per-run.

**Indexes:**
- Primary key index on `session_id`
- Index on `executor_session_id` for executor binding lookups
- Index on `hostname` for affinity routing

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
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
```

**Columns:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Auto-incrementing primary key |
| `session_id` | TEXT | NO | Foreign key to `sessions.session_id` (cascades on delete) |
| `event_type` | TEXT | NO | Event type: `session_start`, `pre_tool`, `post_tool`, `message`, `session_stop` |
| `timestamp` | TEXT | NO | ISO 8601 timestamp when event occurred |
| `tool_name` | TEXT | YES | Name of the tool (for tool-related events) |
| `tool_input` | TEXT | YES | JSON string of tool input parameters |
| `tool_output` | TEXT | YES | JSON string of tool output/response |
| `error` | TEXT | YES | Error message (if tool execution failed) |
| `exit_code` | INTEGER | YES | Exit code (for session_stop events) |
| `reason` | TEXT | YES | Reason for session stop (e.g., "completed", "stopped") |
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
- Database is initialized on first server startup via `init_db()` in `servers/agent-coordinator/database.py`
- Tables are created with `CREATE TABLE IF NOT EXISTS`
- Indexes are created with `CREATE INDEX IF NOT EXISTS`

### Session Lifecycle
1. **Session Pending**: Session created via POST /runs with `status='pending'`
2. **Session Binding**: Executor binds via POST /sessions/{id}/bind, updates `executor_session_id`, `hostname`, `executor_type`, sets `status='running'`
3. **Events**: Insert events as they occur during execution
4. **Session End**: Update `status='finished'` (normal completion), `status='stopped'` (stop command), or `status='error'` (failure)

### Session Resumption
When resuming a session:
```sql
UPDATE sessions
SET status = 'running', last_resumed_at = ?
WHERE session_id = ?
```
This preserves existing metadata (project_dir, agent_name, executor info) when resuming.

### Session Binding
When an executor starts running a session:
```sql
UPDATE sessions
SET status = 'running',
    executor_session_id = ?,
    hostname = ?,
    executor_type = ?,
    project_dir = COALESCE(?, project_dir)
WHERE session_id = ?
```

### Session Affinity
Session affinity information is used to route resume requests to the correct runner:
```sql
SELECT hostname, project_dir, executor_type, executor_session_id
FROM sessions
WHERE session_id = ?
```

## Related Documentation

- **[API.md](./API.md)** - Complete REST API reference
- **[DATA_MODELS.md](./DATA_MODELS.md)** - Pydantic models and validation
- **[RUNS_API.md](./RUNS_API.md)** - Runs API for distributed execution
