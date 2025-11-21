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

---

## Phase 1: Setup and Shared Library

### 1.1 Directory Structure
- [ ] Create directory `skills/document-sync/commands/lib/`
- [ ] Verify parent directory `skills/document-sync/commands/` exists

### 1.2 Library Foundation
- [ ] Create `skills/document-sync/commands/lib/__init__.py`
  - Export main classes: `DocumentClient`, `Config`
  ```python
  from .client import DocumentClient
  from .config import Config

  __all__ = ["DocumentClient", "Config"]
  ```

### 1.3 Configuration Module
- [ ] Create `skills/document-sync/commands/lib/config.py`
- [ ] Implement `Config` class with defaults:
  - `DEFAULT_HOST = "localhost"`
  - `DEFAULT_PORT = 8080`
  - `DEFAULT_SCHEME = "http"`
- [ ] Implement environment variable loading:
  - `DOC_SYNC_HOST`
  - `DOC_SYNC_PORT`
  - `DOC_SYNC_SCHEME`
- [ ] Add `base_url` property that constructs full URL
- [ ] Test configuration with different environment variables

### 1.4 Client Module
- [ ] Create `skills/document-sync/commands/lib/client.py`
- [ ] Import required modules: `httpx`, `pathlib`, `typing`
- [ ] Implement `DocumentClient` class with `__init__(config: Config)`
- [ ] Implement `push_document(file_path, name, tags, description)` method:
  - Read file content from `file_path`
  - Detect content type
  - Prepare multipart form data with file, metadata
  - POST to `/documents/upload`
  - Return JSON response or raise exception
- [ ] Implement `query_documents(name=None, tags=None, limit=None)` method:
  - Build query parameters
  - Handle tags as list (AND logic)
  - GET from `/documents/search`
  - Return JSON array
- [ ] Implement `pull_document(document_id)` method:
  - GET from `/documents/{document_id}/download`
  - Return bytes content and filename from response
  - Handle 404 errors gracefully
- [ ] Implement `delete_document(document_id)` method:
  - DELETE to `/documents/{document_id}`
  - Return JSON confirmation
  - Handle errors appropriately

### 1.5 Optional Document Model
- [ ] Create `skills/document-sync/commands/lib/document.py` (if needed)
- [ ] Define `Document` dataclass or Pydantic model for type safety

### 1.6 Library Testing
- [ ] Create test script to verify library in isolation
- [ ] Test each method with mock server or actual server
- [ ] Verify error handling for network failures
- [ ] Verify error handling for HTTP errors (400, 404, 500)

---

## Phase 2: doc-push Command

### 2.1 Create UV Script
- [ ] Create file `skills/document-sync/commands/doc-push`
- [ ] Add PEP 723 header:
  ```python
  #!/usr/bin/env -S uv run
  # /// script
  # requires-python = ">=3.11"
  # dependencies = [
  #     "httpx",
  #     "typer",
  # ]
  # ///
  ```
- [ ] Make file executable: `chmod +x skills/document-sync/commands/doc-push`

### 2.2 Implement Command
- [ ] Import required modules: `typer`, `pathlib`, `json`, `sys`
- [ ] Import from lib: `DocumentClient`, `Config`
- [ ] Create Typer app instance
- [ ] Implement main command function with arguments:
  - `file_path: str` (positional, required)
  - `--name: str` (optional, defaults to filename)
  - `--tags: str` (optional, comma-separated)
  - `--description: str` (optional)
- [ ] Parse tags from comma-separated string to list
- [ ] Validate file exists using `pathlib.Path`
- [ ] Create Config and DocumentClient instances
- [ ] Call `client.push_document()` with parameters
- [ ] Output JSON response to stdout
- [ ] Handle errors and output to stderr with exit code 1

### 2.3 Testing
- [ ] Test pushing a text file
- [ ] Test pushing with custom name, tags, description
- [ ] Test pushing non-existent file (should fail gracefully)
- [ ] Test pushing to non-running server (should fail gracefully)
- [ ] Verify JSON output format

---

## Phase 3: doc-query Command

### 3.1 Create UV Script
- [ ] Create file `skills/document-sync/commands/doc-query`
- [ ] Add PEP 723 header (same as doc-push)
- [ ] Make file executable

### 3.2 Implement Command
- [ ] Import required modules
- [ ] Import from lib
- [ ] Create Typer app instance
- [ ] Implement main command function with arguments:
  - `--name: str` (optional, filter by name pattern)
  - `--tags: str` (optional, comma-separated, AND logic)
  - `--limit: int` (optional, max results)
- [ ] Parse tags from comma-separated string to list
- [ ] Create Config and DocumentClient instances
- [ ] Call `client.query_documents()` with parameters
- [ ] Output JSON array to stdout
- [ ] Handle errors appropriately

