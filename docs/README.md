# Documentation

This folder contains all project documentation organized by purpose and audience.

## Start Here

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System overview, terminology, and component structure |
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Prerequisites and setup guide for local development |

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

### For Deployment & Operations

| Section | Purpose | When to Read |
|---------|---------|--------------|
| [containers/](./containers/README.md) | Container images, environment variables, volumes | Deploying with Docker |
| [RELEASING.md](./RELEASING.md) | Release process, versioning, CI/CD workflow | Publishing new versions |

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
- **Container Images**: [containers/](./containers/README.md)
- **Release Process**: [RELEASING.md](./RELEASING.md)
