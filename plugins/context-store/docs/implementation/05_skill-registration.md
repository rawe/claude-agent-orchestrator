# Implementation Block 05: Skill Registration & Claude Code Integration

## Goal
Register the document-sync skill with Claude Code, create skill documentation, test Claude's ability to use the commands, and validate the complete end-to-end integration in real Claude Code sessions.

## Benefit
🎯 **Claude Code Can Use Document Sync** - The final piece! Claude can now autonomously push, query, pull, and delete documents during coding sessions. The system is fully integrated and ready for production use.

## MVP Architecture Reference

**Document**: [`architecture-mvp.md`](../architecture-mvp.md)

**Relevant Sections**:
- `Skill Registration` (lines 791-833)
- `skill.json` (lines 795-801)
- `SKILL.md` (lines 803-832)
- `Complete Flow Diagram` (lines 836-870)

## What Gets Built

### 1. Skill Metadata Files
- **skill.json** - Skill registration metadata
- **SKILL.md** - Claude-facing documentation with usage examples

### 2. Integration Testing with Claude
- Manual test scenarios in Claude Code
- Validation that Claude can discover and use commands
- Edge case testing

### 3. User Documentation
- Quick start guide for Claude Code users
- Example prompts for Claude
- Best practices

## Session Flow

### Step 1: Create Skill Registration Files (~30min)

1. **Create skills/document-sync/skill.json**
   ```json
   {
     "name": "document-sync",
     "version": "1.0.0",
     "description": "Document push/pull/query/delete system for AI coding sessions. Store, retrieve, and manage documents across sessions with tagging and search capabilities.",
     "author": "Your Name",
     "commands": {
       "doc-push": "commands/doc-push",
       "doc-pull": "commands/doc-pull",
       "doc-query": "commands/doc-query",
       "doc-delete": "commands/doc-delete"
     },
     "dependencies": {
       "python": ">=3.11",
       "uv": "*"
     }
   }
   ```

