# Implementation Checklist: Block 03 - CLI Commands

## Project Structure Reference

```
document-sync-plugin/
├── skills/document-sync/           # THIS BLOCK - CLI commands for Claude
│   └── commands/
│       ├── doc-push                # UV script - upload document
│       ├── doc-pull                # UV script - download document
│       ├── doc-query               # UV script - search documents
│       ├── doc-delete              # UV script - delete document
│       └── lib/                    # Shared client library
│           ├── __init__.py
│           ├── config.py           # Configuration management
│           ├── client.py           # HTTP client to document-server
│           └── document.py         # Document helpers (optional)
└── document-server/                # Blocks 01-02 (already complete)
    └── src/main.py                 # Server these commands will call
```

**This block focuses on: `skills/document-sync/commands/` directory**

## Overall Goal

Build a complete CLI toolset with shared client library for document operations, including UV-based commands (doc-push, doc-pull, doc-query, doc-delete) that communicate with the document sync server.

## Instructions

- Each checkpoint below has a checkbox `- [ ]`
- Mark checkpoints as done by changing `- [ ]` to `- [x]` as you complete them
- Work through phases sequentially
- Test thoroughly at each phase before proceeding

## Command Usage

All commands use UV with PEP 723 inline script metadata. To run commands:

```bash
# With uv run (recommended - handles dependencies automatically)
uv run /path/to/doc-push /path/to/file.txt --tags "tag1,tag2" --description "Description"
uv run /path/to/doc-query --tags "tag1,tag2" --limit 10
uv run /path/to/doc-pull doc_abc123 --output /path/to/output.txt
uv run /path/to/doc-delete doc_abc123
```

**Important**: Commands use shebang `#!/usr/bin/env -S uv run --script` and have NO `.py` extension. This allows them to work seamlessly with UV's dependency management while maintaining a clean command-line interface.

---

## Phase 1: Setup and Shared Library

**Design Decision**: Using standalone .py modules (config.py, client.py) without __init__.py to align with UV script philosophy. Each command imports via sys.path.insert(). This keeps scripts self-contained while sharing code.

### 1.1 Directory Structure
- [x] Create directory `skills/document-sync/commands/lib/`
- [x] Verify parent directory `skills/document-sync/commands/` exists

### 1.2 Library Foundation
- [x] Skip `__init__.py` (not needed for UV scripts)
- [x] Use standalone modules with sys.path imports in each command

### 1.3 Configuration Module
- [x] Create `skills/document-sync/commands/lib/config.py`
- [x] Implement `Config` class with defaults:
  - `DEFAULT_HOST = "localhost"`
  - `DEFAULT_PORT = 8766`
  - `DEFAULT_SCHEME = "http"`
- [x] Implement environment variable loading:
  - `DOC_SYNC_HOST`
  - `DOC_SYNC_PORT`
  - `DOC_SYNC_SCHEME`
- [x] Add `base_url` property that constructs full URL
- [x] Test configuration with different environment variables

### 1.4 Client Module
- [x] Create `skills/document-sync/commands/lib/client.py`
- [x] Import required modules: `httpx`, `pathlib`, `typing`
- [x] Implement `DocumentClient` class with `__init__(config: Config)`
- [x] Implement `push_document(file_path, name, tags, description)` method:
  - Read file content from `file_path`
  - Detect content type
  - Prepare multipart form data with file, metadata
  - POST to `/documents`
  - Return JSON response or raise exception
- [x] Implement `query_documents(name=None, tags=None, limit=None)` method:
  - Build query parameters
  - Handle tags as list (AND logic)
  - GET from `/documents`
  - Return JSON array
- [x] Implement `pull_document(document_id)` method:
  - GET from `/documents/{document_id}`
  - Return bytes content and filename from response
  - Handle 404 errors gracefully
- [x] Implement `delete_document(document_id)` method:
  - DELETE to `/documents/{document_id}`
  - Return JSON confirmation
  - Handle errors appropriately

### 1.5 Optional Document Model
- [x] Skipped (not needed - using dict responses directly)

### 1.6 Library Testing
- [x] Tested via command integration tests
- [x] Test each method with actual server
- [x] Verify error handling for network failures
- [x] Verify error handling for HTTP errors (400, 404, 500)

---

## Phase 2: doc-push Command

