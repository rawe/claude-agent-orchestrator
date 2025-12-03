---
name: context-store
description: Context Store - Document management system for storing, querying, and retrieving documents across Claude Code sessions. Use this to maintain knowledge bases, share documents between agents. Whenever you encounter a <document id=*> in a session, use this skill to retrieve its content.
---

# Context Store Skill

## What & When

**What**: Commands for uploading, downloading, querying, and deleting documents with metadata and tags through the Context Store server.

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

### `doc-query` - Search by Tags/Name
```bash
uv run <skill-root>/commands/doc-query [--tags TEXT] [--name TEXT]
# Example: uv run <skill-root>/commands/doc-query --tags "api,v2"
```
**Use when**: Find documents by tags (AND logic) or name patterns.

### `doc-search` - Semantic Search
```bash
uv run <skill-root>/commands/doc-search "<query>" [--limit INT]
# Example: uv run <skill-root>/commands/doc-search "how to configure authentication"
```
**Use when**: Find documents by meaning using natural language queries.
**Note**: Requires semantic search enabled on server. Returns section offsets for partial reads.

### `doc-info` - Get Document Metadata & Relations
```bash
uv run <skill-root>/commands/doc-info <document-id>
# Example: uv run <skill-root>/commands/doc-info doc_abc123
```
**Use when**: View metadata and relations for a specific document without downloading it.
**Output**: Includes `relations` field with parent/child/related document links.

### `doc-read` - Read Text Documents
```bash
uv run <skill-root>/commands/doc-read <document-id> [--offset INT] [--limit INT]
# Example: uv run <skill-root>/commands/doc-read doc_abc123
# Partial: uv run <skill-root>/commands/doc-read doc_abc123 --offset 2000 --limit 1000
```
**Use when**: Output text document content directly to stdout (text files only).
**Partial reads**: Use `--offset` and `--limit` to retrieve specific sections (useful with semantic search results).

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

### `doc-link` - Manage Document Relations
```bash
uv run <skill-root>/commands/doc-link --types                     # List relation types
uv run <skill-root>/commands/doc-link --create <from> <to> [opts] # Create relation
uv run <skill-root>/commands/doc-link --update <id> --note "..."  # Update note
uv run <skill-root>/commands/doc-link --remove <id>               # Remove relation
```
**Use when**: Link documents together in parent-child or peer relationships.
**Options for --create**:
- `--type` - Required: `parent-child` (hierarchical) or `related` (peer)
- `--from-note` - Note from source perspective
- `--to-note` - Note from target perspective

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

### Semantic Search + Partial Read
```bash
# Search by meaning
uv run <skill-root>/commands/doc-search "how to authenticate users"
# Returns: {"results": [{"document_id": "doc_abc", "sections": [{"offset": 2000, "limit": 1000}]}]}

# Read only the relevant section
uv run <skill-root>/commands/doc-read doc_abc --offset 2000 --limit 1000
```

### Link Related Documents
```bash
# Create hierarchical relationship (parent owns children)
uv run <skill-root>/commands/doc-link --create doc_architecture doc_api --type parent-child --from-note "API spec"

# Create peer relationship
uv run <skill-root>/commands/doc-link --create doc_api doc_models --type related --from-note "Data models"

# View document with its relations
uv run <skill-root>/commands/doc-info doc_architecture
```

---

## Key Concepts

### Tag AND Logic
**IMPORTANT**: Multiple tags means ALL must match:
- `--tags "python,api"` → Document must have BOTH tags
- `--tags "v2,design,spec"` → Document must have ALL THREE tags

### Output Format
All commands output JSON. Save document IDs from upload for later retrieval/deletion.

### Document Relations
**Relation Types**:
- **parent-child**: Hierarchical ownership. Deleting parent cascades to children.
- **related**: Peer relationship. No cascade delete.

**Bidirectional**: Relations are stored from both perspectives. Creating a parent-child link adds:
- `parent` relation on the parent document
- `child` relation on the child document

---

## Notes for AI Assistants

1. **Tag AND logic** - Multiple tags = ALL must match
2. **Save document IDs** - From upload output for future operations
3. **Check server running** - Handle connection errors gracefully
4. **Parse JSON output** - All commands return JSON
5. **Tags are lowercase** - Use consistent tag naming (`python` not `Python`)
6. **Relations in doc-info** - Use `doc-info` to see document relations without a separate call
7. **Relation IDs** - Save relation IDs from create output for update/remove operations
8. **Cascade delete** - Deleting a parent document also deletes its children

---

## Quick Decision Tree

**Store document?** → `doc-push <file> --tags "tag1,tag2"`

**Find by tags?** → `doc-query --tags "tag1,tag2"` (AND logic)

**Find by meaning?** → `doc-search "your question"` (semantic search)

**Check metadata?** → `doc-info <doc-id>` (metadata + relations)

**Read text file?** → `doc-read <doc-id>` (text files to stdout)

**Read section?** → `doc-read <doc-id> --offset 2000 --limit 1000` (partial read)

**Download document?** → `doc-pull <doc-id>` (ID from query)

**Remove document?** → `doc-delete <doc-id>` (permanent)

**List all?** → `doc-query` (no args)

**Link documents?** → `doc-link --create <from> <to> --type parent-child`

**List relation types?** → `doc-link --types`

**Update link note?** → `doc-link --update <id> --note "text"`

**Remove link?** → `doc-link --remove <id>` (removes both directions)

---

## Additional Resources

- **Detailed Command Reference**: See `references/COMMANDS.md`
- **Configuration Options**: See `references/CONFIGURATION.md`
- **Error Handling**: See `references/TROUBLESHOOTING.md`