2. **Create skills/document-sync/SKILL.md**

   This is the critical file that Claude reads to understand how to use the skill:

   ```markdown
   # Document Sync Skill

   This skill provides document management capabilities for storing, retrieving, searching, and deleting documents during AI coding sessions.

   ## When to Use This Skill

   Use this skill when you need to:
   - Store documents for later retrieval across sessions
   - Keep reference documents organized with tags
   - Search for previously stored documents
   - Share documents between different work sessions
   - Maintain a repository of architecture docs, specs, notes, etc.

   ## Available Commands

   ### doc-push - Upload Document

   Upload a document to the central repository.

   **Usage**:
   ```bash
   uv run doc-push <file-path> [--name NAME] [--tags TAGS] [--description DESC]
   ```

   **Arguments**:
   - `file-path` (required): Path to file to upload
   - `--name` (optional): Friendly name (defaults to filename)
   - `--tags` (optional): Comma-separated tags for categorization
   - `--description` (optional): Document description

   **Returns**: JSON with document_id and metadata

   **Example**:
   ```bash
   uv run doc-push ./architecture.md --name "System Architecture" --tags "design,docs,v2" --description "Latest system architecture"
   ```

   ---

   ### doc-query - Search Documents

   Query documents by name or tags.

   **Usage**:
   ```bash
   uv run doc-query [--name NAME] [--tags TAGS] [--limit N]
   ```

   **Arguments**:
   - `--name` (optional): Filter by name (substring match)
   - `--tags` (optional): Filter by tags (comma-separated, **AND logic** - document must have ALL specified tags)
   - `--limit` (optional): Maximum results [default: 50]

   **Returns**: JSON array of matching documents

   **Example**:
   ```bash
   # Find all design documents
   uv run doc-query --tags "design"

   # Find documents with BOTH design AND v2 tags
   uv run doc-query --tags "design,v2"

   # Search by name
   uv run doc-query --name "architecture"
   ```

   ---

   ### doc-pull - Download Document

   Download a document by its ID.

   **Usage**:
   ```bash
   uv run doc-pull <document-id> [--output PATH]
   ```

   **Arguments**:
   - `document-id` (required): Document ID from push or query
   - `--output` (optional): Output file path (defaults to original filename)

   **Returns**: JSON with download confirmation

   **Example**:
   ```bash
   # Get document ID from query first
   DOC_ID=$(uv run doc-query --name "architecture" | jq -r '.[0].document_id')

   # Pull the document
   uv run doc-pull $DOC_ID --output ./downloaded-architecture.md
   ```

   ---

   ### doc-delete - Delete Document

   Delete a document by its ID.

   **Usage**:
   ```bash
   uv run doc-delete <document-id>
   ```

   **Arguments**:
   - `document-id` (required): Document ID to delete

   **Returns**: JSON with deletion confirmation

   **Example**:
   ```bash
   uv run doc-delete doc_abc123xyz
   ```

   ---

   ## Common Workflows

   ### Store and Tag Documents

   ```bash
   # Store architecture document
   uv run doc-push ./arch.md --name "System Architecture" --tags "architecture,design,current"

   # Store meeting notes
   uv run doc-push ./notes.md --name "Sprint Planning Notes" --tags "notes,sprint,planning"

   # Store API spec
   uv run doc-push ./api-spec.yaml --name "API Specification" --tags "api,spec,current"
   ```

   ### Find Relevant Documents

   ```bash
   # Find all current architecture documents
   uv run doc-query --tags "architecture,current"

   # Find documents by name
   uv run doc-query --name "sprint"

   # List all documents (up to 50)
   uv run doc-query
   ```

   ### Retrieve and Use Documents

   ```bash
   # Find and download
   DOC_ID=$(uv run doc-query --tags "api,current" | jq -r '.[0].document_id')
   uv run doc-pull $DOC_ID --output ./api-spec.yaml

   # Now you can read and use the file
   cat ./api-spec.yaml
   ```

   ### Clean Up Old Documents

   ```bash
   # Find old version
   OLD_DOC=$(uv run doc-query --tags "architecture,v1" | jq -r '.[0].document_id')

   # Delete it
   uv run doc-delete $OLD_DOC
   ```

   ---

   ## Tag Strategy

   **AND Logic**: When querying with multiple tags, documents must have ALL specified tags.

   **Suggested Tag Categories**:
   - **Type**: `architecture`, `spec`, `notes`, `config`, `data`
   - **Status**: `current`, `draft`, `archived`, `v1`, `v2`
   - **Domain**: `backend`, `frontend`, `database`, `api`, `ui`
   - **Project**: `mvp`, `phase2`, `experimental`

   **Example Tagging**:
   ```bash
   uv run doc-push design.md --tags "architecture,backend,current,mvp"
   ```

   ---

   ## Configuration

   Set environment variables to customize server connection:

   ```bash
   export DOCUMENT_SERVER_URL="http://localhost:8766"
   export DOCUMENT_SERVER_TIMEOUT="30"
   ```

   ---

   ## Output Format

   All commands return JSON for easy parsing:

   ```json
   {
     "document_id": "doc_abc123xyz",
     "name": "System Architecture",
     "original_filename": "architecture.md",
     "tags": ["architecture", "design"],
     "size_bytes": 25088,
     "uploaded_at": "2024-11-21T10:30:00Z"
   }
   ```

   Use `jq` for parsing:
   ```bash
   uv run doc-query --tags "design" | jq -r '.[].document_id'
   ```

   ---

   ## Prerequisites

   The document server must be running on localhost:8766 (or custom URL via ENV).

   Start server:
   ```bash
   cd document-server
   uv run src/main.py
   ```

   Or with Docker:
   ```bash
   docker-compose up -d
   ```
   ```

### Step 2: Test Skill Discovery (~15min)

1. **Verify skill structure**
   ```bash
   cd skills/document-sync
   ls -la
   # Should see: skill.json, SKILL.md, commands/

   # Test commands are executable
   cd commands
   ls -la doc-*
   # Should all be executable
   ```

2. **Validate JSON**
   ```bash
   cd skills/document-sync
   cat skill.json | jq .
   # Should parse without errors
   ```

3. **Test command discovery**
   ```bash
   # Claude Code should be able to see these commands
   # The commands directory contains UV scripts that Claude can invoke
   cd commands
   uv run doc-push --help
   uv run doc-query --help
   uv run doc-pull --help
   uv run doc-delete --help
   ```

### Step 3: Manual Testing with Claude Code (~60min)

Start a Claude Code session and test various scenarios:

#### Test 1: Basic Usage

**Prompt to Claude**:
```
I have a document sync skill installed. Please help me:
1. Upload the file "test.md" with tags "test,demo"
2. Query for all documents with tag "test"
3. Show me the results
```

**Expected**: Claude uses `doc-push` and `doc-query` commands correctly

---

#### Test 2: Workflow Integration

