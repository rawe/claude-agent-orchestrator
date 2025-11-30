# Agent Orchestrator Frontend - Handover Document

## Project Goal

Build a **unified frontend** for the Agent Orchestrator Framework that combines:
1. **Observability** - Real-time monitoring of agent sessions via WebSocket
2. **Document Management** - Upload, view, and manage context documents
3. **Agent Management** - CRUD for agent definitions (blueprints)

## Why

Previously, only a basic observability frontend existed. The new unified frontend provides a single interface for all framework capabilities, following the design spec in `FRONTEND-DESIGN-V1.md`.

## Current Status

**Frontend: COMPLETE** - All V1 features implemented and building successfully.

**Backend Integration:**
- Observability Backend (8765): ✅ Integrated
- Document Server (8766): ✅ Integrated
- Agent Manager (8767): ❌ Mocked in frontend (service doesn't exist yet)

## Key Files

### Design & Documentation
- `docs/FRONTEND-DESIGN-V1.md` - Full design specification
- `agent-orchestrator-frontend/docs/BACKEND-TODO.md` - Missing backend endpoints
- `agent-orchestrator-frontend/README.md` - Quick start guide

### Frontend Structure (`agent-orchestrator-frontend/src/`)
```
types/           - TypeScript interfaces (session, event, document, agent)
services/        - API clients (sessionService, documentService, agentService)
hooks/           - React hooks (useSessions, useDocuments, useAgents)
contexts/        - WebSocketContext, NotificationContext
components/
  common/        - Button, Modal, Badge, Spinner, etc.
  layout/        - Header, Sidebar, Layout
  features/
    sessions/    - SessionList, SessionCard, EventTimeline, EventCard
    documents/   - DocumentTable, DocumentPreview, UploadModal
    agents/      - AgentTable, AgentEditor
pages/           - AgentSessions, Documents, AgentManager
```

### Backend Files Modified
- `agent-orchestrator-observability/backend/main.py` - Added CORS for port 3000
- `plugins/document-sync/document-server/src/main.py` - Added CORS middleware

### Docker
- `agent-orchestrator-frontend/docker-compose.yml` - Quick start
- `agent-orchestrator-frontend/Dockerfile` - Production build with nginx

## Tech Stack
React 18, TypeScript, Vite, Tailwind CSS, React Router v6, TanStack Table, Axios, WebSocket

## Running Locally
```bash
cd agent-orchestrator-frontend
npm install
npm run dev  # http://localhost:3000
```

Requires backends running on ports 8765 (observability) and 8766 (documents).

## What's Left for Backend

See `docs/BACKEND-TODO.md` for details. Priority items:
1. `POST /sessions/{id}/stop` - Stop running sessions
2. `GET /documents/tags` - Get unique tags with counts
3. **Agent Manager Service** (port 8767) - Full CRUD API for agent definitions

## Notes
- Agent Manager tab uses mock data until backend exists
- Session "stop" button shows warning (endpoint not implemented)
- Desktop-only, light theme only (per V1 scope)
