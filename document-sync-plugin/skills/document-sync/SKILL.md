---
name: document-sync
description: Document management system for storing, querying, and retrieving documents across Claude Code sessions. Use this to maintain knowledge bases, share documents between sessions, and build persistent documentation repositories.
---

# Document Sync Skill

## What & When

**What**: Commands for uploading, downloading, querying, and deleting documents with metadata and tags through a centralized document server.

**When to use**:
- Store important documents for retrieval in future sessions
- Build a knowledge base of project documentation
- Share architecture, API specs, or design documents across different work sessions
- Query documents by tags to find relevant information

**Key Benefits**:
- Cross-session persistence
- Tag-based organization with AND logic
- Simple JSON output

---

## Quick Reference

### `doc-push` - Upload Documents
```bash
uv run commands/doc-push <file> [--tags TEXT] [--description TEXT]
```
**Use when**: Store a document for future reference.

### `doc-query` - Search Documents
```bash
uv run commands/doc-query [--tags TEXT] [--name TEXT]
```
**Use when**: Find documents by tags (AND logic) or name patterns.

### `doc-info` - Get Document Metadata
```bash
uv run commands/doc-info <document-id>
```
**Use when**: View metadata for a specific document without downloading it.

### `doc-read` - Read Text Documents
```bash
uv run commands/doc-read <document-id>
```
**Use when**: Output text document content directly to stdout (text files only). Useful for piping to other tools.

### `doc-pull` - Download Documents
```bash
uv run commands/doc-pull <document-id> [-o PATH]
```
**Use when**: Retrieve a document by its ID.

### `doc-delete` - Remove Documents
```bash
uv run commands/doc-delete <document-id>
```
**Use when**: Permanently remove a document.

---

## Command Location

**IMPORTANT**: All commands are in the `commands/` subdirectory.

```bash
# Execute using full path to commands
uv run <skill-root>/commands/doc-push architecture.md --tags "design,api"
```

---

## Typical Workflows

### Store and Retrieve
```bash
# Upload with tags
uv run commands/doc-push specs.md --tags "api,v2"

# Find it later
uv run commands/doc-query --tags "api,v2"

# Download it
uv run commands/doc-pull doc_abc123...
```

### Build Knowledge Base
```bash
# Upload multiple documents with consistent tags
uv run commands/doc-push architecture.md --tags "design,mvp"
uv run commands/doc-push api-spec.md --tags "api,mvp"

# Query by project phase
uv run commands/doc-query --tags "mvp"
```

---

## Key Concepts

### Tag AND Logic
**IMPORTANT**: Multiple tags means ALL must match:
- `--tags "python,api"` → Document must have BOTH tags
- `--tags "v2,design,spec"` → Document must have ALL THREE tags

### Prerequisites
- Document server must be running (default: `http://localhost:8766`)
- Check health: `curl http://localhost:8766/health`

### Output Format
All commands output JSON. Save document IDs from upload for later retrieval/deletion.

---

## Notes for AI Assistants

1. **Tag AND logic** - Multiple tags = ALL must match
2. **Save document IDs** - From upload output for future operations
3. **Check server running** - Handle connection errors gracefully
4. **Parse JSON output** - All commands return JSON
5. **Tags are lowercase** - Use consistent tag naming (`python` not `Python`)

---

## Quick Decision Tree

**Store document?** → `doc-push <file> --tags "tag1,tag2"`

**Find documents?** → `doc-query --tags "tag1,tag2"` (AND logic)

**Check metadata?** → `doc-info <doc-id>` (metadata only)

**Read text file?** → `doc-read <doc-id>` (text files to stdout)

**Download document?** → `doc-pull <doc-id>` (ID from query)

**Remove document?** → `doc-delete <doc-id>` (permanent)

**List all?** → `doc-query` (no args)

---

## Additional Resources

- **Detailed Command Reference**: See `references/COMMANDS.md`
- **Configuration Options**: See `references/CONFIGURATION.md`
- **Error Handling**: See `references/TROUBLESHOOTING.md`
