# Unified Session & Run View

## Status

**Draft** - Feature Ideation & Design Exploration

## Overview

This document explores approaches for a new dashboard view that unifies the representation of Sessions and Runs. Currently, the dashboard has two separate views:

- **Sessions View**: Shows persistent agent conversations with event timelines
- **Runs View**: Shows transient executions (start/resume operations) with lifecycle tracking

These views reflect the same underlying activity from different perspectives. A unified view would provide a more holistic understanding of agent orchestration.

## Problem Statement

### Current Separation Creates Friction

The dual-view approach forces users to mentally correlate information across two separate screens:

| User Question | Current Experience |
|---------------|-------------------|
| "What runs executed this session?" | Navigate to Runs, filter by session ID |
| "What happened during this run?" | Navigate to Sessions, find events by timestamp |
| "Why did my session fail?" | Check Runs for errors, then Sessions for events |
| "How many times was this session resumed?" | Count runs manually in Runs view |

### Information Loss in Isolation

**Sessions View lacks:**
- Run lifecycle information (pending → claimed → started → completed)
- Run durations and timing breakdowns
- Runner assignment details
- Prompt history across multiple resumes

**Runs View lacks:**
- Real-time event streaming
- Tool call details and outputs
- Message content and assistant responses
- Session result and final output

## Use Cases

### 1. Orchestration Debugging

**Scenario**: A parent orchestrator spawned 5 child agents. One failed, but the user doesn't know why.

**Need**: See the parent session, its child runs, each child's session events, and any errors—all in one place.

### 2. Performance Analysis

**Scenario**: A session was resumed 10 times over 2 hours. The user wants to understand the execution pattern.

**Need**: Timeline showing each run's duration, gaps between runs, and what triggered each resume (callback, manual, etc.).

### 3. Run-to-Event Correlation

**Scenario**: A run completed but the session shows unexpected behavior.

**Need**: See which events occurred during which run, mapping tool calls and messages to their execution context.

### 4. Multi-Agent Monitoring

**Scenario**: An orchestrator is managing multiple parallel agents with callbacks.

**Need**: Hierarchical view showing parent-child relationships, callback status, and aggregated progress.

### 5. Session History Review

**Scenario**: Reviewing a long-running session that had multiple resume cycles over days.

**Need**: Chronological view of all activity—runs, events, prompts, results—as a single timeline.

---

## Approach 1: Session-Centric Timeline with Run Blocks

### Concept

The primary entity is the **Session**. Runs are visualized as **execution blocks** within the session's timeline. Events are grouped under their respective runs.

### Visual Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Session: orchestrator-main                                              │
│ Status: finished │ Agent: orchestrator │ Created: 2h ago                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ Run #1 (start_session) ─────────────────────────────────────────┐   │
│  │ ● Started: 2h ago  ● Duration: 5m 23s  ● Runner: runner-abc      │   │
│  │ Prompt: "Orchestrate the data pipeline..."                       │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  ○ session_start                                    10:00:00     │   │
│  │  ○ tool_call: start_agent_session (child-1)        10:00:45     │   │
│  │  ○ tool_call: start_agent_session (child-2)        10:00:46     │   │
│  │  ○ assistant: "Started 2 child agents..."          10:01:02     │   │
│  │  ○ session_stop                                     10:05:23     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─ Run #2 (resume_session) ────────────────────────────────────────┐   │
│  │ ● Started: 1h 30m ago  ● Duration: 2m 15s  ● Trigger: callback   │   │
│  │ Prompt: "## Child Result\nchild-1 completed..."                  │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  ○ session_start                                    10:35:00     │   │
│  │  ○ tool_call: get_agent_session_result             10:35:12     │   │
│  │  ○ assistant: "Retrieved result from child-1..."   10:35:45     │   │
│  │  ○ session_stop                                     10:37:15     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ... more runs ...                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Information Displayed

**Session Header:**
- Session ID, name, status badge
- Agent blueprint name
- Created/modified timestamps
- Parent session (if child)
- Project directory

**Run Block Header:**
- Run number and type (start/resume)
- Lifecycle: pending → claimed → started → completed/failed/stopped
- Duration breakdown (queue time, claim time, execution time)
- Runner assignment
- Trigger source (manual, callback, scheduled)
- Prompt (collapsible)

**Run Block Events:**
- All events that occurred during this run's execution window
- Grouped by run based on timestamp correlation
- Expandable event details

### Interactivity

