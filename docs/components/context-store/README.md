# Context Store

A document management system enabling persistent context sharing between agent sessions, human users, and external tools.

## Role in Architecture

The Context Store serves as the **central knowledge repository** for the Agent Orchestrator framework. While each agent session is ephemeral, the Context Store provides persistent storage for documents that need to survive across sessions.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Agent Orchestrator System                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│   │  Session 1  │    │  Session 2  │    │  Session N  │                 │
│   │  (Agent A)  │    │  (Agent B)  │    │  (Agent X)  │                 │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│          │                  │                  │                         │
│          │   ┌──────────────┴──────────────┐   │                        │
│          │   │                             │   │                         │
│          ▼   ▼                             ▼   ▼                         │
│   ┌──────────────────────────────────────────────────────────┐          │
│   │                     Context Store                         │          │
│   │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │          │
│   │  │ Documents  │  │  Metadata  │  │    Relations       │  │          │
│   │  │   (Files)  │  │  (SQLite)  │  │  (Hierarchies)     │  │          │
│   │  └────────────┘  └────────────┘  └────────────────────┘  │          │
│   └──────────────────────────────────────────────────────────┘          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key responsibilities:**
- Persist documents (architecture docs, specifications, generated artifacts) across sessions
- Enable tag-based discovery so agents can find relevant context
- Maintain document relationships for hierarchical organization
- Provide semantic search to find documents by meaning (optional)

## Features

### Document Management
Store, retrieve, and organize documents with rich metadata including tags, descriptions, and checksums. Supports any file type with automatic MIME detection.

### Tag-Based Querying
Query documents using AND logic across multiple tags. Find all documents tagged with both "architecture" and "mvp" without needing to know document IDs.

### Document Relations
Model hierarchical and peer relationships between documents. Parent-child relations cascade delete; related documents maintain loose coupling.

### Two-Phase Creation
Create placeholder documents to reserve IDs before content is ready. Useful for agent workflows that generate content incrementally.

### Surgical Editing
Edit document content using string replacement (Claude-style) or offset-based operations without full file replacement.

### Semantic Search
Find documents by meaning using vector embeddings (optional). Requires Ollama for embeddings and Elasticsearch for vector storage.

### Partial Content Retrieval
Fetch specific sections of large documents using character offsets. Combine with semantic search to retrieve only relevant sections.

## Subcomponents

The Context Store consists of three integrated subcomponents:

### Context Store Server

The core FastAPI service providing the REST API for all document operations.

**Responsibilities:**
- HTTP endpoints for CRUD operations on documents
- File storage layer for document content
- SQLite database for metadata, tags, and relations
- Optional semantic search integration (Ollama + Elasticsearch)

**Port:** `8766`

**Key files:**
- `servers/context-store/src/main.py` - FastAPI application with all endpoints
- `servers/context-store/src/storage.py` - File storage layer
- `servers/context-store/src/database.py` - SQLite operations
- `servers/context-store/src/semantic/` - Vector search module

### CLI Commands

UV-based Python scripts providing command-line access to the Context Store. Used directly by humans or invoked by Claude Code sessions as skills.

**Responsibilities:**
- Translate CLI arguments to HTTP API calls
- Format responses for human readability or JSON parsing
- Handle file I/O for push/pull operations

**Commands:** `doc-push`, `doc-pull`, `doc-create`, `doc-write`, `doc-query`, `doc-search`, `doc-info`, `doc-read`, `doc-edit`, `doc-delete`, `doc-link`

**Key files:**
- `plugins/context-store/skills/context-store/commands/` - Command implementations
- `plugins/context-store/skills/context-store/commands/lib/client.py` - HTTP client
- `plugins/context-store/skills/context-store/commands/lib/config.py` - Configuration

### MCP Server

Model Context Protocol server exposing the Context Store as MCP tools. Enables any MCP-compatible client (Claude Desktop, agent runners) to use the Context Store.

**Responsibilities:**
- Wrap CLI commands as MCP tools
- Support stdio mode (spawned by clients) and HTTP mode (persistent server)
- Auto-discover command directory for tool definitions

**Port (HTTP mode):** `9501`

**Key files:**
- `mcps/context-store/context-store-mcp.py` - MCP server implementation

## Component Interaction

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Access Patterns                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Human User                    Claude Desktop           Agent Runner    │
│       │                              │                        │          │
│       │ CLI                          │ MCP                    │ MCP      │
│       ▼                              ▼                        ▼          │
│   ┌──────────┐               ┌──────────────┐                           │
│   │   CLI    │               │  MCP Server  │                           │
│   │ Commands │               │ (stdio/HTTP) │                           │
│   └────┬─────┘               └──────┬───────┘                           │
│        │                            │                                    │
│        │         HTTP               │  Invokes CLI                       │
│        │         ┌──────────────────┘                                   │
│        │         │                                                       │
│        ▼         ▼                                                       │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    Context Store Server                          │   │
│   │                       (FastAPI :8766)                           │   │
│   │  ┌─────────────────────────────────────────────────────────┐    │   │
│   │  │                    REST API Layer                        │    │   │
│   │  │  POST /documents  GET /documents  DELETE /documents/id  │    │   │
│   │  │  PUT /content     PATCH /content  GET/POST /relations   │    │   │
│   │  └─────────────────────────────────────────────────────────┘    │   │
│   │               │                       │                          │   │
│   │               ▼                       ▼                          │   │
│   │        ┌────────────┐         ┌────────────┐                    │   │
│   │        │   Storage  │         │  Database  │                    │   │
│   │        │   (Files)  │         │  (SQLite)  │                    │   │
│   │        └────────────┘         └────────────┘                    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Direct HTTP access:** Applications can call the REST API directly for programmatic integration.

**CLI access:** Human users and scripts use CLI commands which translate to HTTP calls.

**MCP access:** AI clients use the MCP server, which invokes CLI commands internally.

## Documentation

### This Directory (Architecture & Features)
- [SERVER.md](./SERVER.md) - Server architecture, storage model, feature overview
- [CLI.md](./CLI.md) - CLI architecture, skill integration
- [MCP.md](./MCP.md) - MCP server modes, tool wrapping pattern

### Detailed References
- [Server API Reference](../../../servers/context-store/README.md#available-endpoints) - Full endpoint documentation with examples
- [Server Configuration](../../../servers/context-store/README.md#environment-variables) - All environment variables
- [CLI Commands](../../../plugins/context-store/skills/context-store/README.md#available-commands) - Command usage and examples
- [MCP Client Setup](../../../mcps/context-store/README.md#client-configuration) - Claude Desktop configuration

## Quick Reference

| Component | Port | Location |
|-----------|------|----------|
| Context Store Server | 8766 | `servers/context-store/` |
| MCP Server (HTTP) | 9501 | `mcps/context-store/` |
| CLI Commands | - | `plugins/context-store/skills/context-store/commands/` |
