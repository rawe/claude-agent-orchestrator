# Agent Orchestrator Framework - Unified Frontend Design (V1)

## Executive Summary

This document outlines the **Version 1** design for a comprehensive, modern frontend that unifies all Agent Orchestrator Framework capabilities into a single, cohesive interface. The frontend provides both **passive monitoring** (observability) and **active control** (agent management, document/context management).

### Core Principles
- **Real-time monitoring** of agent sessions with WebSocket streaming
- **Active control** over agent lifecycle (stop, delete)
- **Context management** (document management for agent-created/uploaded documents)
- **Agent definition management** (CRUD operations on agent configs)
- **Desktop-first UI** with React + TypeScript
- **Modular architecture** for easy extension

### V1 Scope
This is a **focused, production-ready release** with:
- Essential features only (deferred nice-to-haves to V2)
- Desktop-optimized (no mobile responsive design)
- Single theme (no dark mode)
- Manual testing (no automated test suite)
- Simple, clean implementation

---

## Technology Stack

### Frontend
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **State Management**: React Context API + Custom Hooks
- **Routing**: React Router v6
- **Real-time**: WebSocket connection with auto-reconnect
- **HTTP Client**: Axios with interceptors
- **UI Components**:
  - Tailwind CSS for styling (utility-first)
  - Headless UI or Radix UI for accessible components
  - React Markdown for rendering
  - Monaco Editor for code/config editing (system prompt editor)
- **Icons**: Lucide React or Heroicons
- **Data Tables**: TanStack Table (formerly React Table)
- **Forms**: React Hook Form + Zod validation
- **Notifications**: React Hot Toast or Sonner

### Backend Requirements

> ⚠️ **Backend architecture is not finalized.** The current separation is provisional. A dedicated session is needed to properly design the backend architecture, especially regarding two-way communication between frontend ↔ observability backend ↔ Python CLI commands ↔ Claude Code sessions via hooks.

**For V1, assumed backend structure:**

1. **Observability Backend (port 8765)** - Extended with:
   - `POST /sessions/{id}/stop` - Stop running sessions
   - `DELETE /sessions/{id}` - Delete sessions
   - Event-driven (WebSocket pushes updates to frontend)

2. **Agent Manager Service (new, separate port TBD)** - Handles:
   - Agent definition CRUD (`/agents/*` endpoints)
   - `GET /agents`, `POST /agents`, `PATCH /agents/{name}`, `DELETE /agents/{name}`
   - `PATCH /agents/{name}/status` - Activate/deactivate

3. **Document Server (port 8766)** - Extended with:
   - `GET /documents/tags` - Get all unique tags with counts
   - `PATCH /documents/{id}` - Update metadata (tags/description)
   - `DELETE /documents/{id}` - Delete document

---

## Application Architecture

### High-Level Structure

```
agent-orchestrator-frontend/
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── common/          # Buttons, modals, forms, etc.
│   │   ├── layout/          # Header, sidebar, navigation
│   │   └── features/        # Feature-specific components
│   │
│   ├── pages/               # Main route pages
│   │   ├── AgentSessions/   # Tab 1: Agent monitoring
│   │   ├── Documents/       # Tab 2: Context management
│   │   └── AgentManager/    # Tab 3: Agent definition management
│   │
│   ├── hooks/               # Custom React hooks
│   │   ├── useWebSocket.ts
│   │   ├── useSessions.ts
│   │   ├── useDocuments.ts
│   │   └── useAgentDefinitions.ts
│   │
│   ├── services/            # API clients
│   │   ├── sessionService.ts
│   │   ├── documentService.ts
│   │   └── agentService.ts
│   │
│   ├── types/               # TypeScript interfaces
│   │   ├── session.ts
│   │   ├── document.ts
│   │   ├── agent.ts
│   │   └── events.ts
│   │
│   ├── contexts/            # React Context providers
│   │   ├── WebSocketContext.tsx
│   │   └── NotificationContext.tsx
│   │
│   ├── utils/               # Utility functions
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   │
│   ├── App.tsx              # Main app component
│   ├── main.tsx             # Entry point
│   └── router.tsx           # Route definitions
│
├── public/                  # Static assets
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── README.md
```

---

## Navigation & Layout

