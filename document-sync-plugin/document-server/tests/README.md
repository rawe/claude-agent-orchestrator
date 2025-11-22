# Tests

## End-to-End Test

Tests all API endpoints (upload, query, download, delete).

**Requirements**: Server must be running on `http://localhost:8766`

**Run**:
```bash
# From document-server/ directory
./tests/e2e.sh
```

**What it tests**:
- Document upload with tags
- Query by filename and tags (including AND logic)
- Document download
- Document deletion
- Path traversal protection
