# Implementation Block 03: CLI Commands

## Goal
Build all UV-based command-line tools (doc-push, doc-pull, doc-query, doc-delete) and the shared client library. Enable command-line interaction with the document server.

## Benefit
🎯 **Complete CLI Workflow** - Users (and Claude) can push, query, pull, and delete documents from the terminal using simple commands. The system becomes usable end-to-end.

## MVP Architecture Reference

**Document**: [`architecture-mvp.md`](../architecture-mvp.md)

**Relevant Sections**:
- `Skill Commands (UV Scripts)` (lines 47-137)
- `Command Script Template (UV Pattern)` (lines 140-186)
- `lib/config.py - Configuration Management` (lines 190-216)
- `lib/client.py - HTTP Client` (lines 224-299)

## What Gets Built

### 1. Directory Structure
```
skills/
└── document-sync/
    ├── skill.json
    ├── SKILL.md
    └── commands/
        ├── doc-push         # UV script
        ├── doc-pull         # UV script
        ├── doc-query        # UV script
        ├── doc-delete       # UV script
        └── lib/
            ├── __init__.py
            ├── config.py    # Config loading
            ├── client.py    # HTTP client
            └── document.py  # Helper utilities
```

### 2. Shared Library Components

**lib/config.py**
- Centralized defaults (server URL, timeout)
- ENV variable loading with fallbacks
- Config dataclass

**lib/client.py**
- DocumentClient class
- Methods: push_document, pull_document, query_documents, delete_document
- HTTP error handling
- Timeout management

**lib/document.py** (optional)
- Helper functions for formatting output
- Utility functions for file handling

### 3. UV Command Scripts

All commands follow the UV inline script pattern:
- Shebang: `#!/usr/bin/env -S uv run --script`
- Inline dependencies in PEP 723 format
- Typer CLI framework
- JSON output only (MVP)

## Session Flow

### Step 1: Create Shared Library (~60min)

1. **Create directory structure**
   ```bash
   mkdir -p skills/document-sync/commands/lib
   cd skills/document-sync
   ```

2. **Create lib/__init__.py**
   - Empty file (makes it a package)

3. **Create lib/config.py**
   ```python
   from dataclasses import dataclass
   import os

   DEFAULT_SERVER_URL = "http://127.0.0.1:8766"
   DEFAULT_TIMEOUT_SECONDS = 30

   @dataclass
   class Config:
       server_url: str
       timeout_seconds: int

   def load_config() -> Config:
       return Config(
           server_url=os.getenv("DOCUMENT_SERVER_URL", DEFAULT_SERVER_URL),
           timeout_seconds=int(os.getenv("DOCUMENT_SERVER_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
       )
   ```

4. **Create lib/client.py**
   - Import httpx, pathlib, typing, json
   - Define DocumentClient class
   - Implement 4 methods (push, pull, query, delete)
   - Each method makes HTTP request and returns dict
   - Handle httpx.HTTPStatusError

5. **Test library in isolation**
   ```bash
   # Start server first
   cd ../../document-server
   uv run src/main.py &

   # Test client
   cd ../skills/document-sync
   python3 -c "
   from lib.config import load_config
   from lib.client import DocumentClient
   config = load_config()
   client = DocumentClient(config.server_url, config.timeout_seconds)
   print('Config loaded:', config)
   "
   ```

### Step 2: Build doc-push Command (~30min)

1. **Create commands/doc-push**
   - Add shebang and PEP 723 header
   - Dependencies: typer, httpx
   - Import from lib.config and lib.client
   - Define typer.Typer() app
   - Create push() command with arguments
   - Read file, call client.push_document()
   - Print JSON response
   - Add error handling

2. **Make executable**
   ```bash
   chmod +x commands/doc-push
   ```

3. **Test**
   ```bash
   cd commands
   echo "test document" > test.txt
   uv run doc-push test.txt --name "Test Doc" --tags "test,demo"
   # Should output JSON with document_id
   ```

### Step 3: Build doc-query Command (~20min)

1. **Create commands/doc-query**
   - Similar structure to doc-push
   - Optional arguments: --name, --tags, --limit
   - Call client.query_documents()
   - Print JSON array

2. **Test**
   ```bash
   # Query all
   uv run doc-query

   # Query by tag
   uv run doc-query --tags "test"

   # Query by name
   uv run doc-query --name "Test"

   # AND logic
   uv run doc-query --tags "test,demo"
   ```

### Step 4: Build doc-pull Command (~30min)

1. **Create commands/doc-pull**
   - Required: document_id argument
   - Optional: --output path (defaults to original filename)
   - Call client.pull_document(document_id, output_path)
   - Handle file already exists (fail or overwrite)
   - Print JSON confirmation

2. **Test**
   ```bash
   # Get document ID from previous push
   DOC_ID=$(uv run doc-query | jq -r '.[0].document_id')

   # Pull with default filename
   uv run doc-pull $DOC_ID

   # Pull with custom output
   uv run doc-pull $DOC_ID --output custom.txt

   # Verify content matches
   diff test.txt custom.txt
   ```

### Step 5: Build doc-delete Command (~20min)

1. **Create commands/doc-delete**
   - Required: document_id argument
   - Call client.delete_document()
   - Print JSON confirmation

2. **Test**
   ```bash
   # Delete document
   uv run doc-delete $DOC_ID

   # Verify it's gone
   uv run doc-query
   # Should return empty array

   # Try to delete again (should get 404)
   uv run doc-delete $DOC_ID
   ```

