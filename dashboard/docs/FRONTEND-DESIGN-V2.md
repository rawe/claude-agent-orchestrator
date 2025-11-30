# Agent Orchestrator Framework - Frontend V2 Features

## Overview

This document lists all features and enhancements **deferred from V1 to V2**. These are valuable improvements that add polish, power-user features, and scalability, but are not essential for the initial release.

V2 features can be implemented incrementally after V1 is stable and deployed.

---

## 1. Agent Sessions Tab Enhancements

### 1.1 Resume Session from UI
**Description:** Add a "Resume" button for paused/stopped sessions to continue execution from the UI.

**Current V1:** Sessions can only be resumed via CLI (`ao-resume`).

**V2 Addition:**
- "Resume" button visible for `not_running` sessions
- Button sends `POST /sessions/{id}/resume` to backend
- Backend pushes event when session resumes
- UI updates status to `running`

**Priority:** Medium
**Effort:** Low

---

### 1.2 Session Timeline Search
**Description:** Search within event timeline by keyword (tool name, error message, content).

**Current V1:** No search capability.

**V2 Addition:**
- Search input above timeline
- Filters events in real-time
- Highlights matching text
- "Clear search" button

**Priority:** Medium
**Effort:** Low

---

### 1.3 Export Session Events
**Description:** Download session events as JSON or CSV for external analysis.

**Current V1:** No export functionality.

**V2 Addition:**
- "Export" button in session toolbar
- Options: JSON (raw events) or CSV (flattened for Excel)
- Filename: `session-{name}-events-{date}.json`

**Priority:** Low
**Effort:** Low

---

### 1.4 Inline Session Name Editing
**Description:** Edit session name directly in the session card without opening a modal.

**Current V1:** Session name is read-only.

**V2 Addition:**
- Click session name to edit inline
- Press Enter to save, Escape to cancel
- API: `PATCH /sessions/{id}` with `{session_name: "new-name"}`

**Priority:** Low
**Effort:** Low

---

### 1.5 Right-Click Context Menu
**Description:** Right-click on session card to show context menu with quick actions.

**Current V1:** Only visible action buttons.

**V2 Addition:**
- Context menu items:
  - Stop (if running)
  - Resume (if paused)
  - Delete
  - Copy Session ID
  - Export Events

**Priority:** Low
**Effort:** Medium

---

### 1.6 Virtual Scrolling for Large Lists
**Description:** Use virtual scrolling (react-window) to handle thousands of sessions or events efficiently.

**Current V1:** Standard list rendering (may lag with 1000+ items).

**V2 Addition:**
- Implement `react-window` or `@tanstack/react-virtual`
- Only render visible items (~20-30 at a time)
- Smooth scrolling even with 10,000+ items

**Priority:** Medium (if performance issues occur)
**Effort:** Medium

---

### 1.7 Date Range Filter
**Description:** Filter sessions by creation/modification date range.

**Current V1:** Only status and agent type filters.

**V2 Addition:**
- Date range picker (e.g., "Last 7 days", "Last 30 days", "Custom range")
- Filter applies to created_at or modified_at
- Clear filter button

**Priority:** Low
**Effort:** Medium

---

## 2. Documents Tab Enhancements

### 2.1 Grid View Toggle
**Description:** Switch between table view and card grid view for documents.

**Current V1:** Table view only.

**V2 Addition:**
- Toggle button in toolbar (Grid ⬜ / Table ≡)
- Grid view shows document cards with thumbnails
- User preference saved (no localStorage in V1, but add in V2)

**Priority:** Medium
**Effort:** Medium

---

### 2.2 Bulk Operations
**Description:** Select multiple documents for batch actions (delete, download, tag).

**Current V1:** Single document actions only.

**V2 Addition:**
- Checkboxes in table view
- "Select All" checkbox in header
- Bulk actions toolbar appears when items selected:
  - Delete selected (with count confirmation)
  - Download selected as ZIP
  - Add tags to selected
  - Remove tags from selected

**Priority:** Medium
**Effort:** High

---

### 2.3 Metadata Editing in Preview
**Description:** Edit document tags and description directly in preview modal.

**Current V1:** Metadata is read-only.

**V2 Addition:**
- "Edit" button in preview modal
- Inline editing for tags (add/remove)
- Editable textarea for description
- "Save Changes" button
- API: `PATCH /documents/{id}`

**Priority:** Medium
**Effort:** Low

---

### 2.4 "Created By" Column
**Description:** Show which agent (or manual upload) created each document.

**Current V1:** Backend doesn't track this yet.

**V2 Addition:**
- Backend stores `created_by: {type: 'agent' | 'manual', agent_name?: string, session_id?: string}`
- Frontend displays in table column
- Click agent name to filter by that agent
- Click session ID to jump to that session

