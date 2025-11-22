# Document Sync Plugin

A document management system that enables Claude Code sessions to store, retrieve, and query documents across different sessions through a centralized server.

## Purpose

The Document Sync Plugin allows Claude Code to:
- **Store documents** with metadata (tags, descriptions) for future reference
- **Retrieve documents** by ID to access previously saved information
- **Query documents** by name or tags to discover relevant content
- **Delete documents** to manage the document repository

## Architecture

The system uses a client-server architecture with two main components:

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

### Components

1. **Document Server** (`document-server/`)
   - FastAPI application with RESTful API
   - File storage with SQLite metadata database
   - Tag-based querying with AND logic
   - SHA256 checksums for integrity

2. **CLI Commands** (`skills/document-sync/`)
   - UV-based scripts: `doc-push`, `doc-pull`, `doc-query`, `doc-delete`
   - JSON output for easy integration
   - Environment-based configuration

## Quick Start

### 1. Start the Document Server

```bash
cd document-server
uv sync
uv run python -m src.main
```

Server runs on `http://localhost:8766` (configurable via environment variables).

### 2. Use CLI Commands

```bash
# Upload a document
uv run skills/document-sync/commands/doc-push file.txt --tags "tag1,tag2"

# Query documents
uv run skills/document-sync/commands/doc-query --tags "tag1"

# Download a document
uv run skills/document-sync/commands/doc-pull doc_abc123...

# Delete a document
uv run skills/document-sync/commands/doc-delete doc_abc123...
```

## Documentation

- **[Document Server](document-server/README.md)** - Server setup, API reference, configuration
- **[CLI Commands](skills/document-sync/README.md)** - Command usage, examples, configuration
- **[Architecture](docs/goal.md)** - Detailed vision and architecture decisions
- **[Implementation Guides](docs/implementation/)** - Block-by-block implementation checklists

## Key Features

- **Metadata-rich storage** - Documents include tags, descriptions, checksums, MIME types
- **Tag-based querying** - Find documents by tags with AND logic for precise filtering
- **Integrity verification** - SHA256 checksums ensure document integrity
- **Environment configuration** - Flexible setup via environment variables
- **UV-based scripts** - Zero-installation CLI with automatic dependency management

## Use Cases

- Share architecture documents between planning and implementation sessions
- Store and retrieve API specifications across multiple development sessions
- Query design documents by tags when working on related features
- Maintain a knowledge base of project documentation accessible to Claude

## Requirements

- **Python 3.11+** - Required for both server and CLI
- **UV package manager** - For dependency management and script execution
- **SQLite** - Included with Python, used for metadata storage


## Implementation Progress (can be removed when complete!)

### ✅ Completed Blocks

- **Block 01: Server Foundation** - FastAPI application with REST endpoints
- **Block 02: Storage & Database** - File storage, SQLite, checksums, tag querying
- **Block 03: CLI Commands** - UV-based scripts for document operations

### 📋 Pending Blocks

- **Block 04: Integration Testing** - End-to-end testing of CLI + Server workflow
- **Block 05: Skill Registration** - Register plugin with Claude Code skill system