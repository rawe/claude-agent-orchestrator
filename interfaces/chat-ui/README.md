# Chat UI

Customer-facing chat interface for the Agent Coordinator.

## Quick Start

```bash
npm install
npm run dev  # http://localhost:3010
```

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Agent Coordinator API (default: `http://localhost:8765`) |
| `VITE_WS_URL` | WebSocket endpoint (default: `ws://localhost:8765/ws`) |
| `VITE_AGENT_BLUEPRINT` | Agent to use for sessions |
| `VITE_APP_TITLE` | Header title |

## Requirements

Agent Coordinator must be running. See `docs/components/agent-coordinator/API.md` for API details.

## Build

```bash
npm run build    # Output in dist/
npm run preview  # Preview production build
```