### 3.3 Testing
- [ ] Test query with no filters (list all)
- [ ] Test query by name pattern
- [ ] Test query by single tag
- [ ] Test query by multiple tags (verify AND logic)
- [ ] Test query with limit
- [ ] Test combined filters (name + tags + limit)
- [ ] Verify empty results return `[]`

---

## Phase 4: doc-pull Command

### 4.1 Create UV Script
- [ ] Create file `skills/document-sync/commands/doc-pull`
- [ ] Add PEP 723 header
- [ ] Make file executable

### 4.2 Implement Command
- [ ] Import required modules including `pathlib`
- [ ] Import from lib
- [ ] Create Typer app instance
- [ ] Implement main command function with arguments:
  - `document_id: str` (positional, required)
  - `--output: str` (optional, output file path)
- [ ] Create Config and DocumentClient instances
- [ ] Call `client.pull_document(document_id)`
- [ ] Extract content bytes and filename from response
- [ ] Determine output path:
  - Use `--output` if provided
  - Otherwise use original filename from response
- [ ] Write bytes to file using `pathlib.Path.write_bytes()`
- [ ] Output success message with file path to stdout
- [ ] Handle 404 errors (document not found)
- [ ] Handle file write errors

### 4.3 Testing
- [ ] Test pulling existing document (default filename)
- [ ] Test pulling with custom output path
- [ ] Test pulling non-existent document ID (should fail gracefully)
- [ ] Test pulling to existing file (should overwrite or warn)
- [ ] Verify file integrity (compare checksums if available)
- [ ] Test pulling binary files (images, PDFs)

---

## Phase 5: doc-delete Command

### 5.1 Create UV Script
- [ ] Create file `skills/document-sync/commands/doc-delete`
- [ ] Add PEP 723 header
- [ ] Make file executable

### 5.2 Implement Command
- [ ] Import required modules
- [ ] Import from lib
- [ ] Create Typer app instance
- [ ] Implement main command function with arguments:
  - `document_id: str` (positional, required)
- [ ] Create Config and DocumentClient instances
- [ ] Call `client.delete_document(document_id)`
- [ ] Output JSON confirmation to stdout
- [ ] Handle 404 errors (document not found)
- [ ] Handle errors appropriately

### 5.3 Testing
- [ ] Test deleting existing document
- [ ] Test deleting non-existent document (should fail gracefully)
- [ ] Verify document is actually deleted (query should not find it)
- [ ] Test deleting already deleted document (should fail)
- [ ] Verify JSON output format

---

## Phase 6: End-to-End Testing

### 6.1 Complete Workflow Test
- [ ] Push a document with tags and description
- [ ] Query to verify document exists
- [ ] Pull the document to verify content integrity
- [ ] Delete the document
- [ ] Query again to verify deletion

### 6.2 Environment Variable Testing
- [ ] Test with `DOC_SYNC_HOST` set to different host
- [ ] Test with `DOC_SYNC_PORT` set to different port
- [ ] Test with `DOC_SYNC_SCHEME` set to "https"
- [ ] Test with no environment variables (should use defaults)

### 6.3 Error Scenario Testing
- [ ] Test all commands with server not running
- [ ] Test invalid document IDs
- [ ] Test invalid file paths
- [ ] Test malformed tags
- [ ] Verify all errors output to stderr
- [ ] Verify appropriate exit codes (0 for success, 1 for errors)

### 6.4 Tag AND Logic Verification
- [ ] Push documents with various tag combinations
- [ ] Query with single tag, verify only matching documents
- [ ] Query with multiple tags, verify only documents with ALL tags
- [ ] Query with non-existent tag combination, verify empty results

### 6.5 File Integrity Testing
- [ ] Push text file, pull, compare content
- [ ] Push binary file (image), pull, compare checksums
- [ ] Push large file (>1MB), verify complete transfer
- [ ] Push file with special characters in name, verify handling

---

## Success Criteria

- [ ] All four CLI commands (doc-push, doc-pull, doc-query, doc-delete) are executable
- [ ] All commands use UV with PEP 723 headers
- [ ] All commands use Typer for argument parsing
- [ ] Shared library (`lib/`) provides reusable client functionality
- [ ] Configuration supports environment variables (DOC_SYNC_HOST, DOC_SYNC_PORT, DOC_SYNC_SCHEME)
- [ ] doc-push successfully uploads documents with metadata
- [ ] doc-query supports filtering by name, tags (AND logic), and limit
- [ ] doc-pull downloads documents and saves to file system
- [ ] doc-delete removes documents from server
- [ ] All commands output valid JSON (except doc-pull which outputs file)
- [ ] Error handling is robust (network errors, HTTP errors, file errors)
- [ ] End-to-end workflow (push → query → pull → delete) works correctly
- [ ] File integrity is maintained (uploaded content matches downloaded content)
- [ ] All commands handle edge cases gracefully

---

## Implementation Notes

### UV Script Header Template
```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx",
#     "typer",
# ]
# ///
```

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
