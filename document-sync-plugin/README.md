# Document Sync Plugin

A document management system that enables Claude Code sessions to store, retrieve, and query documents across different sessions through a centralized server.

## Overview

The Document Sync Plugin provides a simple interface for Claude Code to:
- **Store documents** with metadata (tags, descriptions) for future reference
- **Retrieve documents** by ID to access previously saved information
- **Query documents** by name or tags to discover relevant content
- **Delete documents** to manage the document repository

## Architecture

```
┌─────────────────────────┐
│   Claude Code Session   │
│  Uses document-sync     │
│  skill commands         │
└───────────┬─────────────┘
            │ HTTP Requests
            ▼
┌─────────────────────────┐
│   Document Server       │
│   (FastAPI)             │
└───────────┬─────────────┘
            ▼
    ┌───────────────┐
    │  File Storage │
    │  + SQLite DB  │
    └───────────────┘
```

### Components

- **Document Server** - FastAPI application with RESTful API, file storage, and SQLite database
- **CLI Commands** - UV-based scripts for document operations: `doc-push`, `doc-pull`, `doc-query`, `doc-delete`

## Quick Start

### 1. Start the Document Server

Using Docker:

```bash
docker-compose up -d
```

Server available at `http://localhost:8766`. Verify it's running:

```bash
curl http://localhost:8766/health
```

Stop the server:
```bash
docker-compose down
```

> For local development setup, see the [Document Server README](document-server/README.md)

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

- **[Document Server](document-server/README.md)** - Server setup, API, configuration, testing
- **[CLI Commands](skills/document-sync/README.md)** - Command usage and examples
- **[Architecture Details](docs/goal.md)** - Vision and design decisions
- **[Implementation Guides](docs/implementation/)** - Block-by-block implementation checklists

## Key Features

- **Metadata-rich storage** - Documents include tags, descriptions, checksums, MIME types
- **Tag-based querying** - Find documents by tags with AND logic
- **Integrity verification** - SHA256 checksums
- **Docker deployment** - Simple containerized setup
- **RESTful API** - Clean HTTP interface

## Use Cases

- Share architecture documents between planning and implementation sessions
- Store and retrieve API specifications across multiple development sessions
- Query design documents by tags when working on related features
- Maintain a knowledge base of project documentation accessible to Claude

## Requirements

- **Docker and Docker Compose** - For containerized deployment (recommended)
- **Python 3.11+** - Required for local development
- **UV package manager** - For dependency management and CLI script execution
- **jq** - Optional, for running integration tests


## Implementation Status

✅ **Block 01** - Server Foundation
✅ **Block 02** - Storage & Database
✅ **Block 03** - CLI Commands
✅ **Block 04** - Integration & Docker
📋 **Block 05** - Skill Registration (pending)