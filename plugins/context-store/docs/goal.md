# Document Sync Plugin - Goal

## Vision

Enable AI coding sessions to store, retrieve, and query documents through a centralized document management system, allowing Claude to maintain context and share information across different sessions.

## Core Purpose

Provide a simple interface for Claude Code to:
- **Store documents** with metadata (name, tags, description) for future reference
- **Retrieve documents** by ID to access previously saved information
- **Query documents** by name or tags to discover relevant content
- **Delete documents** to manage the document repository

## High-Level Architecture

The system follows a **client-skill architecture** similar to the Agent Orchestrator Framework's observability pattern:

```
┌─────────────────────────┐
│   Claude Code Session   │
│                         │
│  Uses document-sync     │
│  skill commands         │
└───────────┬─────────────┘
            │
            │ HTTP Requests
            │ (push/pull/query/delete)
            ▼
┌─────────────────────────┐
│   Document Server       │
│   (FastAPI)             │
│                         │
│  - Receives documents   │
│  - Stores files         │
│  - Manages metadata     │
│  - Handles queries      │
└───────────┬─────────────┘
            │
            ▼
    ┌───────────────┐
    │  File Storage │
    │  + SQLite DB  │
    └───────────────┘
```

## Component Interaction

1. **Document Sync Skill** (Client Side)
   - UV-based Python command-line tools
   - Commands: `doc-push`, `doc-pull`, `doc-query`, `doc-delete`
   - Communicates with server via HTTP
   - Returns JSON responses for Claude to interpret

2. **Document Server** (Server Side)
   - Standalone FastAPI application
   - RESTful API endpoints for CRUD operations
   - File system storage for document content
   - SQLite database for metadata and tag management

## Key Features

- **Metadata-rich storage**: Documents include name, tags, description, checksums, MIME types
- **Tag-based querying**: Find documents by tags with AND logic for precise filtering
- **Integrity verification**: SHA256 checksums ensure document integrity
- **Simple deployment**: Docker support with environment-based configuration

## Use Cases

- Share architecture documents between planning and implementation sessions
- Store and retrieve API specifications across multiple development sessions
- Query design documents by tags when working on related features
- Maintain a knowledge base of project documentation accessible to Claude