**Priority:** High
**Effort:** Medium (requires backend changes)

---

### 2.5 Right-Click Context Menu
**Description:** Right-click on document row for quick actions.

**Current V1:** Only visible action buttons.

**V2 Addition:**
- Context menu items:
  - Open preview
  - Download
  - Copy URL
  - Copy Document ID
  - Edit metadata
  - Delete

**Priority:** Low
**Effort:** Low

---

### 2.6 Image & PDF Preview
**Description:** Preview images and PDFs directly in the document preview modal.

**Current V1:** Only markdown and JSON renderers.

**V2 Addition:**
- **Images** (.png, .jpg, .gif, .svg): Show image with zoom
- **PDFs** (.pdf): Embed PDF viewer (iframe or library like react-pdf)
- Detection by MIME type and file extension

**Priority:** Medium
**Effort:** High

---

### 2.7 Document Versioning
**Description:** Track changes to documents over time (versions, rollback).

**Current V1:** Single version only.

**V2 Addition:**
- Backend stores document versions (version number, timestamp)
- Preview shows version history
- "Rollback to this version" button
- Compare versions (diff view)

**Priority:** Low
**Effort:** Very High (requires major backend changes)

---

## 3. Agent Manager Tab Enhancements

### 3.1 Agent Duplication
**Description:** Duplicate an existing agent to create a new one as a starting point.

**Current V1:** No duplicate feature.

**V2 Addition:**
- "Duplicate" button in agent table
- Copies all fields (name becomes `{original-name}_copy`)
- Opens editor modal with copied data
- User can modify and save as new agent

**Priority:** Medium
**Effort:** Low

---

### 3.2 Agent Sets (Task-Based Collections)
**Description:** Create agent sets (collections) to quickly activate/deactivate groups of agents for different tasks.

**Current V1:** Manual individual activation.

**V2 Addition:**
- **Agent Sets Management**:
  - Create sets: "Code Review Set", "Data Analysis Set", etc.
  - Assign agents to sets (many-to-many relationship)
  - Only one set active at a time
- **UI**:
  - Dropdown in Agent Manager header: "Active Set: [Code Review ▼]"
  - Switch sets → bulk activate/deactivate agents
  - "Manage Sets" button → modal to create/edit/delete sets
- **Backend**:
  - New entity: AgentSet (name, agent_names[])
  - API: `GET /agent-sets`, `POST /agent-sets`, `PATCH /agent-sets/{id}/activate`

**Priority:** High (per user feedback)
**Effort:** High

---

### 3.3 Custom MCP Server Configuration
**Description:** Allow users to add custom MCP servers and configure them (not just predefined list).

**Current V1:** Predefined MCP servers only, no config editing.

**V2 Addition:**
- "Add Custom MCP Server" button in agent editor
- Form fields:
  - Server name
  - Command
  - Arguments (array)
  - Environment variables (key-value pairs)
  - JSON config (Monaco editor)
- Configuration expandable panel for each MCP server
- Validation (JSON schema)

**Priority:** Medium
**Effort:** High

---

### 3.4 Agent Statistics & Analytics
**Description:** Show statistics for each agent (total sessions, success rate, avg duration, token usage).

**Current V1:** No statistics displayed.

**V2 Addition:**
- Backend tracks:
  - Total sessions created with agent
  - Success rate (% finished successfully)
  - Average duration
  - Total tokens used (if available)
- Agent table columns: Sessions, Success Rate
- Agent details view (new page/modal):
  - **Overview tab**: Stats, recent sessions, charts
  - **Configuration tab**: System prompt, capabilities
  - **Sessions History tab**: Table of all sessions using this agent
  - **Analytics tab** (future): Time-series charts, tool usage breakdown

**Priority:** Medium
**Effort:** Very High (requires backend tracking + analytics)

---

### 3.5 Agent Import/Export
**Description:** Export agent definitions as files and import them (for sharing/backup).

**Current V1:** No import/export.

**V2 Addition:**
- **Export**:
  - "Export" button per agent
  - Download as JSON or Markdown file
  - Includes: name, description, system prompt, capabilities
- **Import**:
  - "Import Agent" button in toolbar
  - Upload JSON/Markdown file
  - Validate and create agent
- **Shareable Links** (future):
  - Generate URL to share agent definition
  - Public agent marketplace

**Priority:** Low
**Effort:** Medium

---

### 3.6 Agent Template Library
**Description:** Pre-built agent templates for common use cases (code review, data analysis, etc.).

**Current V1:** Empty start for new agents.

**V2 Addition:**
- "New Agent from Template" button
- Template gallery:
  - Code Reviewer Template
  - Data Analyst Template
  - Documentation Writer Template
  - Bug Hunter Template
  - etc.