### Main Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Header (Fixed)                                              │
│  • Logo & Title                                              │
│  • WebSocket Connection Indicator                           │
│  • (Future: Notifications, Help)                            │
└─────────────────────────────────────────────────────────────┘
┌──────────┬──────────────────────────────────────────────────┐
│          │                                                  │
│  Tab Nav │                                                  │
│  (Left   │          Main Content Area                       │
│  Sidebar)│          (Tab-specific content)                  │
│          │                                                  │
│ [⚫]     │                                                  │
│ Agent    │                                                  │
│ Sessions │                                                  │
│          │                                                  │
│ Documents│                                                  │
│          │                                                  │
│ Agent    │                                                  │
│ Manager  │                                                  │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

### Header Component

**Elements:**
- **Logo/Title**: "Agent Orchestrator Framework"
- **WebSocket Connection Indicator**:
  - Simple text or icon: "🔌 Connected" / "⚠️ Disconnected"
  - Shows WebSocket connection status only (not REST endpoints)
  - No traffic light system, just binary status

**Technical:**
- Fixed position, sticky header
- Connection status from WebSocketContext

### Sidebar Navigation

**Features:**
- **Collapsible**: Can collapse completely to left to maximize content width
- **Toggle button**: Arrow/hamburger to expand/collapse
- **When collapsed**: Shows only icons (with tooltips on hover)
- **When expanded**: Shows icons + labels
- **Three tabs**:
  1. Agent Sessions (monitoring icon)
  2. Documents (file icon)
  3. Agent Manager (settings/gear icon)

**Technical:**
- State persisted in component (not localStorage in V1)
- Smooth animation on collapse/expand
- CSS transitions for width changes

---

## Tab 1: Agent Sessions (Observability)

### Purpose
Real-time monitoring and control of active and historical agent sessions.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar                                                      │
│  • Search/Filter controls                                    │
│  • Sort dropdown                                             │
└─────────────────────────────────────────────────────────────┘
┌──────────────┬──────────────────────────────────────────────┐
│              │                                              │
│  Session     │  Event Timeline                              │
│  List        │                                              │
│  (Sidebar)   │  (Selected session events)                   │
│              │                                              │
│  • Session 1 │  ┌────────────────────────────────────────┐ │
│    🟢 Running│  │ 14:32 SESSION_START                   │ │
│              │  │ Session: code-review-1                │ │
│  • Session 2 │  │ Agent: code-reviewer                  │ │
│    ✅ Finished                                              │ │
│              │  └────────────────────────────────────────┘ │
│  • Session 3 │                                              │
│    🛑 Stopped │  ┌────────────────────────────────────────┐ │
│              │  │ 14:33 PRE_TOOL                        │ │
│              │  │ Tool: Read                             │ │
│              │  │ Input: {file_path: "/src/app.ts"}     │ │
│              │  │ [Expand ▼]                            │ │
│              │  └────────────────────────────────────────┘ │
│              │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

### Components

#### 1.1 Session List Sidebar

**Purpose**: Display all sessions with status and quick info

**Session Card Fields:**
- **Session Name** (large, prominent) - most important
  - If no name, show session_id instead
- **Session ID** (smaller, below name)
  - Copyable to clipboard (click icon)
- **Status Indicator**:
  - 🟢 **Running** (green)
  - ✅ **Finished** (blue)
  - 🛑 **Stopped** (red) - manually terminated
  - ⚠️ **Not Running** (yellow) - can be resumed
- **Agent Name** (badge, if present)
  - Only shown if agent was used
- **Project Directory**:
  - Show last folder name only
  - On hover: show full path in tooltip
  - Click icon to copy full path to clipboard
- **Created** (datetime, smaller text)
  - Full timestamp
- **Modified** (datetime, smaller text)
  - Last resumption time (last active time)

**Actions per Session:**
- **Running**: Stop, Delete
- **Finished**: Delete only
- **Stopped**: Delete only
- **Not Running**: Delete only

**Filters:**
- Status filter (All, Running, Finished, Stopped, Not Running)
- Agent type filter (dropdown of all agents)
- Search by session name/ID

**Sorting:**
- **Modified (newest first)** - DEFAULT
- Modified (oldest first)
- Created (newest first)
- Created (oldest first)

**Notes:**
- ❌ NO "New Session" button (sessions created via CLI only)
- ❌ NO resume feature in V1 UI
- ❌ NO right-click context menu (just visible action buttons)
- ❌ NO virtual scrolling (add if performance issues)
- ❌ NO inline name editing