| Action | Result |
|--------|--------|
| Click session header | Expand/collapse all runs |
| Click run block header | Expand/collapse run details and events |
| Click event | Show full event payload in side panel |
| Hover run block | Show timing breakdown tooltip |
| Click "View Run Details" | Open run detail modal (existing component) |
| Click prompt | Expand full prompt text |
| Click child session link | Navigate to child session |

### Pros & Cons

| Pros | Cons |
|------|------|
| Natural hierarchy (session contains runs) | Requires loading both runs and events |
| Clear run-to-event mapping | May be overwhelming for sessions with many runs |
| Shows complete session history | Complex data aggregation on frontend |
| Preserves existing session-centric mental model | Run details require extra click |

---

## Approach 2: Run-Centric View with Session Context Panel

### Concept

The primary entity is the **Run**. Sessions provide context in a persistent side panel. Events stream in real-time for the selected run.

### Visual Design

```
┌──────────────────────────────────────┬──────────────────────────────────┐
│ Runs                                 │ Session Context                  │
│ ─────────────────────────────────── │ ───────────────────────────────  │
│                                      │ orchestrator-main                │
│ ┌─────────────────────────────────┐  │ Status: running                  │
│ │ ● run_abc123 (start_session)   │  │ Agent: orchestrator              │
│ │   Session: orchestrator-main    │  │ Created: 2h ago                  │
│ │   Status: completed │ 5m 23s   │  │ Project: /path/to/project        │
│ └─────────────────────────────────┘  │                                  │
│                                      │ Run History:                     │
│ ┌─────────────────────────────────┐  │ #1 start   completed  5m 23s    │
│ │ ● run_def456 (start_session)   │  │ #2 resume  completed  2m 15s    │
│ │   Session: child-1              │  │ #3 resume  running   1m 02s ●  │
│ │   Status: completed │ 3m 10s   │  │                                  │
│ │   Parent: orchestrator-main     │  │ Children:                        │
│ └─────────────────────────────────┘  │ └─ child-1 (finished)            │
│                                      │ └─ child-2 (running)             │
│ ┌─────────────────────────────────┐  │                                  │
│ │ ○ run_ghi789 (resume_session)  │  ├──────────────────────────────────┤
│ │   Session: orchestrator-main    │  │ Events (Run #3)                  │
│ │   Status: running │ 1m 02s ●   │  │ ───────────────────────────────  │
│ │   ← SELECTED                    │  │ ○ session_start         0:00    │
│ └─────────────────────────────────┘  │ ○ tool_call: bash       0:15    │
│                                      │ ○ assistant: "Running..." 0:45  │
│ ┌─────────────────────────────────┐  │ ● streaming...                   │
│ │ ○ run_jkl012 (start_session)   │  │                                  │
│ │   Session: child-2              │  │                                  │
│ │   Status: pending │ queued     │  │                                  │
│ └─────────────────────────────────┘  │                                  │
└──────────────────────────────────────┴──────────────────────────────────┘
```

### Information Displayed

**Runs List (left panel):**
- Run ID, type (start/resume), status
- Associated session name
- Duration or queue time
- Parent session indicator
- Visual indicator for selected run

**Session Context (right panel - top):**
- Session details for selected run's session
- Run history for this session
- Child sessions (if orchestrator)
- Session result preview

**Events Stream (right panel - bottom):**
- Events filtered to selected run's time window
- Real-time streaming for running runs
- Same event detail as current SessionEvents view

### Interactivity

| Action | Result |
|--------|--------|
| Click run in list | Select run, update context panel |
| Click session name | Navigate to full session view |
| Click child session | Select a run from that session |
| Filter by status | Show only pending/running/completed runs |
| Filter by session | Show only runs for a specific session |
| Click event | Expand event details |
| Click "Run History" item | Select that run |

### Pros & Cons

| Pros | Cons |
|------|------|
| Matches operational workflow (monitoring runs) | Session context is secondary |
| Real-time focus on active runs | Harder to see full session history |
| Easy to see all current activity | Context panel can feel cramped |
| Natural for queue/execution monitoring | Requires frequent panel updates |

---

## Approach 3: Hierarchical Tree View

### Concept

Display a collapsible tree structure where Sessions are parent nodes and Runs are child nodes. Provides a bird's-eye view of the entire orchestration hierarchy.

