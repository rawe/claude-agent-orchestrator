# Document Sync Integration Test Scenarios

## Basic CRUD Operations

### TC-01: Upload Document
- Upload a text file
- Verify document ID returned
- Verify content matches

### TC-02: Query Documents
- Upload multiple documents
- Query all documents
- Verify count and metadata

### TC-03: Get Document Metadata
- Upload a document
- Get metadata by ID
- Verify metadata fields (id, filename, content_type, size_bytes, tags, etc.)
- Verify no file content in response (metadata only)

### TC-04: Download Document
- Upload a document
- Download by ID
- Verify content matches original

### TC-05: Delete Document
- Upload a document
- Delete by ID
- Verify 404 on subsequent access

## Multiple Document Management

### TC-06: Upload Multiple Documents
- Upload 10 different documents
- Verify all IDs are unique
- Query and verify all present

### TC-07: Mixed Operations
- Upload 5 documents
- Delete 2 documents
- Upload 3 more documents
- Query and verify correct count

## Edge Cases

### TC-08: Empty File
- Upload empty file
- Verify successful storage
- Download and verify empty


### TC-09: Special Characters in Filename
- Upload file with spaces, unicode, special chars
- Verify metadata preserved
- Download successfully

### TC-10: Unicode Content
- Upload file with unicode content
- Verify content preserved correctly
- Download and verify encoding

## Error Scenarios

### TC-11: Get Metadata for Non-existent Document
- Request metadata for invalid document ID
- Verify 404 response

### TC-12: Download Non-existent Document
- Request invalid document ID
- Verify 404 response

### TC-13: Delete Non-existent Document
- Delete invalid document ID
- Verify 404 response

### TC-14: Path Traversal Protection
- Attempt path traversal in document ID
- Verify rejection/sanitization

### TC-15: Invalid Document ID Format
- Use invalid characters in ID
- Verify appropriate error handling

## Persistence Testing

### TC-16: Data Persistence Across Restarts
- Upload documents
- Stop container
- Start container
- Verify documents still accessible

## Configuration Testing

### TC-17: Custom Storage Path
- Set DOCUMENT_STORAGE_PATH
- Verify documents stored in correct location

### TC-18: Custom Port
- Set DOCUMENT_SERVER_PORT
- Verify server listens on custom port

## Performance Smoke Tests

### TC-19: Bulk Upload
- Upload 50 documents
- Measure total time
- Verify all successful

### TC-20: Bulk Query
- With 100 documents stored
- Query all documents
- Measure response time

### TC-21: Concurrent Operations
- Simulate multiple clients
- Verify no race conditions
- Check data integrity

## Document Create/Write Operations

### TC-16: Create Placeholder Document
- POST /documents with JSON body (Content-Type: application/json)
- Body: `{"filename": "test.md", "tags": ["test"]}`
- Verify document ID returned
- Verify size_bytes = 0
- Verify checksum is null
- Verify content_type inferred from filename

### TC-17: Create Placeholder with Metadata
- Create placeholder with tags and description
- Body: `{"filename": "doc.md", "tags": ["a", "b"], "metadata": {"description": "..."}}`
- Verify tags preserved in response
- Verify metadata preserved in response

### TC-18: Write Content to Placeholder
- Create placeholder document via POST /documents (JSON)
- PUT content to /documents/{id}/content
- Verify size_bytes updated (> 0)
- Verify checksum computed (not null)
- Download and verify content matches

### TC-19: Write Updates Existing Content
- Upload document with initial content (multipart)
- Write new content via PUT /documents/{id}/content
- Verify old content replaced completely
- Verify new checksum differs from old

### TC-20: Write to Non-existent Document
- PUT content to /documents/{invalid-id}/content
- Verify 404 response

### TC-21: Full Create-Write-Read Workflow
- Step 1: Create placeholder document (size=0, checksum=null)
- Step 2: Write content via PUT (size>0, checksum set)
- Step 3: Read content back via GET
- Verify content matches what was written

### TC-22: Checksum Field in Response
- Upload document and verify checksum in response
- Get metadata and verify checksum present
- Query documents and verify checksum in list items
- Verify checksum consistency across endpoints

## Document Edit Operations

### TC-23: String Replacement - Unique Match
- Create document with content "Hello world, hello universe"
- PATCH with `{"old_string": "world", "new_string": "planet"}`
- Verify content is "Hello planet, hello universe"
- Verify `replacements_made: 1` in response
- Verify checksum updated

### TC-24: String Replacement - Replace All
- Create document with content "TODO: item1\nTODO: item2\nTODO: item3"
- PATCH with `{"old_string": "TODO", "new_string": "DONE", "replace_all": true}`
- Verify all occurrences replaced
- Verify `replacements_made: 3` in response

### TC-25: String Replacement - Not Found Error
- Create document with content "Hello world"
- PATCH with `{"old_string": "missing", "new_string": "replacement"}`
- Verify 400 response with "old_string not found" error

### TC-26: String Replacement - Ambiguous Match Error
- Create document with content "the the the"
- PATCH with `{"old_string": "the", "new_string": "a"}`
- Verify 400 response with "matches N times" error
- Verify content unchanged

### TC-27: Offset Insert (length=0 or omitted)
- Create document with content "ABCDEF"
- PATCH with `{"offset": 3, "new_string": "XYZ"}`
- Verify content is "ABCXYZDEF"
- Verify `edit_range: {offset: 3, old_length: 0, new_length: 3}`

### TC-28: Offset Replace (length > 0)
- Create document with content "ABCDEF"
- PATCH with `{"offset": 2, "length": 2, "new_string": "XY"}`
- Verify content is "ABXYEF"
- Verify `edit_range: {offset: 2, old_length: 2, new_length: 2}`

### TC-29: Offset Delete (empty new_string)
- Create document with content "ABCDEF"
- PATCH with `{"offset": 2, "length": 2, "new_string": ""}`
- Verify content is "ABEF"
- Verify `edit_range: {offset: 2, old_length: 2, new_length: 0}`

### TC-30: Offset Out of Bounds Error
- Create document with content "ABCDEF" (6 chars)
- PATCH with `{"offset": 10, "new_string": "X"}`
- Verify 400 response with "exceeds document length" error
- Verify content unchanged

### TC-31: Edit Non-existent Document
- PATCH with invalid document ID
- Verify 404 response

### TC-32: Edit Binary Content Type Error
- Upload binary file (e.g., image)
- PATCH with edit request
- Verify 400 response with "text content types" error

### TC-33: Edit Triggers Semantic Re-indexing
- Enable semantic search
- Create and write document with content "original content about cats"
- Edit to "updated content about dogs"
- Search for "dogs" - should find document
- Search for "cats" - should NOT find document (re-indexed)

### TC-34: Mode Validation - Mixed Parameters
- PATCH with `{"old_string": "x", "offset": 0, "new_string": "y"}`
- Verify 400 response with "cannot mix" error

### TC-35: Mode Validation - Missing Parameters
- PATCH with `{"new_string": "y"}` (no old_string or offset)
- Verify 400 response with "must provide" error