**Technical:**
- Real-time updates via WebSocket
- Standard list rendering (no virtualization)

#### 1.2 Event Timeline

**Purpose**: Display chronological event stream for selected session

**Event Types & Display:**

**A. Session Events**
- `session_start`:
  - Icon: 🚀
  - Shows: Session ID, Agent name, timestamp, project dir
  - Expandable: Full configuration
- `session_stop`:
  - Icon: 🏁
  - Shows: Reason, exit code, duration
  - Expandable: Final result/error message

**B. Tool Events**
- `pre_tool`:
  - Icon: 🔧
  - Shows: Tool name, timestamp
  - Expandable: Full input parameters (JSON viewer with syntax highlighting)
- `post_tool`:
  - Icon: ✅ (success) or ❌ (error)
  - Shows: Tool name, execution time, status
  - Expandable: Output/result (syntax-highlighted JSON/code)
  - Error: Red border, error message prominent

**C. Message Events**
- `message` (User):
  - Icon: 👤
  - Shows: Message content (markdown rendered)
  - Expandable: Raw JSON
- `message` (Assistant):
  - Icon: 🤖
  - Shows: Response content (markdown rendered)
  - Expandable: Full message blocks

**Timeline Controls (Toolbar):**
- **Filter by Event Type**: Checkboxes for Tools, Messages, Session Events
- **Expand/Collapse All**: Single toggle button
- **Auto-scroll**: Toggle (on by default for running sessions)

**Notes:**
- ❌ NO search within events
- ❌ NO export functionality
- ❌ NO time range filter
- ❌ NO virtual scrolling (add if performance issues)

**Technical:**
- WebSocket streaming with automatic reconnection
- Syntax highlighting (Prism.js or highlight.js)
- Markdown rendering (react-markdown)

#### 1.3 Session Control Actions

**Stop Session:**
- Button visible for running sessions
- Confirmation modal: "Stop this session? This will terminate it immediately."
- API: `POST /sessions/{session_id}/stop`
- Backend pushes event → frontend updates status to "stopped"

**Delete Session:**
- Button visible for all sessions
- Confirmation modal: "Delete this session? This cannot be undone."
- API: `DELETE /sessions/{session_id}`
- Backend pushes event → frontend removes from list

**Event-Driven Pattern:**
1. Frontend sends request (stop/delete)
2. Backend processes
3. Backend pushes WebSocket event
4. Frontend updates UI reactively

---

## Tab 2: Documents (Context Management)

### Purpose
Manage context documents created by agents or uploaded manually. Provides search, filtering, viewing, and CRUD operations.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar                                                      │
│  • "Upload Document" button                                  │
│  • Search bar (filename)                                     │
│  • Tag filter (searchable multi-select dropdown)             │
│  • Sort dropdown                                             │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Document Table View                                          │
│                                                               │
│ | Icon | Doc ID | Filename    | Tags      | Created | Size ||
│ |------|--------|-------------|-----------|---------|-------||
│ | 📄   | abc123 | analysis.md | ai,review | 2h ago  | 45KB ||
│ | 📊   | def456 | data.json   | config    | 1d ago  | 12KB ||
│ | 📝   | ghi789 | report.txt  | summary   | 3d ago  | 8KB  ||
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Components

#### 2.1 Document Toolbar

**Features:**
- **Upload Button**: Opens upload modal
- **Search Bar**:
  - Searches filenames only (not content)
  - Real-time search with debouncing (300ms)
- **Tag Filter**:
  - Searchable multi-select dropdown (Headless UI Combobox)
  - Type to filter tags
  - Shows matching tags as you type
  - Selected tags shown as badges
  - AND logic (document must have ALL selected tags)
  - Backend endpoint: `GET /documents/tags` (returns all unique tags with counts)
- **Sort Dropdown**:
  - Created (newest first) - default
  - Created (oldest first)
  - Filename (A-Z)
  - Filename (Z-A)
  - Size (largest first)
  - Size (smallest first)

**Notes:**
- ❌ NO grid view toggle (table only)
- ❌ NO advanced search syntax

#### 2.2 Document Table View

**Table Columns:**
1. **Icon** (file type indicator: 📄 .md, 📊 .json, 📝 .txt, etc.)
2. **Document ID** (copyable, click to copy)
3. **Filename** (sortable, clickable to preview)
4. **Tags** (colored badges, truncated if many: "tag1, tag2 +3 more")
5. **Created At** (sortable, relative time with absolute in tooltip)
6. **Size** (sortable, human-readable: KB/MB)
7. **Actions** (Delete button, Download button)