- Select template → pre-fills system prompt and capabilities
- User can customize and save

**Priority:** Medium
**Effort:** Medium

---

### 3.7 Agent Versioning
**Description:** Track changes to agent definitions over time, with rollback capability.

**Current V1:** Single version only.

**V2 Addition:**
- Backend stores agent versions (version number, timestamp, changes)
- Agent editor shows "Version History" button
- View previous versions
- Rollback to previous version
- Compare versions (diff view for system prompt)

**Priority:** Low
**Effort:** Very High

---

## 4. UI/UX Enhancements

### 4.1 Dark Mode
**Description:** Support light and dark themes with toggle.

**Current V1:** Light theme only.

**V2 Addition:**
- Theme toggle in header (Sun/Moon icon)
- Three modes: Light, Dark, Auto (system preference)
- Tailwind CSS dark mode (`class` strategy)
- User preference saved in localStorage

**Priority:** Medium
**Effort:** Medium (requires redesigning all components for dark theme)

---

### 4.2 Keyboard Shortcuts
**Description:** Power-user keyboard shortcuts for common actions.

**Current V1:** No keyboard shortcuts.

**V2 Addition:**
- Global shortcuts:
  - `Cmd/Ctrl + K` - Global search/command palette
  - `Escape` - Close modal/panel
  - `/` - Focus search bar
- Tab-specific shortcuts:
  - `Cmd/Ctrl + F` - Focus search
  - `Delete` - Delete selected item
  - Arrow keys - Navigate lists
- Show shortcut hints in UI (tooltips, help modal)

**Priority:** Low
**Effort:** Medium

---

### 4.3 Mobile Responsive Design
**Description:** Fully responsive layout for tablets and mobile devices.

**Current V1:** Desktop-only.

**V2 Addition:**
- Responsive breakpoints:
  - Mobile (< 640px): Single column, drawer navigation
  - Tablet (640px - 1024px): 2 columns, collapsible sidebars
- Mobile adaptations:
  - Hamburger menu for navigation
  - Bottom sheet for modals
  - Touch-friendly buttons (min 44x44px)
  - Swipe gestures

**Priority:** Low (if mobile access needed)
**Effort:** Very High

---

### 4.4 Global Search (Cmd+K)
**Description:** Command palette-style global search across all tabs.

**Current V1:** Per-tab search only.

**V2 Addition:**
- `Cmd/Ctrl + K` opens command palette
- Search across:
  - Sessions (by name, ID)
  - Documents (by name, tags)
  - Agents (by name, description)
- Quick actions:
  - "Upload document"
  - "Create agent"
  - "Stop session X"
- Keyboard navigation (arrow keys, Enter to execute)

**Priority:** Medium
**Effort:** High

---

### 4.5 Settings Panel (UI Preferences)
**Description:** User-facing settings for UI behavior.

**Current V1:** No settings UI (only env vars).

**V2 Addition:**
- Settings icon in header → modal
- Settings categories:
  - **Appearance**: Theme, font size
  - **Behavior**: Auto-scroll default, confirm destructive actions
  - **Notifications**: Enable/disable per type
- Settings stored in localStorage

**Priority:** Low
**Effort:** Low

---

### 4.6 Notifications Bell with History
**Description:** Notification center showing recent system events.

**Current V1:** Toast notifications only.

**V2 Addition:**
- Bell icon in header with badge count
- Click to open notification panel
- Shows recent notifications (last 50)
- Mark as read, clear all
- Notification types:
  - Session finished
  - Document uploaded
  - Agent created
  - Errors

**Priority:** Low
**Effort:** Medium

---

## 5. Performance & Reliability

### 5.1 HTTP Polling Fallback
**Description:** Fall back to HTTP polling if WebSocket connection fails.

**Current V1:** WebSocket only.

**V2 Addition:**
- If WebSocket fails/disconnects repeatedly (after N retries)
- Switch to HTTP polling mode
- Poll backend every 5-10 seconds for updates
- Show indicator: "Using polling mode (WebSocket unavailable)"
- Automatically retry WebSocket every few minutes

**Priority:** Medium (if WebSocket reliability is an issue)
**Effort:** High

---

### 5.2 Offline Mode with Service Worker
**Description:** Cache recent data and queue actions when offline.

**Current V1:** Requires constant connection.

**V2 Addition:**
- Service worker for offline caching
- Cache recent sessions, documents, agents
- Show "Offline" banner when disconnected
- Queue actions (delete, upload) for when back online
- Sync queued actions on reconnection

**Priority:** Low
**Effort:** Very High

---

### 5.3 Request Batching
**Description:** Combine multiple API calls into single request for efficiency.

**Current V1:** Individual requests per action.