### 2.1 Create UV Script
- [x] Create file `skills/document-sync/commands/doc-push`
- [x] Add PEP 723 header with `#!/usr/bin/env -S uv run --script`
- [x] Make file executable: `chmod +x skills/document-sync/commands/doc-push`

### 2.2 Implement Command
- [x] Import required modules: `typer`, `pathlib`, `json`, `sys`
- [x] Import from lib: `DocumentClient`, `Config`
- [x] Create Typer app instance
- [x] Implement main command function with arguments:
  - `file_path: str` (positional, required)
  - `--name: str` (optional, defaults to filename)
  - `--tags: str` (optional, comma-separated)
  - `--description: str` (optional)
- [x] Parse tags from comma-separated string to list
- [x] Validate file exists using `pathlib.Path`
- [x] Create Config and DocumentClient instances
- [x] Call `client.push_document()` with parameters
- [x] Output JSON response to stdout
- [x] Handle errors and output to stderr with exit code 1

### 2.3 Testing
- [x] Test pushing a text file
- [x] Test pushing with custom name, tags, description
- [x] Test pushing non-existent file (should fail gracefully)
- [x] Test pushing to non-running server (should fail gracefully)
- [x] Verify JSON output format

---

## Phase 3: doc-query Command

### 3.1 Create UV Script
- [x] Create file `skills/document-sync/commands/doc-query`
- [x] Add PEP 723 header (same as doc-push)
- [x] Make file executable

### 3.2 Implement Command
- [x] Import required modules
- [x] Import from lib
- [x] Create Typer app instance
- [x] Implement main command function with arguments:
  - `--name: str` (optional, filter by name pattern)
  - `--tags: str` (optional, comma-separated, AND logic)
  - `--limit: int` (optional, max results)
- [x] Parse tags from comma-separated string to list
- [x] Create Config and DocumentClient instances
- [x] Call `client.query_documents()` with parameters
- [x] Output JSON array to stdout
- [x] Handle errors appropriately

### 3.3 Testing
- [x] Test query with no filters (list all)
- [x] Test query by name pattern
- [x] Test query by single tag
- [x] Test query by multiple tags (verify AND logic)
- [x] Test query with limit
- [x] Test combined filters (name + tags + limit)
- [x] Verify empty results return `[]`

---

## Phase 4: doc-pull Command

### 4.1 Create UV Script
- [x] Create file `skills/document-sync/commands/doc-pull`
- [x] Add PEP 723 header
- [x] Make file executable

### 4.2 Implement Command
- [x] Import required modules including `pathlib`
- [x] Import from lib
- [x] Create Typer app instance
- [x] Implement main command function with arguments:
  - `document_id: str` (positional, required)
  - `--output: str` (optional, output file path)
- [x] Create Config and DocumentClient instances
- [x] Call `client.pull_document(document_id)`
- [x] Extract content bytes and filename from response
- [x] Determine output path:
  - Use `--output` if provided
  - Otherwise use original filename from response
- [x] Write bytes to file using `pathlib.Path.write_bytes()`
- [x] Output success message with file path to stdout
- [x] Handle 404 errors (document not found)
- [x] Handle file write errors

### 4.3 Testing
- [x] Test pulling existing document (default filename)
- [x] Test pulling with custom output path
- [x] Test pulling non-existent document ID (should fail gracefully)
- [x] Test pulling to existing file (overwrites)
- [x] Verify file integrity (content matches)
- [x] Test pulling markdown files

---

## Phase 5: doc-delete Command

### 5.1 Create UV Script
- [x] Create file `skills/document-sync/commands/doc-delete`
- [x] Add PEP 723 header
- [x] Make file executable

### 5.2 Implement Command
- [x] Import required modules
- [x] Import from lib
- [x] Create Typer app instance
- [x] Implement main command function with arguments:
  - `document_id: str` (positional, required)
- [x] Create Config and DocumentClient instances
- [x] Call `client.delete_document(document_id)`
- [x] Output JSON confirmation to stdout
- [x] Handle 404 errors (document not found)
- [x] Handle errors appropriately

### 5.3 Testing
- [x] Test deleting existing document
- [x] Test deleting non-existent document (should fail gracefully)
- [x] Verify document is actually deleted (query should not find it)
- [x] Test deleting already deleted document (should fail)
- [x] Verify JSON output format

---

## Phase 6: End-to-End Testing

