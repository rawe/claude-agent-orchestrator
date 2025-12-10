# Agent Callback Architecture - Implementation Guide

## Overview

This directory contains documentation for the **Agent Callback Architecture** feature, which enables parent-child relationships between agent sessions. When a parent agent spawns a child session with `callback=true`, the system tracks this relationship and can automatically resume the parent when the child completes.

### Key Capability

```
Parent Agent (orchestrator)
    │
    ├─ starts child with callback=true
    │
    ▼
Child Agent (worker)
    │
    ├─ completes task
    │
    ▼
Parent Agent resumes (callback triggered)
```

---

## Architecture Summary

### Before (Subprocess-based)
```
MCP Server
    ↓ spawns subprocess
ao-start / ao-resume
    ↓ uses
Claude Agent SDK
    ↓ calls
Agent Runtime API
```

### After (API-based with Callback Support)
```
MCP Server
    ↓ HTTP calls with X-Agent-Session-Name header
Agent Runtime API (Jobs API)
    ↓ stores parent_session_name
Agent Launcher
    ↓ spawns with AGENT_SESSION_NAME env var
ao-start / ao-resume
    ↓ uses
Claude Agent SDK
```

### Parent Session Tracking Flow

1. **Agent Launcher** sets `AGENT_SESSION_NAME={session_name}` when spawning sessions
2. **Claude Code** replaces `${AGENT_SESSION_NAME}` in MCP config headers
3. **MCP Server** receives `X-Agent-Session-Name` header identifying the caller
4. **Jobs API** stores `parent_session_name` when `callback=true`
5. **Agent Runtime** links parent to child session in database

---

## Documentation Index

### Implementation Guides

| Document | Description |
|----------|-------------|
| [MCP Server API Refactor](./mcp-server-api-refactor.md) | Complete architecture and implementation guide for refactoring the MCP server from subprocess-based to API-based |
| [Implementation Report](./mcp-server-api-refactor-report.md) | Phase-by-phase completion status and verification results |
| [Known Bugs](./mcp-server-api-refactor-bugs.md) | Bug tracking for issues discovered during implementation |
| [Callback Flow Test Plan](./callback-flow-test-plan.md) | Step-by-step testing procedures for verifying callback flow |
| [Next Steps](./callback-architecture-next-steps.md) | Remaining work items (dashboard enhancements, debugging) |
| [Callback Queue for Busy Parents](../06-callback-queue-busy-parent.md) | Fix for lost callbacks when parent agents are busy |

### Reading Order

1. Start with **MCP Server API Refactor** for architecture understanding
2. Review **Implementation Report** for current status
3. Use **Callback Flow Test Plan** to verify the implementation
4. Check **Known Bugs** for any issues to be aware of
5. See **Next Steps** for remaining work

---

## Key Files

### MCP Server
- `interfaces/agent-orchestrator-mcp-server/libs/server.py` - MCP tool definitions
- `interfaces/agent-orchestrator-mcp-server/libs/core_functions.py` - Business logic
- `interfaces/agent-orchestrator-mcp-server/libs/api_client.py` - HTTP client for Jobs API
- `interfaces/agent-orchestrator-mcp-server/libs/constants.py` - Configuration constants

### Agent Runtime
- `servers/agent-runtime/main.py` - API endpoints including Jobs API
- `servers/agent-runtime/database.py` - Session and event storage
- `servers/agent-runtime/services/job_queue.py` - Job queue with parent tracking
- `servers/agent-runtime/services/callback_processor.py` - Callback queuing for busy parents

### Agent Launcher
- `servers/agent-launcher/lib/executor.py` - Sets `AGENT_SESSION_NAME` env var

### Agent Configuration
- `config/agents/agent-orchestrator/agent.mcp.json` - MCP config with header template

---

## Quick Verification

To verify the callback architecture is working:

```bash
# 1. Check infrastructure is running
curl -s http://localhost:8765/health

# 2. Create a job with parent_session_name
curl -X POST http://localhost:8765/jobs \
  -H "Content-Type: application/json" \
  -d '{"type":"start_session","session_name":"test-child","prompt":"Say hello","parent_session_name":"test-parent"}'

# 3. Wait for completion, then verify parent is recorded
curl http://localhost:8765/sessions/by-name/test-child | jq '.session.parent_session_name'
# Expected: "test-parent"
```

---

## Status

| Component | Status |
|-----------|--------|
| Jobs API with parent_session_name | ✅ Complete |
| Session-Job linking | ✅ Complete |
| MCP Server API refactor | ✅ Complete |
| HTTP header extraction | ✅ Complete |
| Callback queue for busy parents | ✅ Complete |
| Dashboard parent display | ⏳ Pending |

---

## Related Components

- **Dashboard**: `dashboard/src/` - Frontend for viewing sessions
- **Context Store**: Document management for cross-session knowledge sharing
- **Agent Blueprints**: `config/agents/` - Agent configuration templates
