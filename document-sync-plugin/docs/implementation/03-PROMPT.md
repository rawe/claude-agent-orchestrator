# Block 03: CLI Commands - Implementation Prompt

## Prompt for Claude Code

```
I want to continue implementing the Document Sync Plugin described in document-sync-plugin/docs/goal.md.

Please read:
1. document-sync-plugin/docs/goal.md - for the overall vision and architecture
2. document-sync-plugin/docs/implementation/03-IMPLEMENTATION-CHECKLIST.md - for the detailed implementation steps

Then implement Block 03 (CLI Commands) following the checklist exactly. Work through each phase sequentially, checking off items as you complete them. Use the TodoWrite tool to track your progress through the phases.

Important:
- Blocks 01 and 02 (Server Foundation and Storage/Database) must be completed first
- The document server must be running for testing
- Follow the checklist items in order
- All commands must be UV scripts with PEP 723 headers
- All commands must output valid JSON
- Test each command individually before integration testing
- Verify tag AND logic works correctly in doc-query
- Mark checkboxes with [x] in the checklist file as you complete each item
- Ask me if you encounter any blockers or need clarification
- Stop after completing all success criteria for Block 03
```

## What This Block Accomplishes

By the end of this block, you will have:
- Shared client library (lib/config.py and lib/client.py)
- doc-push command for uploading documents
- doc-query command for searching documents
- doc-pull command for downloading documents
- doc-delete command for removing documents
- Environment-based configuration (DOC_SYNC_HOST, DOC_SYNC_PORT, DOC_SYNC_SCHEME)
- Comprehensive error handling
- End-to-end workflow validation

## Prerequisites

Before starting this block:
- Block 01 must be complete (FastAPI server working)
- Block 02 must be complete (Storage and Database working)
- Document server must be running on port 8766
- Test with: `curl http://localhost:8766/docs`

## Testing Tips

- Start the document server before testing commands
- Test each command in isolation first
- Use the test-data directory for test files
- Verify JSON output format for all commands
- Test error scenarios (server down, invalid IDs, etc.)

## Next Steps After Completion

Once Block 03 is complete and all tests pass, proceed to:
- **Block 04**: Integration Testing & Docker setup