**Prompt to Claude**:
```
Create a new file called "architecture-notes.md" with some sample content about a web application architecture. Then use the document sync skill to:
1. Store it with tags "architecture,web,notes"
2. Query to verify it was stored
3. Download it to a new location to verify content
```

**Expected**: Claude creates file, pushes it, queries, and pulls successfully

---

#### Test 3: Search and Retrieval

**Prompt to Claude**:
```
I need to find all documents tagged with both "architecture" and "web". Use the document sync skill to search for them and show me what's available.
```

**Expected**: Claude understands AND logic and uses correct query

---

#### Test 4: Document Management

**Prompt to Claude**:
```
Using the document sync skill:
1. Store three different markdown files with different tags
2. Show me all stored documents
3. Find only the ones tagged "important"
4. Delete one of them
5. Verify it's gone
```

**Expected**: Claude performs complete workflow autonomously

---

#### Test 5: Error Handling

**Prompt to Claude**:
```
Try to download a document with ID "doc_nonexistent" using the document sync skill. What happens?
```

**Expected**: Claude handles error gracefully and reports to user

---

#### Test 6: Cross-Session Usage

**Session 1 Prompt**:
```
Create a file called "session1-data.md" and store it using document sync with tags "session1,data"
```

**Session 2 Prompt** (new Claude Code session):
```
Use document sync to find and retrieve the document from the previous session tagged "session1". Show me its contents.
```

**Expected**: Document persists across sessions

### Step 4: Create User Documentation (~45min)

1. **Create USER-GUIDE.md**

   ```markdown
   # Document Sync - User Guide

   ## Quick Start

   ### 1. Start the Document Server

   ```bash
   # Option A: Direct
   cd document-server
   uv run src/main.py

   # Option B: Docker
   docker-compose up -d
   ```

   ### 2. Use in Claude Code

   Simply ask Claude to use the document sync skill:

   ```
   "Store this file using document sync with tags architecture,design"
   ```

   Claude will automatically use the appropriate commands.

   ### 3. Manual Usage

   You can also use commands directly:

   ```bash
   cd skills/document-sync/commands
   uv run doc-push myfile.md --tags "important,docs"
   ```

   ## Example Prompts for Claude

   ### Storing Documents
   - "Store this architecture document with tags design,v2"
   - "Save all markdown files in this directory to document sync with tag 'backup'"
   - "Upload the API spec and tag it as api,current,production"

   ### Finding Documents
   - "Show me all documents tagged 'architecture'"
   - "Find documents from yesterday tagged 'notes'"
   - "List all available documents"

   ### Retrieving Documents
   - "Get the latest architecture document"
   - "Download all documents tagged 'important'"
   - "Retrieve the document named 'API Spec'"

   ### Managing Documents
   - "Delete old documents tagged 'draft'"
   - "Clean up documents older than last week"
   - "Update the tags on the architecture document"

   ## Best Practices

   ### Tagging Strategy

   Use consistent tag categories:
   - **Type**: architecture, spec, notes, config
   - **Status**: current, draft, archived
   - **Version**: v1, v2, v3
   - **Importance**: important, reference, temporary

   Example:
   ```bash
   uv run doc-push design.md --tags "architecture,current,v2,important"
   ```

   ### Organization

   - Tag documents immediately when storing
   - Use descriptive names
   - Review and clean up periodically
   - Use version tags to track iterations

   ### Search Tips

   - Remember: multiple tags use AND logic
   - Use name search for fuzzy matching
   - Combine name and tag filters
   - List all documents first to understand what's available

   ## Troubleshooting

   ### "Connection refused" error

   Server not running. Start it:
   ```bash
   docker-compose up -d
   ```

   ### "Document not found" error

   Document may have been deleted. Query to see what's available:
   ```bash
   uv run doc-query
   ```

   ### Commands not working

   Ensure you're in the right directory:
   ```bash
   cd skills/document-sync/commands
   ```

   ### Server URL issues

   Set custom URL:
   ```bash
   export DOCUMENT_SERVER_URL="http://localhost:8766"
   ```

   ## Advanced Usage

   ### Custom Server Port

   ```bash
   # Server side
   DOCUMENT_SERVER_PORT=9000 uv run src/main.py

   # Client side
   export DOCUMENT_SERVER_URL="http://localhost:9000"
   ```

   ### Parsing JSON Output

   All commands output JSON. Use jq:
   ```bash
   # Get all document IDs
   uv run doc-query | jq -r '.[].document_id'

   # Get documents uploaded today
   uv run doc-query | jq '[.[] | select(.uploaded_at | startswith("2024-11-21"))]'

   # Count documents
   uv run doc-query | jq 'length'
   ```

   ### Scripting

   Automate workflows:
   ```bash
   #!/bin/bash
   # Backup all markdown files

   for file in *.md; do
     uv run doc-push "$file" --tags "backup,$(date +%Y-%m-%d)"
   done
   ```
   ```

