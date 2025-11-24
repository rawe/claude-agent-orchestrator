# Agent Orchestrator Framework - Unified Frontend Design

## Executive Summary

This document outlines the design for a comprehensive, modern frontend that unifies all Agent Orchestrator Framework capabilities into a single, cohesive interface. The frontend will provide both **passive monitoring** (observability) and **active control** (agent management, document management, configuration).

### Core Principles
- **Real-time monitoring** of agent sessions with WebSocket streaming
- **Active control** over agent lifecycle (start, stop, resume, delete)
- **Document management** for agent-created documents
- **Agent definition management** (CRUD operations on agent configs)
- **Modern, responsive UI** with React + TypeScript
- **Modular architecture** for easy extension

---

## Technology Stack

### Frontend
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **State Management**: React Context API + Custom Hooks (or Zustand for complex state)
- **Routing**: React Router v6
- **Real-time**: WebSocket connections with auto-reconnect
- **HTTP Client**: Axios or Fetch API with interceptors
- **UI Components**:
  - Tailwind CSS for styling (modern, utility-first)
  - Headless UI or Radix UI for accessible components
  - React Markdown for rendering
  - Monaco Editor for code/config editing
- **Icons**: Lucide React or Heroicons
- **Data Tables**: TanStack Table (formerly React Table)
- **Forms**: React Hook Form + Zod validation
- **Notifications**: React Hot Toast or Sonner

### Backend Requirements
- Existing observability backend (Port 8765)
- Existing document server (Port 8766)
- **NEW**: Agent management API (to be integrated into observability backend or separate service)

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
│   │   ├── Documents/       # Tab 2: Document management
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
│  • Connection Status Indicator (WebSocket)                   │
│  • User Actions (Settings, Help, Notifications)             │
└─────────────────────────────────────────────────────────────┘
┌──────────┬──────────────────────────────────────────────────┐
│          │                                                  │
│  Tab     │                                                  │
│  Nav     │          Main Content Area                       │
│  (Left)  │          (Tab-specific content)                  │
│          │                                                  │
│  • Agent │                                                  │
│    Sessions                                                 │
│          │                                                  │
│  • Documents                                                │
│          │                                                  │
│  • Agent │                                                  │
│    Manager                                                  │
│          │                                                  │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

### Header Component

**Elements:**
- **Logo/Title**: "Agent Orchestrator Framework" (clickable, navigates home)
- **Connection Status**:
  - Green dot: "Connected" (all services online)
  - Yellow dot: "Partial" (some services offline)
  - Red dot: "Disconnected" (no backend connection)
  - Tooltip shows individual service status
- **Notifications Bell**: Badge count for system events
- **Settings Gear**: Configure endpoints, preferences
- **Help/Docs**: Link to documentation

**Technical:**
- Fixed position, sticky header
- Connection status uses WebSocket + HTTP health checks
- Real-time update every 5 seconds

---

## Tab 1: Agent Sessions (Observability)

### Purpose
Real-time monitoring and control of active and historical agent sessions.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar                                                      │
│  • "New Session" button                                      │
│  • Search/Filter controls                                    │
│  • View options (Auto-scroll, Expand all, etc.)             │
└─────────────────────────────────────────────────────────────┘
┌──────────────┬──────────────────────────────────────────────┐
│              │                                              │
│  Session     │  Event Timeline                              │
│  List        │                                              │
│  (Sidebar)   │  (Selected session events)                   │
│              │                                              │
│  • Session 1 │  ┌────────────────────────────────────────┐ │
│    ✓ Done    │  │ 14:32 SESSION_START                   │ │
│              │  │ Session: code-review-1                │ │
│  • Session 2 │  │ Agent: code-reviewer                  │ │
│    ▶ Running │  └────────────────────────────────────────┘ │
│              │                                              │
│  • Session 3 │  ┌────────────────────────────────────────┐ │
│    ⏸ Paused  │  │ 14:33 PRE_TOOL                        │ │
│              │  │ Tool: Read                             │ │
│              │  │ Input: {file_path: "/src/app.ts"}     │ │
│              │  │ [Expand for details ▼]                │ │
│              │  └────────────────────────────────────────┘ │
│              │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

### Components

#### 1.1 Session List Sidebar

**Purpose**: Display all sessions with status and quick info

**Features:**
- **Session Card** per session:
  - Session name (editable inline)
  - Status indicator (icon + color):
    - 🟢 Running (green)
    - ⏸️ Paused/Ready to resume (yellow)
    - ✅ Finished (blue)
    - ❌ Failed (red)
  - Agent name (badge)
  - Creation timestamp (relative time: "2h ago")
  - Project directory (collapsible, copyable)
  - Click to select → loads events
  - Right-click context menu:
    - Stop (if running) ⚠️ **NEW**
    - Delete session
    - Copy session ID

**Filters:**
- Status filter (All, Running, Finished, Failed)
- Agent type filter (dropdown of all agents)
- Date range picker
- Search by session name/ID

**Sorting:**
- Created (newest first) - default
- Status (running first)
- Agent name (alphabetical)

**Actions:**
- "New Session" button → opens modal

**Technical:**
- Virtual scrolling for large lists (react-window)
- Real-time updates via WebSocket
- Optimistic UI updates
- Infinite scroll pagination

