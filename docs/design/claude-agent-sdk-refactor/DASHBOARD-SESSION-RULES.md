# Dashboard Session Rules

Quick reference for what the dashboard allows per session status in each tab.

---

## Session Statuses

| Status | Meaning | Process? | Terminal? |
|-----------|-----------------------------------|----------|-----------|
| `pending` | Created, no executor bound yet | No | No |
| `running` | Turn actively executing | Yes | No |
| `idle` | Turn done, waiting for next input | Yes | No |
| `stopping` | Stop issued, awaiting termination | Yes | No |
| `finished` | Completed naturally or graceful shutdown | No | Yes |
| `stopped` | Force-terminated by stop command | No | Yes |
| `failed` | Process crashed (non-zero exit) | No | Yes |

---

## Sessions Tab

### Stop Button

| Status | Shown? | Behavior |
|-----------|--------|----------|
| `running` | Yes | Force-kills the process (SIGTERM/SIGKILL) -> `stopped` |
| `idle` | Yes | Graceful NDJSON shutdown -> `finished` |
| `pending` | No | - |
| `stopping` | No | Already stopping |
| `finished` | No | Already terminal |
| `stopped` | No | Already terminal |
| `failed` | No | Already terminal |

### Delete Button

| Status | Enabled? | Reason |
|-----------|----------|--------|
| `running` | No | Must stop first |
| `idle` | No | Must stop first |
| `stopping` | No | Wait for termination |
| `pending` | Yes | - |
| `finished` | Yes | - |
| `stopped` | Yes | - |
| `failed` | Yes | - |

### Stop All

Stops all sessions with status `running` or `idle`. Skips everything else.

### Delete All

Deletes only sessions with terminal status (`finished`, `stopped`, `failed`) or `pending`. Skips `running`, `idle`, `stopping`.

### Status Filter

Filters: All, Idle, Finished, Stopped, Failed, Running, Pending.

---

## Chat Tab

### Sending Messages (Resume)

Only **idle** sessions can receive new messages (resume). All other statuses either start a new session or are blocked.

| Condition | Action |
|-----------|--------|
| No session yet | Start new session |
| Session is `idle` | Resume existing session (send turn via NDJSON stdin) |
| Session is `finished` | Start new session |
| Session is `stopped` | Start new session |
| Session is `failed` | Start new session |
| Session is `error` (UI-only) | Start new session |
| Session is `running` | Blocked (input disabled, "agent is working") |
| Session is `stopping` | Blocked (input disabled) |

### Stop Button (Chat)

| Status | Can Stop? | Reason |
|-----------|-----------|--------|
| `running` | Yes | Active turn |
| `idle` | Yes | Graceful shutdown |
| `starting` | Yes | Being initialized |
| `stopping` | No | Already stopping |
| `finished` | No | Terminal |
| `error` | No | Terminal |

### Session Selector (Chat Tab)

The session selector lets the user switch between sessions or start a new chat. It only shows sessions that can be meaningfully selected.

**Excluded from list** (cannot switch to):
- `running` — active, locked
- `stopping` — transitioning
- `pending` — not yet bound

**Shown in list** (selectable):
- `idle` — can resume with new message
- `finished` — read-only, new message starts fresh session
- `stopped` — read-only, new message starts fresh session
- `failed` — read-only, new message starts fresh session

**Status indicators:**
- Blue dot: `idle` (resumable)
- Red dot: `failed`
- Gray dot: `finished`, `stopped` (terminal)

**Filter chips:** All, Idle, Finished, Stopped, Failed.

### Locked State

While a session is active (`running`, `stopping`, or `starting`), the session selector is **disabled** — the user cannot switch sessions mid-turn.

---

## Standalone Chat UI (`apps/chat-ui`)

Same rules as the dashboard Chat Tab above. Key implementation details:

- Session type includes all 7 statuses
- `run_completed` events do NOT override session status (SSE `session_updated` is authoritative)
- Resume logic: only idle sessions resume; terminal sessions start new
- `agentStatus` in the UI maps: `idle`, `starting`, `running`, `stopping`, `finished`, `error`
