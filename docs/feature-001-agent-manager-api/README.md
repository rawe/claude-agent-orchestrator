# Feature 001: Agent Manager API

## Overview

Create an **Agent Manager API Service** that provides HTTP endpoints for agent CRUD operations and status management. This feature enables the unified frontend to manage agent definitions through a RESTful API while maintaining 100% backward compatibility with the existing file-based storage system.

## Status

✅ **Approved** - Ready for implementation

## Key Goals

1. Provide HTTP API for agent CRUD operations
2. Enable frontend-based agent management
3. Support Python CLI commands for reading agent configurations
4. Maintain file-based storage for backward compatibility
5. Support agent activation/deactivation via status toggle

## Core Principles

- **File-based storage**: Continue using `.agent-orchestrator/agents/{name}/` structure
- **API-first**: Python CLI and frontend both consume HTTP API (port 8767)
- **Signal file for status**: `.disabled` file indicates inactive agent
- **Minimal abstraction**: Simple file operations wrapper, no complex ORM
- **Shared validation**: Single source of truth for agent validation rules

## Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Python CLI │ ──HTTP─→│ Agent Manager    │ ──R/W─→ │  File System    │
│  Commands   │         │ Service :8767    │         │  .agent-orch... │
└─────────────┘         └──────────────────┘         └─────────────────┘
                                  ↑
                                  │ HTTP
                                  │
                        ┌─────────────────┐
                        │ Unified         │
                        │ Frontend        │
                        └─────────────────┘
```

## Implementation Timeline

**Total Estimated Time**: 3-4 weeks

- Phase 1: Agent Manager Service (New) - 2 weeks
- Phase 2: Update Python CLI Commands - 1 week
- Phase 3: Update Frontend - 1 week
- Phase 4: Testing & Validation - ongoing

## Documents

- **[IMPL-001-implementation-plan.md](./IMPL-001-implementation-plan.md)** - Detailed implementation plan with step-by-step instructions

## Related Features

- Agent definitions are consumed by the agent orchestration system
- Integrates with the observability backend for agent session tracking

## Next Steps

1. Review and approve this implementation plan
2. Begin Phase 1: Agent Manager Service implementation
3. Test each phase before proceeding to the next
