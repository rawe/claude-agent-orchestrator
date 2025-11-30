# Agent Orchestrator Frontend

A unified React frontend for the Agent Orchestrator Framework, providing real-time monitoring, document management, and agent configuration capabilities.

## Features

### Agent Sessions (Observability)
- Real-time session monitoring via WebSocket
- Event timeline with expandable details
- Session filtering by status and agent
- Stop and delete session actions

### Documents (Context Management)
- Upload and manage documents
- Tag-based filtering
- Markdown and JSON preview
- Download functionality

### Agent Manager
- Create and edit agent definitions
- System prompt editor with preview
- MCP server and skill configuration
- Activate/deactivate agents

## Quick Start

### Option 1: Docker (Recommended)

Run the production build with Docker Compose:

```bash
cd agent-orchestrator-frontend
docker-compose up -d
```

The frontend will be available at `http://localhost:3000`.

For development with hot reload:

```bash
docker-compose --profile dev up frontend-dev
```

### Option 2: Local Development

Prerequisites:
- Node.js 18+
- npm or yarn

```bash
cd agent-orchestrator-frontend
npm install
npm run dev
```

The application will be available at `http://localhost:3000`.

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
VITE_OBSERVABILITY_BACKEND_URL=http://localhost:8765
VITE_DOCUMENT_SERVER_URL=http://localhost:8766
VITE_AGENT_REGISTRY_URL=http://localhost:8767
VITE_WEBSOCKET_URL=ws://localhost:8765/ws
```

### Production Build

```bash
npm run build
```

Or build the Docker image directly:

```bash
docker build -t agent-orchestrator-frontend .
docker run -p 3000:80 agent-orchestrator-frontend
```

## Architecture

```
src/
├── components/
│   ├── common/        # Reusable UI components
│   ├── layout/        # Header, Sidebar, Layout
│   └── features/      # Feature-specific components
│       ├── sessions/  # Session monitoring
│       ├── documents/ # Document management
│       └── agents/    # Agent configuration
├── pages/             # Route pages
├── hooks/             # Custom React hooks
├── services/          # API clients
├── types/             # TypeScript interfaces
├── contexts/          # React context providers
└── utils/             # Utility functions
```

## Backend Requirements

This frontend requires the following backend services:

1. **Observability Backend** (port 8765) - Session and event management
2. **Context Store Server** (port 8766) - Document storage and retrieval
3. **Agent Registry** (port 8767) - Agent definition CRUD

See `docs/BACKEND-TODO.md` for details on missing backend endpoints.

## Technology Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router v6
- TanStack Table
- React Hook Form + Zod
- Axios
- React Hot Toast
- Lucide Icons

## Notes

- Some session features (stop) are mocked until backend implements them
- Desktop-optimized (no mobile responsive design in V1)
- Light theme only (no dark mode in V1)
