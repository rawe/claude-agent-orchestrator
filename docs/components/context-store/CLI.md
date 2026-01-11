# CLI Commands

UV-based command-line interface for interacting with the Context Store. Serves both human users and Claude Code sessions through skills.

## Role in Architecture

The CLI Commands layer provides the **primary interface** for document operations. It translates user intentions (store, find, retrieve) into HTTP API calls against the Context Store Server.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Access Patterns                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Human User              Claude Code Session                   │
│       │                          │                              │
│       │ Terminal                 │ Skill invocation             │
│       ▼                          ▼                              │
│   ┌──────────────────────────────────────────────┐             │
│   │              CLI Commands                     │             │
│   │   doc-push │ doc-query │ doc-read │ ...      │             │
│   │                                               │             │
│   │   ┌───────────────────────────────────┐      │             │
│   │   │         Shared Library            │      │             │
│   │   │   config.py  │  client.py         │      │             │
│   │   └───────────────────────────────────┘      │             │
│   └──────────────────────┬───────────────────────┘             │
│                          │ HTTP                                 │
│                          ▼                                      │
│   ┌──────────────────────────────────────────────┐             │
│   │          Context Store Server (:8766)         │             │
│   └──────────────────────────────────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture

### PEP 723 UV Scripts

Each command is a standalone Python script using [PEP 723](https://peps.python.org/pep-0723/) inline script metadata. This enables:

- **Zero installation** - Dependencies specified in the script are auto-installed by UV
- **Reproducible** - Version constraints ensure consistent behavior
- **Portable** - Single files that work in any UV-enabled environment

**Script structure:**
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx",
#     "typer",
# ]
# ///

# Command implementation...
```

The shebang allows direct execution: `./doc-push file.txt` or `uv run --script doc-push file.txt`.

### Shared Client Library

Commands share a common library (`lib/`) for HTTP communication and configuration:

| File | Purpose |
|------|---------|
| `config.py` | Environment variable handling, URL construction |
| `client.py` | HTTP client with all API operations |

The `DocumentClient` class encapsulates all server interactions, providing methods like `push_document()`, `query_documents()`, `read_document()`, etc. This ensures consistent error handling and request formatting across commands.

### Output Format

All commands output JSON for programmatic parsing (except `doc-read` which outputs raw text for piping). Errors go to stderr with exit code 1.

## Commands Overview

| Command | Purpose |
|---------|---------|
| `doc-push` | Upload file to server with tags and metadata |
| `doc-pull` | Download document to local filesystem |
| `doc-create` | Create placeholder document (no content) |
| `doc-write` | Write content to existing document |
| `doc-query` | Search documents by tags/name (AND logic) |
| `doc-search` | Semantic search by meaning (requires embeddings) |
| `doc-info` | Get document metadata and relations |
| `doc-read` | Read text document to stdout (supports partial) |
| `doc-edit` | Surgical edit via string replacement or offset |
| `doc-delete` | Permanently remove document |
| `doc-link` | Manage document relations (parent-child, related) |

## Skill Integration

The CLI commands integrate with Claude Code as a **skill**. When the skill is loaded, Claude Code can invoke commands directly.

**Skill definition:** `plugins/context-store/skills/context-store/SKILL.md`

The skill manifest uses frontmatter to describe the capability:
```yaml
---
name: context-store
description: Document management system for storing, querying, and retrieving documents across Claude Code sessions.
---
```

**How it works:**
1. Claude Code session loads the context-store skill
2. User asks Claude to "store this document" or "find documents tagged with mvp"
3. Claude invokes the appropriate command (e.g., `doc-push`, `doc-query`)
4. JSON output is parsed and presented to the user

**Key design choices:**
- Commands use absolute paths (Claude Code sessions maintain a `<skill-root>` reference)
- JSON output enables Claude to parse and reason about results
- Error messages include actionable suggestions (e.g., "Use doc-pull for binary files")

## Configuration

Commands connect to the server using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DOC_SYNC_HOST` | `localhost` | Server hostname |
| `DOC_SYNC_PORT` | `8766` | Server port |
| `DOC_SYNC_SCHEME` | `http` | Protocol (http/https) |

**Example with remote server:**
```bash
DOC_SYNC_HOST=docs.example.com DOC_SYNC_PORT=443 DOC_SYNC_SCHEME=https \
  uv run --script doc-query --tags "architecture"
```

## Key Files

| Path | Description |
|------|-------------|
| `plugins/context-store/skills/context-store/commands/` | Command implementations |
| `plugins/context-store/skills/context-store/commands/lib/config.py` | Configuration module |
| `plugins/context-store/skills/context-store/commands/lib/client.py` | HTTP client library |
| `plugins/context-store/skills/context-store/SKILL.md` | Skill manifest for Claude Code |
| `plugins/context-store/skills/context-store/README.md` | Command reference documentation |

## Related Documentation

### Architecture (this directory)
- [Context Store Overview](./README.md) - System architecture
- [Server Architecture](./SERVER.md) - REST API and storage layer
- [MCP Server Architecture](./MCP.md) - MCP protocol integration

### Detailed References (CLI README)
- [Available Commands](../../../plugins/context-store/skills/context-store/README.md#available-commands) - Full command documentation with examples
- [Configuration](../../../plugins/context-store/skills/context-store/README.md#configuration) - Environment variables reference
- [Common Workflows](../../../plugins/context-store/skills/context-store/README.md#common-workflows) - Store, retrieve, share patterns
- [Troubleshooting](../../../plugins/context-store/skills/context-store/README.md#troubleshooting) - Common issues and solutions

### Plugin Documentation
- [User Guide](../../../plugins/context-store/USER-GUIDE.md) - End-user workflows and examples
- [Skill Manifest](../../../plugins/context-store/skills/context-store/SKILL.md) - Claude Code skill definition