**Row Interaction:**
- **Click row**: Opens preview modal

**Empty State:**
- Illustration + text: "No documents yet. Upload your first document or agents will create them."
- "Upload Document" button

**Notes:**
- ❌ NO "Created By" column (not in backend yet, defer to V2)
- ❌ NO bulk operations (checkboxes, multi-delete)
- ❌ NO right-click context menu
- ❌ NO virtual scrolling

**Technical:**
- TanStack Table for sorting/filtering
- Standard pagination (50 items per page) or simple infinite scroll
- Skeleton loaders during fetch

#### 2.3 Document Preview Modal

**Layout**: Large centered modal overlay

**Sections:**

**A. Header**
- Filename (large, prominent)
- Actions (icon buttons):
  - 📥 Download
  - 🗑️ Delete (with confirmation)
  - ❌ Close modal

**B. Metadata**
- **Document ID**: Copyable
- **Tags**: Display only (not editable in V1)
- **Description**: Display only (if present)
- **Created At**: Full timestamp
- **File Size**: KB/MB
- **MIME Type**: Display
- **Checksum**: SHA256 hash (copyable, for verification)

**C. Content Preview with Renderers**

**Markdown files (.md):**
- Toggle button: "Raw" ↔ "Rendered"
- Raw: Plain text display
- Rendered: Markdown rendering (react-markdown)

**JSON files (.json):**
- Toggle button: "Raw" ↔ "Pretty"
- Raw: Original JSON string
- Pretty: Formatted JSON with syntax highlighting

**Other files:**
- "Preview not available" message
- Download button

**Detection:** By file extension only

**Notes:**
- ❌ NO metadata editing
- ❌ NO "Copy URL" feature
- ❌ NO related information section
- ❌ NO image/PDF viewer support

**Technical:**
- Lazy loading of content (fetch on modal open)
- Markdown rendering (react-markdown)
- JSON syntax highlighting (Prism.js)

#### 2.4 Upload Document Modal

**Form Fields:**

1. **File Upload** (required)
   - Drag-and-drop zone
   - File browser button
   - Multiple file support
   - File size limit display (e.g., "Max 50MB per file")
   - Preview list of selected files

2. **Tags** (optional)
   - Tag input (press Enter to add)
   - Autocomplete from existing tags
   - Colored badges for added tags

3. **Description** (optional)
   - Textarea (500 char limit)
   - Placeholder: "Describe this document..."

**Actions:**
- "Upload" (primary, shows progress)
- "Cancel"

**Upload Progress:**
- Per-file progress bars
- Success/error indicators
- Retry button for failed uploads (optional)

**Notes:**
- ❌ NO replace existing option
- ❌ NO private/public toggle

**Technical:**
- Multipart form data upload
- Progress tracking (axios onUploadProgress)
- API: `POST /documents`

---

## Tab 3: Agent Manager

### Purpose
Create, edit, view, and delete agent definitions (blueprints for creating agent sessions).

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar                                                      │
│  • "New Agent" button                                        │
│  • Search bar (name, description)                            │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Agent Table View                                             │
│                                                               │
│ | Name          | Description      | Capabilities | Status ||
│ |---------------|------------------|--------------|--------||
│ | code-reviewer | Reviews code...  | github,eslint| Active ||
│ | data-analyst  | Analyzes data... | pandas       | Active ||
│ |               |                  |              | [Edit] ||
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Components

#### 3.1 Agent List View

**Display Mode**: Table only

**Table Columns:**
1. **Name** (sortable, clickable to edit)
2. **Description** (truncated with "..." and full text in tooltip)
3. **Capabilities** (badges for MCP servers + skills, truncated: "github, eslint +2 more")
4. **Status** (Active/Inactive badge)
5. **Actions** (Edit, Delete buttons)

**Empty State:**
- "No agents yet. Create your first specialized agent."
- "New Agent" button

**Notes:**
- ❌ NO statistics column (total sessions, success rate, etc.)
- ❌ NO custom icons (all agents use same icon or no icon)
- ❌ NO card view
- ❌ NO duplicate action

**Technical:**
- API: `GET /agents`
- TanStack Table for sorting
- Standard list rendering