### Visual Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Agent Activity Tree                                       [Expand All]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ▼ orchestrator-main                          finished     2h ago       │
│   │ Status: finished │ Agent: orchestrator │ 4 runs │ 2 children       │
│   │                                                                     │
│   ├─ ▶ Run #1 (start_session)               completed    5m 23s        │
│   ├─ ▶ Run #2 (resume_session)              completed    2m 15s        │
│   ├─ ▶ Run #3 (resume_session)              completed    1m 45s        │
│   ├─ ▶ Run #4 (resume_session)              completed    3m 02s        │
│   │                                                                     │
│   ├─ ▼ child-1                               finished     1h ago       │
│   │   │ Status: finished │ Agent: researcher │ 1 run                   │
│   │   │                                                                 │
│   │   └─ ▶ Run #1 (start_session)           completed    3m 10s        │
│   │                                                                     │
│   └─ ▼ child-2                               finished     45m ago      │
│       │ Status: finished │ Agent: coder │ 2 runs                       │
│       │                                                                 │
│       ├─ ▶ Run #1 (start_session)           completed    8m 45s        │
│       └─ ▶ Run #2 (resume_session)          completed    2m 30s        │
│                                                                         │
│ ▼ standalone-task                            running      15m ago      │
│   │ Status: running │ Agent: analyst │ 1 run                           │
│   │                                                                     │
│   └─ ● Run #1 (start_session)               running      15m 23s ●     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Information Displayed

**Session Node (when collapsed):**
- Session name, status, age
- Run count, child count
- Agent name

**Session Node (when expanded):**
- Full session metadata
- List of runs as child nodes
- Child sessions as nested trees

**Run Node (when collapsed):**
- Run number, type, status, duration
- Indicator for running/streaming

**Run Node (when expanded):**
- Full run details (prompt, runner, timing)
- Event list inline or in side panel

### Interactivity

| Action | Result |
|--------|--------|
| Click ▶/▼ on session | Expand/collapse session |
| Click ▶/▼ on run | Expand/collapse run details |
| Click session name | Open session detail panel |
| Click run | Open run detail panel |
| Right-click session | Context menu: Stop, Delete, View Events |
| Right-click run | Context menu: View Details, View Events |
| Drag to reorder | N/A (chronological only) |
| Search | Filter tree by session name, agent, status |

### Pros & Cons

| Pros | Cons |
|------|------|
| Clear parent-child hierarchy | Deep nesting can be hard to read |
| Compact overview of all activity | Limited detail at each level |
| Natural for orchestration patterns | Requires loading full hierarchy |
| Easy to understand relationships | Not ideal for real-time monitoring |

---

## Approach 4: Swimlane Timeline View

### Concept

Horizontal swimlanes where each session is a lane. Runs appear as blocks flowing through time. Shows the temporal relationship between concurrent sessions.

### Visual Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Timeline                    10:00    10:15    10:30    10:45    11:00  │
├─────────────────────────────────────────────────────────────────────────┤
│                               │        │        │        │        │    │
│ orchestrator-main     ████████│████    │   ████ │████    │████████│    │
│                       Run #1  │ idle   │ Run #2 │ idle   │ Run #3 │    │
│                               │        │        │        │        │    │
├─────────────────────────────────────────────────────────────────────────┤
│                               │        │        │        │        │    │
│ child-1 ──────────────────────│████████│████    │        │        │    │
│                               │ Run #1        │ (finished)             │
│                               │        │        │        │        │    │
├─────────────────────────────────────────────────────────────────────────┤
│                               │        │        │        │        │    │
│ child-2 ──────────────────────│────────│████████│██████  │        │    │
│                               │        │ Run #1 │ Run #2 │              │
│                               │        │        │        │        │    │
├─────────────────────────────────────────────────────────────────────────┤
│                               │        │        │        │        │    │
│ standalone-task ──────────────│────────│────────│────────│████████│●   │
│                               │        │        │        │ Run #1 │    │
│                               │        │        │        │        │    │
└─────────────────────────────────────────────────────────────────────────┘