2. **Update main project README.md**

   Add section about skill usage and link to USER-GUIDE.md

### Step 5: Final Validation (~30min)

1. **Start clean environment**
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

2. **Run through complete user journey**

   Open Claude Code and have a real conversation:

   ```
   User: "I'm working on a project and want to use document sync. Can you help me store this README.md file with tags 'docs,readme,important'?"

   [Claude should use doc-push]

   User: "Now show me all documents"

   [Claude should use doc-query]

   User: "Great, can you retrieve that document and verify the content?"

   [Claude should use doc-pull and Read tools]

   User: "Perfect! Now delete it"

   [Claude should use doc-delete]
   ```

3. **Test edge cases**
   - Large files
   - Special characters in filenames
   - Unicode content
   - Empty tags
   - Many documents (50+)

4. **Verify documentation**
   - All links work
   - Examples are accurate
   - Commands match actual implementation

## Success Criteria ✅

- [ ] skill.json validates and contains correct metadata
- [ ] SKILL.md is comprehensive and clear
- [ ] Claude can discover and use all 4 commands
- [ ] Claude understands when to use document sync
- [ ] Claude correctly uses tag AND logic
- [ ] Claude handles errors gracefully
- [ ] Documents persist across Claude sessions
- [ ] USER-GUIDE.md is complete and helpful
- [ ] All example prompts work as documented
- [ ] Integration test scenarios pass in Claude Code

## Implementation Hints & Gotchas

### SKILL.md Best Practices

Claude reads this file to understand the skill. Make it:
- **Clear**: Explain what each command does
- **Example-rich**: Show concrete usage examples
- **Workflow-focused**: Show common patterns
- **Error-aware**: Mention what can go wrong

### JSON vs Human-Readable

Commands output JSON for machine parsing. Claude handles this well:
```bash
# Claude can parse this automatically
uv run doc-query --tags "design" | jq -r '.[0].document_id'
```

### Command Path

Claude invokes commands with `uv run` from the commands directory. Ensure paths are relative to that location.

### Server Dependency

Document clearly in SKILL.md that server must be running. Claude should be able to detect connection errors and inform the user.

### Tag AND Logic

Emphasize in documentation that multiple tags = AND logic. This is important for Claude to understand:
```markdown
**Important**: Multiple tags use AND logic - document must have ALL specified tags.
```

### Testing with Claude

Real conversations reveal issues docs might miss. Test:
- Ambiguous requests
- Multi-step workflows
- Error recovery
- Cross-session usage

## Common Issues

**Issue**: Claude doesn't use the skill
- **Solution**: Check SKILL.md explains when to use it clearly

**Issue**: Claude uses wrong command syntax
- **Solution**: Verify examples in SKILL.md match actual command signatures

**Issue**: Commands fail in Claude but work manually
- **Solution**: Check working directory and relative paths

**Issue**: Claude can't parse output
- **Solution**: Ensure JSON output is valid, no extra text

**Issue**: Server not running when Claude tries to use skill
- **Solution**: Add health check step to USER-GUIDE.md startup

## Dependencies Met

This is the final block! All components should now be working:
- ✅ Server foundation (Block 01)
- ✅ Storage and database (Block 02)
- ✅ CLI commands (Block 03)
- ✅ Integration and Docker (Block 04)
- ✅ Skill registration (Block 05)

## Estimated Time

**2-3 hours** including skill setup, Claude testing, documentation, and validation.

## Notes

- Real testing with Claude is critical - documentation alone isn't enough
- Keep SKILL.md updated as you learn what works
- User feedback will reveal missing use cases
- Cross-session testing validates persistence
- This is the moment it all comes together! 🎉

## Celebration Checklist 🎉

Once this block is complete:

- [ ] Claude can autonomously manage documents
- [ ] System works end-to-end
- [ ] All documentation is accurate
- [ ] MVP is production-ready
- [ ] You have a working document sync system!

**Congratulations! You've built a complete document management system for AI coding sessions.**