#### 1.2 Event Timeline

**Purpose**: Display chronological event stream for selected session

**Event Types & Display:**

**A. Session Events**
- `SESSION_START`:
  - Icon: 🚀
  - Shows: Session ID, Agent name, timestamp, project dir
  - Expandable: Full configuration
- `SESSION_STOP`:
  - Icon: 🏁
  - Shows: Reason (success/error/manual), exit code, duration
  - Expandable: Final result/error message

**B. Tool Events**
- `PRE_TOOL`:
  - Icon: 🔧 (or tool-specific icon)
  - Shows: Tool name, timestamp
  - Expandable: Full input parameters (JSON viewer)
- `POST_TOOL`:
  - Icon: ✅ (success) or ❌ (error)
  - Shows: Tool name, execution time, status
  - Expandable: Output/result (code-highlighted for JSON/code)
  - Error: Red border, error message prominent

**C. Message Events**
- `MESSAGE` (User):
  - Icon: 👤
  - Shows: Message content (markdown rendered)
  - Expandable: Raw JSON
- `MESSAGE` (Assistant):
  - Icon: 🤖
  - Shows: Response content (markdown rendered)
  - Expandable: Full message blocks, thinking process

**Features:**
- **Auto-scroll**: Toggle to follow live events (on by default for running sessions)
- **Expand/Collapse All**: Bulk toggle for event details
- **Search**: Filter events by keyword
- **Export**: Download events as JSON/CSV
- **Markdown Toggle**: Switch between rendered/raw markdown
- **Time Display**: Absolute timestamps + relative time
- **Performance**: Virtual scrolling for thousands of events

**Technical:**
- WebSocket streaming with automatic reconnection
- Event buffering to prevent UI freeze
- Syntax highlighting (Prism.js or highlight.js)
- Lazy loading for event details

#### 1.3 New Session Modal

**Purpose**: Create a new agent session

**Form Fields:**
1. **Session Name** (required)
   - Text input
   - Validation: unique name, alphanumeric + hyphens
   - Auto-suggestion based on agent type

2. **Agent Type** (required)
   - Dropdown of available agent definitions
   - Shows agent description on hover/select
   - Option: "None (blank session)"

3. **Initial Prompt** (optional)
   - Textarea (expandable)
   - Markdown preview toggle
   - Example prompts for selected agent

4. **Project Directory** (optional)
   - File path input with browser button
   - Defaults to current working directory
   - Validation: directory exists

5. **Advanced Options** (collapsible)
   - Override system prompt (textarea)
   - Override MCP configuration (JSON editor)
   - Model selection (if supported)
   - Timeout settings