**V2 Addition:**
- Backend supports batch endpoints:
  - `POST /batch` - Send multiple operations in one request
- Frontend batches concurrent requests
- Reduces network overhead

**Priority:** Low
**Effort:** High (requires backend support)

---

## 6. Testing & Quality

### 6.1 Automated Testing
**Description:** Unit, integration, and E2E tests.

**Current V1:** Manual testing only.

**V2 Addition:**
- **Unit Tests** (Jest + React Testing Library):
  - Component rendering
  - Hooks logic
  - Utility functions
  - Target: 80%+ coverage
- **Integration Tests**:
  - API service layer
  - WebSocket integration
  - Form submissions
- **E2E Tests** (Playwright or Cypress):
  - Critical user flows
  - Cross-browser testing

**Priority:** High (before production)
**Effort:** Very High

---

### 6.2 Accessibility Audit
**Description:** Full WCAG 2.1 Level AA compliance.

**Current V1:** Basic semantic HTML, but not audited.

**V2 Addition:**
- Automated testing (axe-core, Lighthouse)
- Manual keyboard navigation testing
- Screen reader testing (NVDA, JAWS, VoiceOver)
- Fix all issues:
  - ARIA labels
  - Focus management
  - Color contrast
  - Keyboard navigation

**Priority:** Medium
**Effort:** High

---

## 7. Advanced Features (Future)

### 7.1 Agent Collaboration & Workflows
**Description:** Multiple agents working together in coordinated workflows.

**Priority:** Low
**Effort:** Very High (requires major architecture changes)

---

### 7.2 Workflow Builder (No-Code)
**Description:** Visual workflow designer to create agent pipelines.

**Priority:** Low
**Effort:** Very High

---

### 7.3 Scheduled Sessions (Cron Jobs)
**Description:** Schedule agents to run automatically at specific times.

**Priority:** Low
**Effort:** High (requires backend scheduler)

---

### 7.4 Webhooks & Integrations
**Description:** Notify external systems of events (Slack, Discord, email).

**Priority:** Low
**Effort:** Medium (backend feature)

---

### 7.5 API Gateway for Third-Party Access
**Description:** Public API for external applications to integrate with AOF.

**Priority:** Low
**Effort:** Very High

---

### 7.6 Authentication & Multi-Tenancy
**Description:** User accounts, login, role-based access control.

**Priority:** Medium (if multi-user environment)
**Effort:** Very High

---

## Priority Matrix

### High Priority (Implement Soon After V1)
1. Agent Sets (task-based collections)
2. "Created By" column for documents
3. Automated testing suite
4. Virtual scrolling (if performance issues)

### Medium Priority (Nice to Have)
1. Resume session from UI
2. Document grid view toggle
3. Bulk document operations
4. Agent duplication
5. Custom MCP configuration
6. Agent statistics
7. Dark mode
8. Global search (Cmd+K)
9. Timeline search
10. Document metadata editing

### Low Priority (Future Enhancements)
1. Export session events
2. Inline session name editing
3. Right-click context menus
4. Image/PDF preview
5. Agent import/export
6. Agent templates
7. Keyboard shortcuts
8. Mobile responsive design
9. Settings panel
10. Notification center
11. All "Advanced Features"

---

## Implementation Strategy

### Phase 1: Quick Wins (Post-V1 Launch)
- Agent Sets
- Resume session from UI
- Timeline search
- Document metadata editing
- Agent duplication

**Effort:** 2-3 weeks
**Impact:** High user value, relatively low effort

### Phase 2: Power Features
- Bulk operations (documents)
- Custom MCP configuration
- Agent statistics
- Dark mode
- Virtual scrolling

**Effort:** 4-6 weeks
**Impact:** High for power users

### Phase 3: Polish & Scale
- Automated testing
- Accessibility audit
- Global search
- Keyboard shortcuts
- Mobile responsive

**Effort:** 6-8 weeks
**Impact:** Production-ready quality

### Phase 4: Advanced Features
- Agent collaboration
- Workflow builder
- Scheduled sessions
- Webhooks
- Authentication

**Effort:** 3-6 months
**Impact:** Enterprise-ready features

---

## Summary

V2 features transform the frontend from a **functional MVP** into a **polished, production-ready platform** with:
- Power-user features (keyboard shortcuts, bulk operations, search)
- Better UX (dark mode, mobile support, accessibility)
- Advanced capabilities (agent sets, statistics, versioning)
- Quality assurance (automated tests, accessibility)

These enhancements can be implemented incrementally based on user feedback and priorities after V1 is stable.

---

**Document Version**: 1.0
**Release**: V2 (Future)
**Last Updated**: 2025-11-24
**Author**: Claude (Agent Orchestrator Framework)