#### 3.2 New/Edit Agent Modal

**Layout**: Large modal overlay

**Modal Sections (Vertical Layout):**

**A. Basic Information**
1. **Agent Name** (required)
   - Text input
   - Validation: unique, alphanumeric + hyphens
   - Example: `code-reviewer`, `data-analyst`

2. **Description** (required)
   - Textarea (250 chars)
   - Example: "Reviews pull requests and suggests improvements"

**B. System Prompt** (required)
- **Tabbed Editor**:
  - **Tab 1: "Edit"** - Monaco Editor for raw markdown
    - Markdown syntax highlighting
    - Line numbers
    - Search & replace
  - **Tab 2: "Preview"** - Rendered markdown view
    - Full markdown rendering
    - Read-only
- Switch between tabs to edit or preview

**C. Capabilities Configuration**

**MCP Servers:**
- Predefined list (hardcoded in frontend)
- Simple checkboxes (multi-select)
- No configuration editing per server

**Skills:**
- Predefined list (hardcoded in frontend)
- Simple checkboxes (multi-select)

**Example Lists:**
```typescript
const MCP_SERVERS = [
  { name: 'github', label: 'GitHub' },
  { name: 'filesystem', label: 'Filesystem' },
  { name: 'postgres', label: 'PostgreSQL' },
  // ... etc
];

const SKILLS = [
  { name: 'pdf', label: 'PDF Handler' },
  { name: 'xlsx', label: 'Excel Handler' },
  // ... etc
];
```

**Actions:**
- "Save Agent" (primary)
- "Cancel"

**Validation:**
- Name uniqueness check (async API call)
- System prompt not empty
- At least one capability selected (warning, not blocking)

**Notes:**
- ❌ NO icon/emoji picker
- ❌ NO advanced settings (model, timeout, temperature)
- ❌ NO template snippets
- ❌ NO AI assist
- ❌ NO autosave draft
- ❌ NO "Save & Create Session" action
- ❌ NO add custom MCP server/skill

**Technical:**
- Monaco Editor embedded in tab
- Markdown rendering (react-markdown) in preview tab
- API: `POST /agents` (create), `PATCH /agents/{name}` (update)

#### 3.3 Agent Actions

**Edit:**
- Click agent name or Edit button
- Opens agent editor modal with current values

**Delete:**
- Confirmation modal: "Delete agent 'code-reviewer'? This cannot be undone."
- Frontend sends `DELETE /agents/{name}`
- Backend responds with success/error
- If error (e.g., "has active sessions"), show error message
- If success, remove from list

**Activate/Deactivate:**
- Toggle button or action
- API: `PATCH /agents/{name}/status`
- Inactive agents still visible but with "Inactive" badge
- Inactive agents not available for new session creation (CLI checks this)

**Notes:**
- ❌ NO agent details view (separate page/tabs)
- ❌ NO session history view
- ❌ NO import/export
- ❌ NO versioning
- ❌ NO duplicate

---

## Supporting Components & Features

### 4.1 WebSocket Connection Management

**Purpose**: Maintain real-time connection to backend for live updates

**Features:**
- Auto-connect on app load
- Auto-reconnect on disconnect (exponential backoff: 1s, 2s, 4s, 8s, max 30s)
- Connection status indicator in header
- NO HTTP polling fallback

**Technical:**
- WebSocketContext provider wraps entire app
- Custom `useWebSocket` hook for subscribing to events
- Event types: `session_status_changed`, `session_deleted`, `event_new`, `document_uploaded`, etc.

**Implementation:**
```typescript
interface WebSocketContextValue {
  connected: boolean;
  subscribe: (eventType: string, callback: (data: any) => void) => void;
  unsubscribe: (eventType: string, callback: (data: any) => void) => void;
}
```

### 4.2 Notification System

**Purpose**: Display toast notifications and modals for user feedback

**Toast Notifications** (React Hot Toast or Sonner):
- **Success**: Green, checkmark icon
- **Error**: Red, X icon
- **Warning**: Yellow, ! icon
- **Info**: Blue, i icon
- Auto-dismiss after 5 seconds
- Click to dismiss
- Stack multiple notifications

**Modal Dialogs:**
- For critical errors requiring user attention
- Confirmation modals for destructive actions (delete)
- Must be manually dismissed