**Actions:**
- "Create & Start" (primary)
- "Create & Wait" (secondary - creates but doesn't run)
- "Cancel"

**Technical:**
- Form validation with Zod schema
- Preview of final configuration
- API call to create session
- Redirect to session view on success
- Error handling with clear messages

#### 1.4 Session Control Actions

**NEW FEATURE**: Stop running agent sessions

**Implementation:**
- **Stop Button**:
  - Visible only for running sessions
  - Confirmation modal: "Are you sure? This will terminate the session immediately."
  - API endpoint: `POST /sessions/{session_id}/stop`
  - Backend needs to send SIGTERM to Claude Code process
  - Updates session status to "stopped"

**Additional Controls:**
- **Resume**: Continue paused session (existing feature, now UI button)
- **Delete**: Remove session and all events (with confirmation)
- **Duplicate**: Create new session with same config
- **Export**: Download session transcript

---

## Tab 2: Documents

### Purpose
Manage documents created by agents or uploaded manually. Provides search, filtering, viewing, and CRUD operations.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar                                                      │
│  • "Upload Document" button                                  │
│  • Search bar (filename, tags, content)                      │
│  • Filter by tags (multi-select)                             │
│  • Sort options (date, name, size)                           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Document Grid / Table View                                   │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 📄 Doc 1     │  │ 📄 Doc 2     │  │ 📄 Doc 3     │      │
│  │              │  │              │  │              │      │
│  │ Analysis.md  │  │ Report.pdf   │  │ Config.json  │      │
│  │ Tags: ai     │  │ Tags: review │  │ Tags: setup  │      │
│  │ 2h ago       │  │ 1d ago       │  │ 3d ago       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Document Preview Panel (Right sidebar or modal)              │
│  • Metadata (tags, description, upload date, size)           │
│  • Content preview (if text/markdown)                        │
│  • Actions (Download, Delete, Edit metadata, Copy URL)       │
└─────────────────────────────────────────────────────────────┘
```

### Components

#### 2.1 Document Toolbar

**Features:**
- **Upload Button**: Opens upload modal
- **Search Bar**:
  - Placeholder: "Search documents by name, tags, or content..."
  - Real-time search with debouncing
  - Advanced search syntax (future): `tag:ai filename:*.md`
- **Tag Filter**:
  - Multi-select dropdown
  - Shows all available tags with counts
  - AND logic (matches all selected tags)
- **Sort Dropdown**:
  - Uploaded (newest first) - default
  - Uploaded (oldest first)
  - Name (A-Z)
  - Name (Z-A)
  - Size (largest first)
  - Size (smallest first)
- **View Toggle**: Grid view ⬜ / Table view ≡

**Technical:**
- Debounced search (300ms)
- URL state management (filters persist in URL)
- API calls with query parameters

#### 2.2 Document Grid/Table View

**Grid View** (Default):
- Card-based layout
- Shows:
  - File icon (based on type: 📄 txt, 📝 md, 🖼️ img, 📊 json, etc.)
  - Filename (truncated with tooltip)
  - Tags (colored badges, max 3 visible)
  - Upload date (relative)
  - Size (human-readable)
  - Agent name (if created by agent)
- Hover effects: Shadow, highlight
- Click: Opens preview panel
- Right-click: Context menu (Download, Delete, Edit)

**Table View**:
- Columns:
  - Checkbox (bulk select)
  - Icon
  - Filename (sortable)
  - Tags
  - Description (truncated)
  - Created By (agent name or "Manual")
  - Created At (sortable)
  - Size (sortable)
  - Actions (buttons)
- Row click: Opens preview
- Bulk actions: Delete selected, Download selected (ZIP)

**Empty State**:
- Illustration + text
- "No documents yet. Upload your first document or create one via an agent."
- "Upload Document" button

**Technical:**
- Pagination (50 items per page) or infinite scroll
- Virtualized rendering for large lists
- Skeleton loaders during fetch

#### 2.3 Document Preview Panel

**Layout**: Right sidebar (slide-in) or modal

**Sections:**

**A. Header**
- Filename (large, prominent)
- Actions (icon buttons):
  - 📥 Download
  - 🗑️ Delete (with confirmation)
  - ✏️ Edit metadata
  - 🔗 Copy URL (document server URL)
  - ❌ Close panel

**B. Metadata**
- **Document ID**: `doc-12345` (copyable)
- **Tags**: Editable inline (add/remove tags)
- **Description**: Editable textarea
- **Created By**: Agent name + session link (or "Manual upload")
- **Created At**: Full timestamp
- **File Size**: KB/MB
- **MIME Type**: `text/markdown`
- **Checksum**: SHA256 hash (copyable, for verification)
- **URL**: Full document server URL (copyable)

**C. Content Preview**
- **If text/markdown**: Rendered preview with markdown
- **If JSON/code**: Syntax-highlighted code block
- **If image**: Image viewer (zoomable)
- **If PDF**: Embedded PDF viewer (iframe or library)
- **If binary**: "Preview not available" + download button

**D. Related Information** (Future)
- Sessions that referenced this document
- Other documents with same tags
- Version history (if versioning implemented)

**Technical:**
- Lazy loading of content (fetch on open)
- Markdown rendering (react-markdown)
- Syntax highlighting (Prism.js)
- Image optimization

#### 2.4 Upload Document Modal

**Form Fields:**

1. **File Upload** (required)
   - Drag-and-drop zone
   - File browser button
   - Multiple file support
   - File size limit display (e.g., "Max 50MB per file")
   - Preview of selected files

2. **Tags** (optional)
   - Tag input (press Enter to add)
   - Existing tag suggestions (autocomplete)
   - Colored badges for added tags
   - Example: `analysis, agent-output, code-review`

3. **Description** (optional)
   - Textarea (500 char limit)
   - Placeholder: "Describe this document..."

4. **Options** (Advanced, collapsible)
   - Replace existing (if filename matches)
   - Private/Public toggle (future feature)

**Actions:**
- "Upload" (primary, shows progress)
- "Cancel"

**Upload Progress:**
- Per-file progress bars
- Success/error indicators
- Retry button for failed uploads

**Technical:**
- Multipart form data upload
- Progress tracking (axios onUploadProgress)
- Error handling (file too large, invalid type, etc.)
- Optimistic UI updates

#### 2.5 Document Management Features

**Bulk Operations:**
- Select multiple documents (checkboxes)
- Actions:
  - Delete selected (with confirmation: "Delete 5 documents?")
  - Download selected as ZIP
  - Add tags to selected
  - Remove tags from selected

**Context Menu** (Right-click on document):
- Open in new tab
- Download
- Copy URL
- Copy document ID
- Edit metadata
- Delete
- View related sessions

**Keyboard Shortcuts:**
- `Cmd/Ctrl + F`: Focus search
- `Cmd/Ctrl + U`: Upload document
- `Delete`: Delete selected
- `Escape`: Close preview panel

---

## Tab 3: Agent Manager

### Purpose
Create, edit, view, and delete agent definitions. Manage agent configurations including system prompts, capabilities (MCP servers, skills), and metadata.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar                                                      │
│  • "New Agent" button                                        │
│  • Search bar (name, description)                            │
│  • Filter by capabilities (MCP servers, skills)              │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Agent List (Cards or Table)                                  │
│                                                               │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ 🤖 code-reviewer     │  │ 🤖 data-analyst      │        │
│  │                      │  │                      │        │
│  │ Reviews code and     │  │ Analyzes data and    │        │
│  │ suggests improvements│  │ generates reports    │        │
│  │                      │  │                      │        │
│  │ Capabilities:        │  │ Capabilities:        │        │
│  │  • MCP: github       │  │  • MCP: pandas       │        │
│  │  • Skill: code-lint  │  │  • Skill: plotting   │        │
│  │                      │  │                      │        │
│  │ Sessions: 12 (3 active)                         │        │
│  │ [Edit] [Duplicate]   │  │ [Edit] [Duplicate]   │        │
│  │ [Delete] [Deactivate]│  │ [Delete] [Deactivate]│        │
│  └──────────────────────┘  └──────────────────────┘        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Components

#### 3.1 Agent List View

**Display Mode**: Card grid (default) or table

**Agent Card:**
- **Header**:
  - Agent icon (default or custom emoji)
  - Agent name (clickable → edit view)
  - Status badge:
    - 🟢 Active
    - ⏸️ Deactivated (hidden from new session creation)
- **Description**: 2-3 lines, truncated with "Read more"
- **Capabilities Section**:
  - MCP Servers: List with icons (e.g., `github`, `filesystem`)
  - Skills: List with icons (e.g., `pdf`, `xlsx`)
  - Max 3 visible, "+2 more" if exceeded
- **Statistics**:
  - Total sessions created with this agent
  - Active sessions count
  - Success rate (% of successful sessions)
- **Actions** (Button row):
  - **Edit**: Opens agent editor
  - **Duplicate**: Create copy with "_copy" suffix
  - **Delete**: Confirmation modal (warns if active sessions exist)
  - **Deactivate/Activate**: Toggle availability

**Empty State**:
- "No agents yet. Create your first specialized agent."
- "New Agent" button

**Technical:**
- API: `GET /agents` (returns list of agent definitions)
- Caching with React Query
- Optimistic updates

#### 3.2 New/Edit Agent Modal

**Full-screen modal** or **dedicated page** (better UX for complex editing)

**Form Sections:**

**A. Basic Information**
1. **Agent Name** (required)
   - Text input
   - Validation: unique, alphanumeric + hyphens
   - Example: `code-reviewer`, `data-analyst`

2. **Description** (required)
   - Textarea (250 chars)
   - Describes agent's purpose
   - Example: "Reviews pull requests and suggests improvements"

3. **Icon/Emoji** (optional)
   - Emoji picker
   - Default: 🤖

**B. System Prompt** (required)
- **Monaco Editor** (code editor component):
  - Markdown syntax highlighting
  - Line numbers
  - Full-screen mode
  - Undo/redo
  - Search & replace
  - Template snippets (dropdown):
    - "Code Reviewer Template"
    - "Data Analyst Template"
    - "General Purpose Template"
- **Preview Panel**: Shows rendered markdown (side-by-side or toggle)
- **Character Count**: Display remaining/used
- **AI Assist** (future): "Generate system prompt based on description"

**C. Capabilities Configuration**

**C1. MCP Servers**
- **List of Available MCP Servers**:
  - Checkbox list (multi-select)
  - Each item shows:
    - Server name (e.g., `github`, `filesystem`)
    - Description (tooltip)
    - Configuration required? (icon)
- **Configuration per Server**:
  - If server requires config (e.g., API keys), show expandable panel
  - JSON editor for server-specific settings
  - Example (GitHub MCP):
    ```json
    {
      "token": "ghp_xxxxx",
      "repos": ["owner/repo1", "owner/repo2"]
    }
    ```
- **Add Custom MCP Server**:
  - Button to add server not in global list
  - Fields: Name, command, args, env vars
  - JSON editor for full config

**C2. Skills (Claude Code Skills)**
- **List of Available Skills**:
  - Checkbox list (multi-select)
  - Each item shows:
    - Skill name (e.g., `pdf`, `xlsx`)
    - Description
- **Note**: Skills are Claude Code plugins, so they're loaded from system
- **Add Custom Skill**: Link to skill installation docs

**D. Advanced Settings** (Collapsible)

1. **Model Selection** (if backend supports)
   - Dropdown: `claude-sonnet-4-5`, `claude-opus-4`, etc.
   - Default: System default

2. **Timeout**
   - Number input (minutes)
   - Default: 30 minutes

3. **Max Tokens**
   - Number input
   - Default: 100,000

4. **Temperature** (if applicable)
   - Slider (0.0 - 1.0)

5. **Auto-resume on Error**
   - Toggle switch
   - If enabled, agent restarts after crash

**E. Testing** (Optional, Future)
- "Test Agent" button
- Runs a simple test session with sample prompt
- Shows output in expandable panel

**Actions:**
- "Save Agent" (primary)
- "Save & Create Session" (saves + opens new session modal)
- "Cancel"

**Validation:**
- Name uniqueness check (async)
- System prompt not empty
- At least one capability selected (warning, not error)
- JSON config validity for MCP servers

**Technical:**
- Monaco Editor for code editing
- JSON schema validation for MCP configs
- API: `POST /agents` (create), `PATCH /agents/{name}` (update)
- Autosave draft (localStorage)

#### 3.3 Agent Details View (Read-Only)

**Layout**: Full-page view with tabs

**Tabs:**

**Tab A: Overview**
- Agent name, description, icon
- System prompt (rendered markdown, expandable)
- Capabilities list (MCP + Skills)
- Statistics:
  - Total sessions: 45
  - Success rate: 92%
  - Avg duration: 12 min
  - Most used tools (chart)
- Recent sessions (table, links to session view)

**Tab B: Configuration**
- Full system prompt (raw markdown)
- MCP configurations (JSON viewer)
- Skills list
- Advanced settings

**Tab C: Sessions History**
- Table of all sessions using this agent
- Columns: Session name, status, created, duration, actions
- Filter/sort
- Click to view session details

**Tab D: Analytics** (Future)
- Success rate over time (line chart)
- Tool usage breakdown (pie chart)
- Average tokens used
- Performance metrics

**Actions** (Floating Action Bar):
- "Edit Agent"
- "Create Session with Agent"
- "Duplicate Agent"
- "Deactivate/Delete Agent"

#### 3.4 Agent Management Features

**Activation/Deactivation:**
- Deactivated agents:
  - Not shown in "New Session" agent dropdown
  - Still visible in Agent Manager (with badge)
  - Existing sessions unaffected
  - Can be reactivated anytime

**Deletion:**
- Confirmation modal:
  - "Delete agent 'code-reviewer'?"
  - Warning if active sessions exist: "X active sessions will become orphaned"
  - Option: "Stop all active sessions before deleting"
  - Checkbox: "I understand this cannot be undone"
- Soft delete vs hard delete:
  - Soft: Agent marked as deleted, not shown, but data retained
  - Hard: Permanently removed (with cascade option)

**Import/Export:**
- **Export Agent**: Download agent definition as JSON/Markdown
- **Import Agent**: Upload agent definition file
- **Share Agent**: Generate shareable link (future)

**Versioning** (Future):
- Track changes to agent definitions
- Rollback to previous version
- Compare versions (diff view)

---

## Supporting Components & Features

### 4.1 WebSocket Connection Management

**Purpose**: Maintain real-time connection to backend for live updates

**Features:**
- Auto-connect on app load
- Auto-reconnect on disconnect (exponential backoff)
- Connection status indicator in header
- Fallback to HTTP polling if WebSocket fails
- Heartbeat/ping mechanism to keep connection alive

**Technical:**
- WebSocketContext provider wraps entire app
- Custom `useWebSocket` hook for subscribing to events
- Event types: `session_update`, `event_new`, `document_uploaded`, etc.
- Message queue during disconnect (buffer events)

**Implementation:**
```typescript
interface WebSocketContextValue {
  connected: boolean;
  subscribe: (eventType: string, callback: (data: any) => void) => void;
  unsubscribe: (eventType: string, callback: (data: any) => void) => void;
  send: (message: any) => void;
}
```

### 4.2 Notification System

**Purpose**: Display toast notifications for user actions and system events

**Types:**
- **Success**: Green, checkmark icon (e.g., "Session created successfully")
- **Error**: Red, X icon (e.g., "Failed to upload document")
- **Warning**: Yellow, ! icon (e.g., "Session has been running for 30+ minutes")
- **Info**: Blue, i icon (e.g., "New event received")

**Features:**
- Auto-dismiss after 5 seconds (configurable)
- Click to dismiss
- Action buttons (e.g., "View Session", "Retry")
- Stack multiple notifications
- Persist critical errors until dismissed

**Technical:**
- React Hot Toast or Sonner library
- NotificationContext provider
- Custom hook: `useNotification()`

**Example Usage:**
```typescript
const { showSuccess, showError } = useNotification();
showSuccess("Agent created successfully!", { action: "View", onAction: () => navigate(`/agents/${id}`) });
```

### 4.3 Settings Panel

**Purpose**: Configure frontend behavior and backend endpoints

**Settings Categories:**

**A. Connections**
- **Observability Backend URL**: Default `http://localhost:8765`
- **Document Server URL**: Default `http://localhost:8766`
- **WebSocket URL**: Auto-derived or custom
- **Test Connection** buttons

**B. Appearance**
- **Theme**: Light / Dark / Auto (system preference)
- **Accent Color**: Color picker
- **Compact Mode**: Toggle for denser UI
- **Font Size**: Small / Medium / Large

**C. Behavior**
- **Auto-scroll in Event Timeline**: On/Off
- **Event Retention**: Keep events for X days (for cleanup)
- **Notification Settings**: Enable/disable per type
- **Default Session View**: Grid / Table
- **Confirm Destructive Actions**: On/Off

**D. Advanced**
- **Polling Interval** (if WebSocket fails): 5s / 10s / 30s
- **Max Events per Session**: Limit timeline (performance)
- **Debug Mode**: Enable verbose logging
- **Export/Import Settings**: JSON file

**Technical:**
- Settings stored in localStorage
- SettingsContext provider
- Validation for URLs
- Apply settings immediately (no restart needed)

### 4.4 Search & Filtering System

**Global Search** (Future Enhancement):
- Search across all tabs: Sessions, Documents, Agents
- Keyboard shortcut: `Cmd/Ctrl + K` (command palette style)
- Quick actions: "Create new session", "Upload document", etc.

**Per-Tab Filters**:
- Persist in URL query parameters
- Shareable links with filters applied
- "Clear all filters" button

**Advanced Filtering**:
- Multiple criteria with AND/OR logic
- Date range pickers
- Tag intersection/union
- Regular expression support

### 4.5 Error Handling & Loading States

**Error Boundaries**:
- React error boundaries for each major component
- Graceful fallback UI: "Something went wrong" + "Retry" button
- Error reporting (send to backend or external service)

**Loading States**:
- Skeleton loaders for lists/cards
- Spinner for actions (button loading state)
- Progress bars for uploads/downloads
- Shimmer effects for placeholders

**Empty States**:
- Friendly illustrations (SVG)
- Helpful text explaining what to do next
- Primary action button

**Offline Mode** (Future):
- Detect offline status
- Cache recent data (service worker)
- Queue actions for when back online
- Show "Offline" banner

### 4.6 Accessibility (a11y)

**Requirements:**
- WCAG 2.1 Level AA compliance
- Keyboard navigation (Tab, Enter, Escape, Arrow keys)
- Screen reader support (ARIA labels, roles, live regions)
- Focus indicators (visible outlines)
- Sufficient color contrast (4.5:1 minimum)
- Semantic HTML
- Skip links ("Skip to main content")

**Testing:**
- Automated: axe-core, Lighthouse
- Manual: Keyboard-only navigation, screen reader testing

### 4.7 Responsive Design

**Breakpoints:**
- Mobile: < 640px (single column, drawer navigation)
- Tablet: 640px - 1024px (2 columns, collapsible sidebars)
- Desktop: > 1024px (full layout)

**Mobile Adaptations:**
- Hamburger menu for navigation
- Bottom sheet for modals/panels
- Touch-friendly buttons (min 44x44px)
- Swipe gestures (close panels, refresh lists)

---

## Data Flow & State Management

### State Architecture

**Global State** (React Context):
- `WebSocketContext`: Connection status, event subscriptions
- `NotificationContext`: Toast notifications
- `SettingsContext`: User preferences
- `AuthContext` (future): User authentication

**Server State** (React Query):
- Sessions: `useSessions()`, `useSession(id)`
- Documents: `useDocuments()`, `useDocument(id)`
- Agents: `useAgents()`, `useAgent(name)`
- Automatic caching, refetching, invalidation

**Component State** (useState/useReducer):
- Form inputs
- UI toggles (modals, dropdowns, expanded states)
- Local filters

### Data Fetching Patterns

**Initial Load:**
1. Fetch sessions, documents, agents (parallel)
2. Show skeleton loaders
3. Render data when ready

**Real-time Updates:**
1. WebSocket event received (e.g., `event_new`)
2. Update React Query cache
3. UI automatically re-renders

**Optimistic Updates:**
1. User action (e.g., delete session)
2. Immediately update UI
3. Send API request
4. If fails, rollback + show error

**Pagination:**
- Infinite scroll (append data)
- React Query `useInfiniteQuery`

---

## API Requirements

### New Endpoints Needed

**Agent Management API** (to be added to backend or new service):

```typescript
// Agent CRUD
GET    /agents                      // List all agents
GET    /agents/{name}               // Get agent details
POST   /agents                      // Create agent
PATCH  /agents/{name}               // Update agent
DELETE /agents/{name}               // Delete agent
POST   /agents/{name}/duplicate     // Duplicate agent
PATCH  /agents/{name}/activate      // Activate agent
PATCH  /agents/{name}/deactivate    // Deactivate agent

// Agent sessions
GET    /agents/{name}/sessions      // Get sessions for agent
GET    /agents/{name}/stats         // Get agent statistics

// Capabilities
GET    /capabilities/mcp-servers    // List available MCP servers
GET    /capabilities/skills         // List available skills
```

**Session Control API** (extend observability backend):

```typescript
POST   /sessions/{id}/stop          // Stop running session
POST   /sessions/{id}/resume        // Resume paused session
POST   /sessions/{id}/duplicate     // Duplicate session config
GET    /sessions/{id}/transcript    // Get full transcript
```

**Document API Enhancements** (extend document server):

```typescript
PATCH  /documents/{id}              // Update tags/description
POST   /documents/bulk-delete       // Delete multiple documents
GET    /documents/tags              // Get all unique tags with counts
GET    /documents/search            // Advanced search endpoint
```

---

## Technology Choices & Justification

### Why Tailwind CSS?
- Utility-first: Fast development, consistent design
- Customizable: Easy theming
- Small bundle size (only used classes included)
- Great developer experience with IntelliSense

### Why React Query?
- Declarative data fetching
- Automatic caching, refetching, synchronization
- Optimistic updates
- Works seamlessly with REST APIs
- Built-in loading/error states

### Why Monaco Editor?
- Full-featured code editor (powers VS Code)
- Syntax highlighting for markdown, JSON
- IntelliSense, search, multi-cursor
- Accessible and performant

### Why React Router?
- Standard routing library for React
- Nested routes, URL state management
- Code splitting support
- Great TypeScript support

---

## Development Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Project setup (Vite, TypeScript, Tailwind)
- [ ] Layout structure (header, navigation, tabs)
- [ ] API service layer (axios clients)
- [ ] WebSocket integration
- [ ] Basic routing

### Phase 2: Agent Sessions Tab (Week 3-4)
- [ ] Session list sidebar
- [ ] Event timeline
- [ ] Filters and search
- [ ] New session modal
- [ ] Stop/resume controls

### Phase 3: Documents Tab (Week 5-6)
- [ ] Document grid/table views
- [ ] Upload modal
- [ ] Preview panel
- [ ] Search and filtering
- [ ] Bulk operations

### Phase 4: Agent Manager Tab (Week 7-8)
- [ ] Agent list view
- [ ] Agent editor (system prompt, capabilities)
- [ ] MCP server configuration
- [ ] Agent details view
- [ ] Activation/deactivation

### Phase 5: Polish & Testing (Week 9-10)
- [ ] Settings panel
- [ ] Notifications
- [ ] Error handling
- [ ] Accessibility audit
- [ ] Responsive design
- [ ] Unit tests
- [ ] E2E tests

### Phase 6: Advanced Features (Week 11-12)
- [ ] Global search (Cmd+K)
- [ ] Analytics/statistics
- [ ] Export/import
- [ ] Keyboard shortcuts
- [ ] Dark mode

---

## File Structure Detail

```
agent-orchestrator-frontend/
├── public/
│   ├── favicon.ico
│   └── robots.txt
│
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Dropdown.tsx
│   │   │   ├── Checkbox.tsx
│   │   │   ├── Tooltip.tsx
│   │   │   ├── Spinner.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── EmptyState.tsx
│   │   │
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Navigation.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   │
│   │   └── features/
│   │       ├── sessions/
│   │       │   ├── SessionList.tsx
│   │       │   ├── SessionCard.tsx
│   │       │   ├── EventTimeline.tsx
│   │       │   ├── EventCard.tsx
│   │       │   ├── NewSessionModal.tsx
│   │       │   └── SessionControls.tsx
│   │       │
│   │       ├── documents/
│   │       │   ├── DocumentGrid.tsx
│   │       │   ├── DocumentCard.tsx
│   │       │   ├── DocumentTable.tsx
│   │       │   ├── DocumentPreview.tsx
│   │       │   ├── UploadModal.tsx
│   │       │   └── DocumentToolbar.tsx
│   │       │
│   │       └── agents/
│   │           ├── AgentList.tsx
│   │           ├── AgentCard.tsx
│   │           ├── AgentEditor.tsx
│   │           ├── AgentDetails.tsx
│   │           ├── SystemPromptEditor.tsx
│   │           ├── CapabilitySelector.tsx
│   │           └── MCPConfigEditor.tsx
│   │
│   ├── pages/
│   │   ├── AgentSessions.tsx
│   │   ├── Documents.tsx
│   │   ├── AgentManager.tsx
│   │   └── Settings.tsx
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useSessions.ts
│   │   ├── useSession.ts
│   │   ├── useDocuments.ts
│   │   ├── useDocument.ts
│   │   ├── useAgents.ts
│   │   ├── useAgent.ts
│   │   ├── useNotification.ts
│   │   └── useSettings.ts
│   │
│   ├── services/
│   │   ├── api.ts              # Axios instance configuration
│   │   ├── sessionService.ts   # Session CRUD
│   │   ├── documentService.ts  # Document CRUD
│   │   ├── agentService.ts     # Agent CRUD
│   │   └── websocket.ts        # WebSocket client
│   │
│   ├── types/
│   │   ├── session.ts
│   │   ├── event.ts
│   │   ├── document.ts
│   │   ├── agent.ts
│   │   └── common.ts
│   │
│   ├── contexts/
│   │   ├── WebSocketContext.tsx
│   │   ├── NotificationContext.tsx
│   │   ├── SettingsContext.tsx
│   │   └── AuthContext.tsx
│   │
│   ├── utils/
│   │   ├── formatters.ts       # Date, size, number formatters
│   │   ├── validators.ts       # Form validation
│   │   ├── constants.ts        # App constants
│   │   └── helpers.ts          # Utility functions
│   │
│   ├── styles/
│   │   ├── globals.css         # Global styles, Tailwind imports
│   │   └── theme.css           # CSS variables for theming
│   │
│   ├── App.tsx
│   ├── main.tsx
│   ├── router.tsx
│   └── vite-env.d.ts
│
├── .env.example
├── .gitignore
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── README.md
└── Dockerfile                  # For containerized deployment
```

---

## Key TypeScript Interfaces

### Session Types
```typescript
interface Session {
  session_id: string;
  session_name: string;
  status: 'running' | 'paused' | 'finished' | 'failed';
  created_at: string;
  updated_at: string;
  project_dir?: string;
  agent_name?: string;
  duration_seconds?: number;
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
  updated_at: string;
  size_bytes: number;
  mime_type: string;
  checksum: string;
  url: string;
  created_by?: {
    type: 'agent' | 'manual';
    agent_name?: string;
    session_id?: string;
  };
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
  icon?: string;
  system_prompt: string;
  mcp_servers: MCPServerConfig[];
  skills: string[];
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
  statistics?: AgentStatistics;
}

interface MCPServerConfig {
  name: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
  config?: Record<string, any>;
}

interface AgentStatistics {
  total_sessions: number;
  active_sessions: number;
  success_rate: number;
  avg_duration_seconds: number;
  total_tokens_used: number;
}
```

---

## Security Considerations

### Frontend Security
1. **Input Validation**: All user inputs validated on frontend AND backend
2. **XSS Prevention**: React's built-in escaping + DOMPurify for markdown
3. **CSRF Protection**: CSRF tokens for state-changing requests
4. **Secure Storage**: No sensitive data in localStorage (use httpOnly cookies for auth)
5. **Content Security Policy**: Strict CSP headers
6. **Dependency Audits**: Regular `npm audit` + automated updates

### API Security
1. **Authentication**: JWT tokens or session cookies (future)
2. **Authorization**: Role-based access control (future)
3. **Rate Limiting**: Prevent abuse (backend)
4. **CORS**: Strict origin whitelist
5. **HTTPS Only**: Enforce encrypted connections in production

### File Upload Security
1. **File Type Validation**: Check MIME type AND file content
2. **Size Limits**: Enforce max file size (50MB)
3. **Malware Scanning**: Integrate with AV scanner (future)
4. **Sandboxed Storage**: Files stored outside web root
5. **Content Disposition**: Force download for user-uploaded files

---

## Performance Optimization

### Frontend Performance
1. **Code Splitting**: Lazy load routes and heavy components
2. **Tree Shaking**: Remove unused code (Vite does this)
3. **Image Optimization**: Compress, lazy load, responsive images
4. **Virtual Scrolling**: For long lists (react-window)
5. **Memoization**: React.memo, useMemo, useCallback
6. **Bundle Analysis**: Visualize bundle size (rollup-plugin-visualizer)

### Network Performance
1. **HTTP/2**: Multiplexing, server push
2. **Compression**: Gzip/Brotli for text assets
3. **Caching**: Aggressive caching with cache-busting
4. **CDN**: Static assets on CDN (future)
5. **Request Batching**: Combine multiple API calls

### WebSocket Performance
1. **Throttling**: Limit event frequency (debounce)
2. **Backpressure**: Slow down if client can't keep up
3. **Compression**: WebSocket compression (permessage-deflate)
4. **Reconnection**: Exponential backoff

---

## Testing Strategy

### Unit Tests (Jest + React Testing Library)
- Component rendering
- User interactions
- Hooks logic
- Utility functions
- Coverage target: 80%+

### Integration Tests
- API service layer
- WebSocket integration
- Form submissions
- Navigation flows

### End-to-End Tests (Playwright or Cypress)
- Critical user flows:
  - Create session → View events → Stop session
  - Upload document → Search → Download
  - Create agent → Edit → Create session with agent
- Cross-browser testing (Chrome, Firefox, Safari)

### Performance Tests
- Lighthouse CI
- Bundle size monitoring
- Render performance (React DevTools Profiler)

### Accessibility Tests
- axe-core (automated)
- Manual keyboard navigation
- Screen reader testing (NVDA, JAWS, VoiceOver)

---

## Deployment

### Docker Deployment
```dockerfile
# Dockerfile
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

### Docker Compose Integration
```yaml
# Add to docker-compose.yml
services:
  agent-orchestrator-frontend:
    build:
      context: ./agent-orchestrator-frontend
    ports:
      - "3000:80"
    environment:
      - VITE_BACKEND_URL=http://observability-backend:8765
      - VITE_DOCUMENT_SERVER_URL=http://document-server:8766
    depends_on:
      - observability-backend
      - document-server
    networks:
      - agent-orchestrator-network
```

### Environment Variables
```bash
# .env.production
VITE_BACKEND_URL=https://api.example.com
VITE_DOCUMENT_SERVER_URL=https://docs.example.com
VITE_WS_URL=wss://api.example.com/ws
VITE_ENABLE_DEBUG=false
```

---

## Open Questions & Future Enhancements

### Open Questions (To Discuss)
1. **Authentication**: Do we need user accounts? Multi-tenancy?
2. **Permissions**: Role-based access (admin vs viewer)?
3. **Session Sharing**: Can users share session links?
4. **Document Privacy**: Public/private documents?
5. **Agent Marketplace**: Share/discover community agents?
6. **Pricing/Billing**: Track token usage per user?

### Future Enhancements
1. **Agent Collaboration**: Multiple agents working together
2. **Workflow Builder**: Visual workflow designer (no-code)
3. **Scheduled Sessions**: Cron-like agent execution
4. **Webhooks**: Notify external systems of events
5. **API Gateway**: Public API for third-party integrations
6. **Mobile Apps**: Native iOS/Android apps
7. **AI Assistant**: In-app AI to help with agent creation
8. **Version Control**: Git-like versioning for agents
9. **Templates Library**: Pre-built agent templates
10. **Analytics Dashboard**: Deep insights into agent performance

---

## Summary

This frontend design provides:
- **Unified interface** for all AOF capabilities
- **Real-time monitoring** with WebSocket streaming
- **Active control** over agent lifecycle (start, stop, resume, delete)
- **Document management** for agent outputs
- **Agent definition CRUD** with system prompt & capability configuration
- **Modern, responsive UI** built with React + TypeScript + Tailwind
- **Scalable architecture** for future enhancements

The design maintains the existing observability features while adding comprehensive management capabilities. It's modular, performant, and user-friendly.

---

## Next Steps

1. **Review this document** with stakeholders
2. **Refine requirements** based on feedback
3. **Create wireframes/mockups** (Figma)
4. **Set up project structure** (boilerplate)
5. **Implement backend APIs** (agent management endpoints)
6. **Build frontend** (phased approach)
7. **Test & iterate**
8. **Deploy & monitor**

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**Author**: Claude (Agent Orchestrator Framework)