Legend: ████ = run execution   ──── = session idle   ● = currently running
```

### Information Displayed

**Swimlane Header:**
- Session name
- Current status indicator
- Collapse/expand control

**Run Block:**
- Run type indicator (start vs resume)
- Duration (block width)
- Status color coding
- Hover: full run details tooltip

**Timeline Axis:**
- Time markers (configurable granularity)
- Current time indicator
- Zoom controls

### Interactivity

| Action | Result |
|--------|--------|
| Click run block | Select run, show details in side panel |
| Hover run block | Show run summary tooltip |
| Click swimlane header | Show session details |
| Scroll horizontally | Pan through time |
| Zoom in/out | Adjust time granularity |
| Click "Now" button | Jump to current time |
| Filter by status | Hide/show swimlanes by session status |
| Drag selection | Select time range for analysis |

### Pros & Cons

| Pros | Cons |
|------|------|
| Excellent for timing analysis | Complex to implement |
| Shows concurrency clearly | Less detail visible at once |
| Visual gaps show idle time | Requires good time data |
| Great for performance debugging | Can be cluttered with many sessions |
| Industry-standard pattern (Gantt) | Horizontal scrolling can be awkward |

---

## Approach 5: Unified Activity Feed

### Concept

A single chronological feed showing all activity—runs and events—interleaved. Similar to a social media timeline or activity log.

### Visual Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Activity Feed                               [Filter ▼] [Session ▼]      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 🚀 RUN STARTED                                            10:45:00 │ │
│ │ Run #3 of orchestrator-main (resume_session)                       │ │
│ │ Prompt: "## Child Result\nchild-1 completed with result..."        │ │
│ │ Runner: runner-abc123                                              │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 📥 EVENT                                                  10:45:02 │ │
│ │ orchestrator-main → session_start                                  │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 🔧 EVENT                                                  10:45:15 │ │
│ │ orchestrator-main → tool_call: get_agent_session_result            │ │
│ │ Arguments: { "session_name": "child-1" }                           │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ ✅ RUN COMPLETED                                          10:47:15 │ │
│ │ Run #3 of orchestrator-main                                        │ │
│ │ Duration: 2m 15s │ Status: completed                               │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ ❌ RUN FAILED                                             10:42:30 │ │
│ │ Run #1 of child-3 (start_session)                                  │ │
│ │ Error: "Agent blueprint not found: researcher-v2"                  │ │
│ │ Duration: 0m 45s                                                   │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ● Live updates streaming...                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Information Displayed

**Run Cards:**
- Run lifecycle events (started, completed, failed, stopped)
- Run type and session association
- Prompt preview
- Duration and status
- Error message (if failed)

**Event Cards:**
- Event type with icon
- Session association
- Event payload preview
- Timestamp

**Feed Controls:**
- Filter by activity type (runs, events, errors)
- Filter by session
- Real-time toggle
- Load more / infinite scroll

### Interactivity

| Action | Result |
|--------|--------|
| Click card | Expand full details |
| Click session name | Filter feed to this session |
| Toggle "Runs only" | Show only run lifecycle events |
| Toggle "Errors only" | Show only failures and errors |
| Click timestamp | Jump to that point in filtered timeline |
| Infinite scroll | Load older activity |
| New activity | Animates in at top of feed |

### Pros & Cons

| Pros | Cons |
|------|------|
| Simple, familiar pattern | No structural hierarchy |
| Real-time friendly | Hard to see session overview |
| Easy to implement | Context switching between sessions |
| Good for monitoring | May need heavy filtering to be useful |
| Shows everything chronologically | Overwhelming with high activity |

---

## Approach 6: Dashboard Cards with Drill-Down

### Concept

High-level dashboard with summary cards. Each card represents a session and shows run activity at a glance. Clicking drills into details.

### Visual Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Sessions Overview                                    [Grid ▢] [List ≡] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│ │ orchestrator-main    │  │ child-1              │  │ child-2         │ │
│ │ ━━━━━━━━━━━━━━━━━━━ │  │ ━━━━━━━━━━━━━━━━━━━ │  │ ━━━━━━━━━━━━━━━ │ │
│ │ ● FINISHED          │  │ ● FINISHED          │  │ ○ RUNNING       │ │
│ │                      │  │                      │  │                 │ │
│ │ Agent: orchestrator  │  │ Agent: researcher    │  │ Agent: coder    │ │
│ │ Runs: 4 ✓           │  │ Runs: 1 ✓           │  │ Runs: 2 (1 ●)   │ │
│ │ Children: 2          │  │ Parent: orch...      │  │ Parent: orch... │ │
│ │                      │  │                      │  │                 │ │
│ │ ▃▃▃▅▅▅▅▃▃▃▇▇▃▃     │  │ ▃▃▃▃▅▅▅▅▃▃▃        │  │ ▃▃▃▅▅▅▇▇●      │ │
│ │ └─ run activity ──┘  │  │ └─ run activity ──┘  │  │ └─ activity ──┘ │ │
│ │                      │  │                      │  │                 │ │
│ │ Last: 45m ago        │  │ Last: 1h ago         │  │ Active now      │ │
│ └──────────────────────┘  └──────────────────────┘  └─────────────────┘ │
│                                                                         │
│ ┌──────────────────────┐  ┌──────────────────────┐                      │
│ │ standalone-task      │  │ batch-processor      │                      │
│ │ ━━━━━━━━━━━━━━━━━━━ │  │ ━━━━━━━━━━━━━━━━━━━ │                      │
│ │ ○ RUNNING           │  │ ✗ STOPPED           │                      │
│ │                      │  │                      │                      │
│ │ Agent: analyst       │  │ Agent: batch         │                      │
│ │ Runs: 1 (1 ●)       │  │ Runs: 1 ✗           │                      │
│ │                      │  │                      │                      │
│ │ ▃▃▃▃▃▅▅▅▅●          │  │ ▃▃▅▅▅✗              │                      │
│ │                      │  │                      │                      │
│ │ Active: 15m          │  │ Stopped: 30m ago     │                      │
│ └──────────────────────┘  └──────────────────────┘                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Legend: ▃▅▇ = run activity sparkline  ● = active  ✓ = completed  ✗ = failed
```

