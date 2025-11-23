---
name: document-sync
description: Document management system for storing, querying, and retrieving documents across Claude Code sessions. Use this to maintain knowledge bases, share documents between agent. Whenever you encounter a <document id=*> in a session, use this skill to retrieve its content.
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

**CRITICAL**: Always use absolute paths - NEVER use `cd`:

### `doc-push` - Upload Documents
```bash
uv run <skill-root>/commands/doc-push <file> [--tags TEXT] [--description TEXT]
# Example: uv run <skill-root>/commands/doc-push specs.md --tags "api,v2"
```
**Use when**: Store a document for future reference.

### `doc-query` - Search Documents
```bash
uv run <skill-root>/commands/doc-query [--tags TEXT] [--name TEXT]
# Example: uv run <skill-root>/commands/doc-query --tags "api,v2"
```
**Use when**: Find documents by tags (AND logic) or name patterns.

### `doc-info` - Get Document Metadata
```bash
uv run <skill-root>/commands/doc-info <document-id>
# Example: uv run <skill-root>/commands/doc-info doc_abc123
```
**Use when**: View metadata for a specific document without downloading it.

### `doc-read` - Read Text Documents
```bash
uv run <skill-root>/commands/doc-read <document-id>
# Example: uv run <skill-root>/commands/doc-read doc_abc123
```
**Use when**: Output text document content directly to stdout (text files only).

### `doc-pull` - Download Documents
```bash
uv run <skill-root>/commands/doc-pull <document-id> [-o PATH]
# Example: uv run <skill-root>/commands/doc-pull doc_abc123 -o specs.md
```
**Use when**: Retrieve a document by its ID.

### `doc-delete` - Remove Documents
```bash
uv run <skill-root>/commands/doc-delete <document-id>
# Example: uv run <skill-root>/commands/doc-delete doc_abc123
```
**Use when**: Permanently remove a document.

---

## Typical Workflows

### Store and Retrieve
```bash
# Upload with tags
uv run <skill-root>/commands/doc-push specs.md --tags "api,v2"

# Find it later
uv run <skill-root>/commands/doc-query --tags "api,v2"

# Download it
uv run <skill-root>/commands/doc-pull doc_abc123
```

### Build Knowledge Base
```bash
# Upload multiple documents with consistent tags
uv run <skill-root>/commands/doc-push architecture.md --tags "design,mvp"
uv run <skill-root>/commands/doc-push api-spec.md --tags "api,mvp"

# Query by project phase
uv run <skill-root>/commands/doc-query --tags "mvp"
```

---

## Key Concepts

### Tag AND Logic
**IMPORTANT**: Multiple tags means ALL must match:
- `--tags "python,api"` → Document must have BOTH tags
- `--tags "v2,design,spec"` → Document must have ALL THREE tags

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