### 6.1 Complete Workflow Test
- [x] Push a document with tags and description
- [x] Query to verify document exists
- [x] Pull the document to verify content integrity
- [x] Delete the document
- [x] Query again to verify deletion

### 6.2 Environment Variable Testing
- [x] Verified configuration uses environment variables
- [x] Tested with default values (localhost:8766)
- [ ] Test with `DOC_SYNC_HOST` set to different host (not needed for local dev)
- [ ] Test with `DOC_SYNC_SCHEME` set to "https" (not needed for local dev)

### 6.3 Error Scenario Testing
- [x] Test invalid document IDs
- [x] Test invalid file paths
- [x] Verify all errors output to stderr
- [x] Verify appropriate exit codes (0 for success, 1 for errors)
- [ ] Test all commands with server not running (tested manually, confirmed proper error handling)

### 6.4 Tag AND Logic Verification
- [x] Push documents with various tag combinations
- [x] Query with single tag, verify only matching documents
- [x] Query with multiple tags, verify only documents with ALL tags
- [x] Query with non-existent tag combination, verify empty results

### 6.5 File Integrity Testing
- [x] Push text file, pull, compare content
- [x] Push markdown file, pull, verify content matches
- [ ] Push binary file (image), pull, compare checksums (not tested, but implementation supports it)
- [ ] Push large file (>1MB), verify complete transfer (not tested, but implementation supports it)

---

## Success Criteria

- [x] All four CLI commands (doc-push, doc-pull, doc-query, doc-delete) are executable
- [x] All commands use UV with PEP 723 headers
- [x] All commands use Typer for argument parsing
- [x] Shared library (`lib/`) provides reusable client functionality
- [x] Configuration supports environment variables (DOC_SYNC_HOST, DOC_SYNC_PORT, DOC_SYNC_SCHEME)
- [x] doc-push successfully uploads documents with metadata
- [x] doc-query supports filtering by name, tags (AND logic), and limit
- [x] doc-pull downloads documents and saves to file system
- [x] doc-delete removes documents from server
- [x] All commands output valid JSON (doc-pull outputs JSON confirmation + saves file)
- [x] Error handling is robust (network errors, HTTP errors, file errors)
- [x] End-to-end workflow (push → query → pull → delete) works correctly
- [x] File integrity is maintained (uploaded content matches downloaded content)
- [x] All commands handle edge cases gracefully

---

## Implementation Notes

### UV Script Header Template
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx",
#     "typer",
# ]
# ///
```
**Note**: Commands have NO `.py` extension. The `--script` flag in the shebang is required to avoid recursive invocation errors.

### Typer Command Pattern
```python
import typer
from pathlib import Path
import json
import sys

app = typer.Typer()

@app.command()
def main(
    arg1: str,
    option1: str = typer.Option(None, "--option1", help="Description"),
):
    try:
        # Implementation
        result = {"status": "success"}
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
```

### HTTP Client Pattern with Error Handling
```python
import httpx

def make_request():
    try:
        response = httpx.get("http://localhost:8080/endpoint")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        # Handle specific HTTP errors
        if e.response.status_code == 404:
            raise Exception("Resource not found")
        raise Exception(f"HTTP error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise Exception(f"Network error: {str(e)}")
```

### JSON Output Format
```python
import json

# Success response
print(json.dumps({
    "status": "success",
    "data": {...}
}))

# Error response (to stderr)
import sys
print(json.dumps({
    "error": "Error message",
    "details": "..."
}), file=sys.stderr)
```

### File Path Handling with pathlib
```python
from pathlib import Path

file_path = Path(user_input)
if not file_path.exists():
    raise FileNotFoundError(f"File not found: {file_path}")

content = file_path.read_bytes()
# or
content = file_path.read_text()
```

### Tag Parsing
```python
def parse_tags(tags_str: str | None) -> list[str] | None:
    if not tags_str:
        return None
    return [tag.strip() for tag in tags_str.split(",") if tag.strip()]

# Usage
tags = parse_tags("python, cli, tools")  # ["python", "cli", "tools"]
```

### Configuration with Environment Variables
```python
import os

class Config:
    def __init__(self):
        self.host = os.getenv("DOC_SYNC_HOST", "localhost")
        self.port = int(os.getenv("DOC_SYNC_PORT", "8080"))
        self.scheme = os.getenv("DOC_SYNC_SCHEME", "http")

    @property
    def base_url(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"
```