### Information Displayed

**Session Card:**
- Session name and status badge
- Agent blueprint name
- Run count with status summary
- Parent/child relationship indicator
- Activity sparkline (mini timeline)
- Last activity timestamp

**Sparkline:**
- Compact visualization of run activity over time
- Height indicates run duration
- Color indicates status
- Animated dot for running

### Interactivity

| Action | Result |
|--------|--------|
| Click card | Open detailed session/run panel |
| Hover card | Show quick stats tooltip |
| Click status badge | Filter to sessions with this status |
| Click parent/child link | Navigate to related session |
| Toggle Grid/List | Change layout |
| Sort dropdown | Order by status, activity, created |
| Right-click card | Context menu: Stop, Delete, View Events |

### Drill-Down Panel

When a card is clicked, a slide-out panel shows:
- Full session details
- Run list with expandable details
- Event timeline for selected run
- Actions: Stop, Delete, Resume (if applicable)

### Pros & Cons

| Pros | Cons |
|------|------|
| High-level overview | Requires drill-down for details |
| Scales to many sessions | Sparkline may be too compact |
| Quick status scanning | Card layout limits info density |
| Visual activity indicators | Parent-child not immediately clear |
| Modern, dashboard feel | Two-step interaction required |

---

## Comparison Matrix

| Approach | Best For | Complexity | Real-time | Hierarchy | Detail Level |
|----------|----------|------------|-----------|-----------|--------------|
| 1. Session Timeline | Deep session analysis | Medium | ● | ●● | ●●● |
| 2. Run-Centric | Run monitoring/debugging | Medium | ●●● | ● | ●●● |
| 3. Tree View | Orchestration overview | Low | ● | ●●● | ●● |
| 4. Swimlane | Performance analysis | High | ●● | ●● | ●● |
| 5. Activity Feed | Live monitoring | Low | ●●● | ● | ●● |
| 6. Dashboard Cards | Overview + drill-down | Medium | ●● | ●● | ●●● |

## Recommendation

For a first implementation, consider a **hybrid approach** combining:

1. **Dashboard Cards (Approach 6)** as the default overview
2. **Session Timeline (Approach 1)** as the drill-down detail view

This provides:
- Quick scanning of all sessions at a glance
- Clear run activity indicators per session
- Deep drill-down when investigation is needed
- Manageable implementation complexity
- Natural progression from current separate views

### Migration Path

1. **Phase 1**: Add activity sparkline and run count to existing session cards
2. **Phase 2**: Create unified session/run detail panel (Approach 1 pattern)
3. **Phase 3**: Add timeline view (Approach 4) as optional visualization
4. **Phase 4**: Add activity feed (Approach 5) for real-time monitoring view

---

## Technical Considerations

### Data Requirements

A unified view requires:
- Joining runs with their session data
- Correlating events with runs by timestamp
- Real-time updates for both runs and events
- Efficient loading for sessions with many runs

### API Changes

May need new endpoints:
- `GET /sessions/{id}/with-runs` - Session with embedded run list
- `GET /runs?session_id={id}` - Runs filtered by session (exists)
- SSE: Include run lifecycle events in session stream

### Performance

- Pagination for sessions with many runs
- Lazy loading of events per run
- Caching of completed run data
- Virtualized lists for large datasets

## Related Documents

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Core session/run relationship
- [agent-callback-architecture.md](./agent-callback-architecture.md) - Parent-child patterns
- [ADR-001-run-session-separation.md](../adr/ADR-001-run-session-separation.md) - Design rationale