**Example Usage:**
```typescript
const { showSuccess, showError } = useNotification();
showSuccess("Document uploaded successfully!");
showError("Failed to stop session: " + error.message);
```

### 4.3 Error Handling & Loading States

**Error Boundaries:**
- React error boundaries for major sections
- Fallback UI: "Something went wrong" + "Retry" button

**Loading States:**
- Skeleton loaders for lists/tables
- Spinner for button actions (loading state)
- Progress bars for uploads

**Empty States:**
- Simple text + icon
- Primary action button

---

## Data Flow & State Management

### State Architecture

**Global State** (React Context):
- `WebSocketContext`: Connection status, event subscriptions
- `NotificationContext`: Toast notifications

**Server State** (React Query or manual with useEffect):
- Sessions: `useSessions()`, `useSession(id)`
- Documents: `useDocuments()`, `useDocument(id)`
- Agents: `useAgents()`, `useAgent(name)`
- Automatic caching, refetching

**Component State** (useState/useReducer):
- Form inputs
- UI toggles (modals, dropdowns, expanded states)
- Local filters

### Data Fetching Patterns

**Initial Load:**
1. Fetch data on component mount
2. Show skeleton loaders
3. Render data when ready

**Real-time Updates:**
1. WebSocket event received
2. Update cache/state
3. UI re-renders

**Optimistic Updates:**
1. User action (e.g., delete)
2. Immediately update UI
3. Send API request
4. If fails, rollback + show error

---

## API Requirements

### New Endpoints Needed

**Agent Management API** (new service):

```typescript
GET    /agents                      // List all agents
GET    /agents/{name}               // Get agent details
POST   /agents                      // Create agent
PATCH  /agents/{name}               // Update agent
DELETE /agents/{name}               // Delete agent
PATCH  /agents/{name}/status        // Activate/deactivate
```

**Session Control API** (extend observability backend):

```typescript
POST   /sessions/{id}/stop          // Stop running session
DELETE /sessions/{id}                // Delete session
```

**Document API Enhancements** (extend document server):

```typescript
PATCH  /documents/{id}              // Update tags/description
GET    /documents/tags              // Get all unique tags with counts
```

---

## Configuration

### Environment Variables

**Required:**
- `VITE_OBSERVABILITY_BACKEND_URL` - Default: `http://localhost:8765`
- `VITE_DOCUMENT_SERVER_URL` - Default: `http://localhost:8766`
- `VITE_AGENT_MANAGER_URL` - Default: `http://localhost:8767` (TBD)

**Example `.env` file:**
```bash
VITE_OBSERVABILITY_BACKEND_URL=http://localhost:8765
VITE_DOCUMENT_SERVER_URL=http://localhost:8766
VITE_AGENT_MANAGER_URL=http://localhost:8767
```

**No UI settings panel** - all configuration via environment variables at build/deploy time.

---

## Design Principles & Constraints

### V1 Scope Decisions

**Desktop-First:**
- Optimized for desktop (1024px+ / 1920px typical)
- No mobile responsive design
- No tablet optimizations

**Single Theme:**
- Light theme only
- No dark mode
- No theme switching

**Simplified Features:**
- No keyboard shortcuts
- No virtual scrolling (add if performance issues)
- No persistence (localStorage) - fresh state on reload
- No polling fallback - WebSocket only
- Manual testing only - no automated tests

**Minimal Settings:**
- Backend URLs via environment variables
- No user-facing settings panel
- No runtime configuration

**Event-Driven:**
- Frontend requests actions
- Backend processes and pushes events
- Frontend updates reactively
- No polling, no optimistic assumptions

---

## File Structure