### Step 6: End-to-End Workflow Test (~30min)

Test the complete workflow as a user would:

```bash
cd skills/document-sync/commands

# 1. Push a document
echo "MVP Architecture" > architecture.md
uv run doc-push architecture.md \
  --name "Document Sync MVP" \
  --tags "architecture,mvp,design" \
  --description "MVP architecture document"

# Save the document ID
DOC_ID=$(uv run doc-query --name "MVP" | jq -r '.[0].document_id')
echo "Document ID: $DOC_ID"

# 2. Push another document
echo "Implementation plan" > plan.md
uv run doc-push plan.md \
  --name "Implementation Plan" \
  --tags "plan,mvp"

# 3. Query all documents
uv run doc-query | jq

# 4. Query by single tag
uv run doc-query --tags "mvp" | jq

# 5. Query by multiple tags (AND logic)
uv run doc-query --tags "architecture,mvp" | jq
# Should only return first document

# 6. Query by name
uv run doc-query --name "plan" | jq

# 7. Pull a document
uv run doc-pull $DOC_ID --output retrieved.md
cat retrieved.md

# 8. Delete a document
uv run doc-delete $DOC_ID

# 9. Verify deletion
uv run doc-query --name "MVP" | jq
# Should return empty array

# 10. Test error handling
uv run doc-pull doc_nonexistent
# Should show error message

uv run doc-delete doc_nonexistent
# Should show error message
```

### Step 7: Test Environment Variables (~15min)

```bash
# Test custom server URL
DOCUMENT_SERVER_URL=http://localhost:9999 uv run doc-query
# Should fail to connect

# Test custom timeout
DOCUMENT_SERVER_TIMEOUT=1 uv run doc-query
# Should timeout if server is slow

# Test with correct URL
DOCUMENT_SERVER_URL=http://127.0.0.1:8766 uv run doc-query
# Should work
```

## Success Criteria ✅

- [ ] All 4 commands are executable
- [ ] `uv run doc-push` uploads documents successfully
- [ ] `uv run doc-query` returns JSON array
- [ ] `uv run doc-pull` downloads documents correctly
- [ ] `uv run doc-delete` removes documents
- [ ] JSON output is valid (pipes to jq)
- [ ] ENV variables override defaults
- [ ] Error messages are clear (404, network errors)
- [ ] Complete workflow (push→query→pull→delete) works
- [ ] Tag AND logic works in queries
- [ ] File content integrity maintained (push→pull→diff)

## Implementation Hints & Gotchas

### UV Script Header Template
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.9.0",
#     "httpx>=0.25.0",
# ]
# ///
```

### Typer Command Pattern
```python
import typer
from pathlib import Path

app = typer.Typer()

@app.command()
def push(
    file_path: Path,
    name: str = typer.Option(None, help="Document name"),
    tags: str = typer.Option("", help="Comma-separated tags"),
):
    """Push a document to the server"""
    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(1)

    # Your logic here

if __name__ == "__main__":
    app()
```

### HTTP Client Pattern
```python
import httpx

class DocumentClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout

    def push_document(self, file_path, name, tags, description):
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f)}
                data = {"name": name, "tags": tags, "description": description}

                response = httpx.post(
                    f"{self.base_url}/documents",
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": str(e), "status_code": e.response.status_code}
        except Exception as e:
            return {"error": str(e)}
```

### JSON Output
Always print valid JSON for machine readability:
```python
import json
result = client.push_document(...)
print(json.dumps(result, indent=2))
```

### Error Handling
Show clear errors but keep JSON format:
```python
try:
    result = client.delete_document(document_id)
    if "error" in result:
        typer.echo(json.dumps(result, indent=2), err=True)
        raise typer.Exit(1)
    print(json.dumps(result, indent=2))
except Exception as e:
    error = {"error": str(e), "command": "doc-delete"}
    typer.echo(json.dumps(error, indent=2), err=True)
    raise typer.Exit(1)
```

### File Path Handling
Use pathlib for cross-platform compatibility:
```python
from pathlib import Path

file_path = Path(file_path)
if not file_path.exists():
    raise typer.Exit(1)

output_path = Path(output or "default.txt")
output_path.write_bytes(content)
```

### Tag Parsing
Split and clean tags:
```python
tags_list = [t.strip() for t in tags.split(",") if t.strip()]
```

## Common Issues

**Issue**: Import errors from lib/
- **Solution**: Run from commands/ directory, or adjust PYTHONPATH

**Issue**: UV can't find dependencies
- **Solution**: Check PEP 723 header format, ensure dependencies list is correct

**Issue**: httpx timeout errors
- **Solution**: Increase DOCUMENT_SERVER_TIMEOUT or check server is running

**Issue**: JSON parsing errors with jq
- **Solution**: Ensure all print statements output valid JSON, no extra debug text

**Issue**: File not found when pulling
- **Solution**: Check output path handling, ensure directory exists

## Dependencies for Next Block
- ✅ All 4 CLI commands working
- ✅ Shared client library functional
- ✅ End-to-end workflow tested
- ✅ Error handling in place

## Estimated Time
**3-4 hours** including library, all commands, testing, and debugging.

## Notes
- Test each command immediately after creating it
- Keep commands simple - all logic in client library
- JSON-only output makes piping to jq easy
- UV inline scripts are self-contained (great for distribution)
- Error messages should be JSON formatted for consistency
