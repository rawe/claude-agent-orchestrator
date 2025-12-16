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