```
agent-orchestrator-frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Badge.tsx
│   │   │   └── Spinner.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   └── Sidebar.tsx
│   │   └── features/
│   │       ├── sessions/
│   │       │   ├── SessionList.tsx
│   │       │   ├── SessionCard.tsx
│   │       │   ├── EventTimeline.tsx
│   │       │   └── EventCard.tsx
│   │       ├── documents/
│   │       │   ├── DocumentTable.tsx
│   │       │   ├── DocumentPreview.tsx
│   │       │   └── UploadModal.tsx
│   │       └── agents/
│   │           ├── AgentTable.tsx
│   │           ├── AgentEditor.tsx
│   │           └── SystemPromptEditor.tsx
│   │
│   ├── pages/
│   │   ├── AgentSessions.tsx
│   │   ├── Documents.tsx
│   │   └── AgentManager.tsx
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useSessions.ts
│   │   ├── useDocuments.ts
│   │   └── useAgents.ts
│   │
│   ├── services/
│   │   ├── api.ts
│   │   ├── sessionService.ts
│   │   ├── documentService.ts
│   │   └── agentService.ts
│   │
│   ├── types/
│   │   ├── session.ts
│   │   ├── event.ts
│   │   ├── document.ts
│   │   └── agent.ts
│   │
│   ├── contexts/
│   │   ├── WebSocketContext.tsx
│   │   └── NotificationContext.tsx
│   │
│   ├── utils/
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   │
│   ├── App.tsx
│   ├── main.tsx
│   └── router.tsx
│
├── public/
├── .env.example
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── README.md
```

---

## Key TypeScript Interfaces

### Session Types
```typescript
interface Session {
  session_id: string;
  session_name?: string;
  status: 'running' | 'finished' | 'stopped' | 'not_running';
  created_at: string;
  modified_at: string;  // Last resumption/activity
  project_dir?: string;
  agent_name?: string;
}

interface Event {
  id: number;
  session_id: string;
  event_type: 'session_start' | 'session_stop' | 'pre_tool' | 'post_tool' | 'message';
  timestamp: string;
  tool_name?: string;
  tool_input?: Record<string, any>;
  tool_output?: any;
  error?: string;
  exit_code?: number;
  reason?: string;
  role?: 'user' | 'assistant';
  content?: MessageContent[];
}

interface MessageContent {
  type: 'text' | 'tool_use' | 'tool_result';
  text?: string;
  name?: string;
  input?: Record<string, any>;
  content?: any;
}
```

### Document Types
```typescript
interface Document {
  id: string;
  filename: string;
  tags: string[];
  description?: string;
  created_at: string;
  size_bytes: number;
  mime_type: string;
  checksum: string;
  url: string;
}

interface DocumentUpload {
  file: File;
  tags: string[];
  description?: string;
}
```

### Agent Types
```typescript
interface Agent {
  name: string;
  description: string;
  system_prompt: string;
  mcp_servers: string[];  // Just names in V1
  skills: string[];       // Just names in V1
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
}
```

---

## Deployment

### Docker Setup

**Dockerfile:**
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Docker Compose Integration:**
```yaml
services:
  agent-orchestrator-frontend:
    build:
      context: ./agent-orchestrator-frontend
    ports:
      - "3000:80"
    environment:
      - VITE_OBSERVABILITY_BACKEND_URL=http://observability-backend:8765
      - VITE_DOCUMENT_SERVER_URL=http://document-server:8766
      - VITE_AGENT_MANAGER_URL=http://agent-manager:8767
    depends_on:
      - observability-backend
      - document-server
    networks:
      - agent-orchestrator-network
```

**Location:**
- New project: `agent-orchestrator-frontend/`
- Runs alongside existing observability frontend during transition
- Eventually replaces old frontend

---

## Summary

### What V1 Includes

**Agent Sessions Tab:**
- Real-time session monitoring
- Event timeline with expand/collapse
- Stop and delete session actions
- Status filtering and sorting
- WebSocket live updates

**Documents Tab:**
- Table view of all documents
- Upload documents manually
- Tag-based filtering (AND logic)
- Document preview with markdown/JSON renderers
- Search by filename

**Agent Manager Tab:**
- Table view of all agents
- Create/edit agents with Monaco editor
- System prompt with preview
- Simple capability selection (checkboxes)
- Activate/deactivate agents

**Infrastructure:**
- React + TypeScript + Vite
- Tailwind CSS styling
- WebSocket real-time connection
- Toast notifications + modals
- Event-driven architecture
- Desktop-optimized layout
- Collapsible sidebar

### What V1 Excludes (See FRONTEND-DESIGN-V2.md)

All deferred features are documented in the separate V2 features document.

---

## Next Steps

1. ✅ Design document finalized
2. ⏭️ Set up project structure (boilerplate)
3. ⏭️ Implement backend APIs (new endpoints)
4. ⏭️ Build frontend (phased approach)
5. ⏭️ Manual testing
6. ⏭️ Deploy to Docker

---

**Document Version**: 1.0
**Release**: V1
**Last Updated**: 2025-11-24
**Author**: Claude (Agent Orchestrator Framework)
