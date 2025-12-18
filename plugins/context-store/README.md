# Context Store Plugin

A document management system that enables Claude Code sessions to store, retrieve, and query documents across different sessions through a centralized server.

## Overview

The Context Store Plugin provides a simple interface for Claude Code to:
- **Store documents** with metadata (tags, descriptions) for future reference
- **Query documents** by name or tags to discover relevant content
- **Get document metadata** to inspect file info without downloading
- **Read text documents** directly to stdout for piping and processing
- **Retrieve documents** by ID to access previously saved information
- **Delete documents** to manage the document repository

## Architecture

```
┌─────────────────────────┐
│   Claude Code Session   │
│  Uses context-store     │
│  skill commands         │
└───────────┬─────────────┘
            │ HTTP Requests
            ▼
┌─────────────────────────┐
│   Context Store Server  │
│   (FastAPI)             │
└───────────┬─────────────┘
            ▼
    ┌───────────────┐
    │  File Storage │
    │  + SQLite DB  │
    └───────────────┘
```

### Components

- **Context Store Server** - FastAPI application with RESTful API, file storage, and SQLite database
- **CLI Commands** - UV-based scripts for document operations: `doc-push`, `doc-query`, `doc-info`, `doc-read`, `doc-pull`, `doc-delete`

## Quick Start

### 1. Start the Context Store Server

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

> For local development setup, see the [Context Store Server README](../../servers/context-store/README.md)

### 2. Working with Claude Code

Ask Claude in natural language to manage documents:

```
"Store this architecture document with tags design and api"
"Show me all documents tagged with 'mvp'"
"Find documents that have both 'python' and 'tutorial' tags"
"Download the API specification document"
```

Claude will use the context-store commands automatically. See [USER-GUIDE.md](USER-GUIDE.md) for more examples and workflows.

### 3. Manual Command Usage

You can also run commands directly:

```bash
# Upload a document
uv run --script skills/context-store/commands/doc-push file.txt --tags "tag1,tag2"

# Query documents
uv run --script skills/context-store/commands/doc-query --tags "tag1"

# Get document metadata
uv run --script skills/context-store/commands/doc-info doc_abc123...

# Read text document content
uv run --script skills/context-store/commands/doc-read doc_abc123...

# Download a document
uv run --script skills/context-store/commands/doc-pull doc_abc123...

# Delete a document
uv run --script skills/context-store/commands/doc-delete doc_abc123...
```

## Documentation

- **[USER GUIDE](USER-GUIDE.md)** - How to use with Claude Code (start here!)
- **[Context Store Server](../../servers/context-store/README.md)** - Server setup, API, configuration, testing
- **[CLI Commands](skills/context-store/README.md)** - Command usage and examples
- **[Claude Code Skill](skills/context-store/SKILL.md)** - Documentation for Claude

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
✅ **Block 05** - Skill Registration & Claude Code Integration