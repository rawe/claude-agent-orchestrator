# Deferred Features

Features from original plan not implemented in this iteration.

## Monaco Editor for MCP JSON
- Original: `@monaco-editor/react` with syntax highlighting
- Current: Simple textarea with JSON validation
- Add later if users need better editing experience

## MCP Templates (5 remaining)
- Implemented: playwright, brave-search
- Deferred: github, filesystem, postgres, sqlite, slack
- To add: edit `src/utils/mcpTemplates.ts`

## CLI Local Fallback
- Original: `--local` flag for file-based fallback
- Current: API-only, clean error on unavailable
- Reason: Planning to remove file-based persistence

## Authentication/Authorization
- Not in scope for MVP

## Agent Versioning
- Not in scope

## Bulk Operations
- Not in scope

## Import/Export
- Not in scope

## Audit Logging
- Not in scope

## Rate Limiting
- Not in scope

## Caching Layer
- Not in scope
