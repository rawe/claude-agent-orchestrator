# Documentation

This folder contains all project documentation organized by purpose and audience.

## Start Here

| Document | Description |
|----------|-------------|
| [VISION.md](./VISION.md) | Project vision, core pillars, and long-term goals. Start here to understand *why* this framework exists |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System overview, core terminology, and component structure. Understand *how* the Agent Orchestrator works |
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Prerequisites, setup instructions, and quick start guide for local development |

## Documentation Map

### For Understanding the System

| Section | Purpose | When to Read |
|---------|---------|--------------|
| [architecture/](./architecture/) | Cross-cutting concerns (auth, SSE, MCP integration) | Understanding how components interact |
| [adr/](./adr/README.md) | Why decisions were made | Understanding design rationale |

### For Using Features

| Section | Purpose | When to Read |
|---------|---------|--------------|
| [features/](./features/README.md) | Implemented feature documentation | Learning what the system does |
| [components/](./components/) | API docs, schemas, data models | Building integrations |
| [setup/](./setup/) | Deployment guides | Configuring external services |
| [reference/](./reference/) | Quick-reference specs | Looking up schemas/formats |

### For Contributors

| Section | Purpose | When to Read |
|---------|---------|--------------|
| [design/](./design/README.md) | Planned feature specifications | Before implementing new features |
| [refactoring/](./refactoring/README.md) | Technical debt and improvements | Finding improvement opportunities |

## Quick Links

- **Sessions & Runs**: [ARCHITECTURE.md](./ARCHITECTURE.md) → [features/](./features/)
- **Authentication**: [architecture/auth-oidc.md](./architecture/auth-oidc.md)
- **MCP Integration**: [architecture/mcp-runner-integration.md](./architecture/mcp-runner-integration.md)
- **Capabilities System**: [features/capabilities-system.md](./features/capabilities-system.md)
