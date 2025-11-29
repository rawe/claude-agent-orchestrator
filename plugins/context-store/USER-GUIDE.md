# Context Store Plugin - User Guide

## Overview

The Context Store Plugin enables Claude Code to store, query, and retrieve documents across different sessions. Documents are stored on a centralized server with tags and metadata for easy organization and discovery.

## Quick Start

### 1. Start the Context Store Server

**Using Docker (Recommended)**:
```bash
cd plugins/context-store
docker-compose up -d
```

**Verify server is running**:
```bash
curl http://localhost:8766/health
# Should return: {"status": "healthy"}
```

**Stop server**:
```bash
docker-compose down
```

### 2. Working with Claude

Simply ask Claude in natural language to manage documents:

**Store a document**:
> "Store this architecture document with tags design and api"

**Find documents**:
> "Show me all documents tagged with 'mvp'"
> "Find documents that have both 'python' and 'tutorial' tags"

**Check document info**:
> "Show me the metadata for that document"
> "What's the file size and type?"

**Read document content**:
> "Read the content of the specification document"
> "Show me the first 20 lines of that file"

**Retrieve a document**:
> "Download the API specification document"

**Remove a document**:
> "Delete the old design document"

## Natural Language Examples

Claude understands these types of requests:

### Uploading Documents
- "Save this file to the document repository with tags api and v2"
- "Store architecture.md with tags design, mvp, and description 'MVP architecture'"
- "Upload this specification document"

### Querying Documents
- "List all documents"
- "Show me documents tagged with 'design'"
- "Find documents with both 'api' and 'spec' tags"
- "Search for documents containing 'architecture' in the name"

### Checking Document Metadata
- "Show me the metadata for document doc_abc123..."
- "What's the file size and type of this document?"
- "Check the tags and creation date for doc_abc123..."

### Reading Document Content
- "Read the content of document doc_abc123..."
- "Show me the contents of the API spec document"
- "Pipe the document content to grep and search for 'authentication'"
- "Preview the first 10 lines of document doc_abc123..."

### Downloading Documents
- "Download document doc_abc123..."
- "Retrieve the API specification"
- "Get the design document and save it as design-v2.md"

### Deleting Documents
- "Delete document doc_abc123..."
- "Remove the old specification document"

## Key Concepts

### Tags
Tags are used to organize and find documents. Use consistent, descriptive tags:
- **Good**: `api`, `design`, `mvp`, `v2`
- **Avoid**: `Document`, `IMPORTANT`, `misc`

### Tag AND Logic
When searching with multiple tags, documents must have ALL tags (not just any):
- `--tags "python,api"` → Must have BOTH python AND api tags
- `--tags "mvp,design"` → Must have BOTH mvp AND design tags

### Document IDs
Each uploaded document gets a unique ID like `doc_abc123...`. Save this ID to download or delete the document later.

## Common Workflows

### Building a Knowledge Base
```
1. Ask Claude to create documentation
2. Ask Claude to store it: "Store this with tags mvp, design, api"
3. In future sessions: "Show me all mvp design documents"
4. Claude can then retrieve and reference those documents
```

### Cross-Session Documentation
```
SESSION 1:
  You: "Create an API specification for user authentication"
  Claude: [creates spec]
  You: "Store this with tags api, auth, spec"

SESSION 2 (later):
  You: "Show me the authentication API spec"
  Claude: [queries and retrieves the document]
```

### Version Management
```
# Upload v1
"Store api-spec.md with tags api, spec, v1"

# Later, upload v2
"Store api-spec-v2.md with tags api, spec, v2"

# Query specific version
"Show me v2 API specifications"
```

## Configuration

By default, commands connect to `http://localhost:8766`. To use a different server:

```bash
export DOC_SYNC_HOST=example.com
export DOC_SYNC_PORT=443
export DOC_SYNC_SCHEME=https
```

## Troubleshooting

### "Connection refused" errors
**Problem**: Document server is not running.
**Solution**: Start the server with `docker-compose up -d`

### Documents not found
**Problem**: Document was deleted or ID is incorrect.
**Solution**: Ask Claude to list all documents or search by tags to find the correct ID.

### Server not accessible
**Problem**: Server configuration is incorrect.
**Solution**: Check that server is running at the configured host and port.

## Best Practices

1. **Use descriptive tags**: Makes documents easier to find later
2. **Be consistent**: Use the same tag format (lowercase, hyphens)
3. **Add descriptions**: Helps identify documents in query results
4. **Organize by project phase**: Use tags like `mvp`, `v1`, `v2`
5. **Regular cleanup**: Delete outdated documents to keep repository organized

## Manual Command Usage

While Claude can handle document operations through natural language, you can also run commands directly:

```bash
# Upload
uv run skills/context-store/commands/doc-push file.txt --tags "tag1,tag2"

# Query
uv run skills/context-store/commands/doc-query --tags "tag1"

# Download
uv run skills/context-store/commands/doc-pull doc_abc123...

# Delete
uv run skills/context-store/commands/doc-delete doc_abc123...
```

See `skills/context-store/README.md` for detailed command documentation.

## Additional Resources

- **Server Setup**: See `document-server/README.md`
- **Architecture**: See `docs/goal.md`
- **Command Reference**: See `skills/context-store/SKILL.md`
