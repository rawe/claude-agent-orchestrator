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

### TC-03: Download Document
- Upload a document
- Download by ID
- Verify content matches original

### TC-04: Delete Document
- Upload a document
- Delete by ID
- Verify 404 on subsequent access

## Multiple Document Management

### TC-05: Upload Multiple Documents
- Upload 10 different documents
- Verify all IDs are unique
- Query and verify all present

### TC-06: Mixed Operations
- Upload 5 documents
- Delete 2 documents
- Upload 3 more documents
- Query and verify correct count

## Edge Cases

### TC-07: Empty File
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

### TC-11: Download Non-existent Document
- Request invalid document ID
- Verify 404 response

### TC-12: Delete Non-existent Document
- Delete invalid document ID
- Verify 404 response

### TC-13: Path Traversal Protection
- Attempt path traversal in document ID
- Verify rejection/sanitization

### TC-14: Invalid Document ID Format
- Use invalid characters in ID
- Verify appropriate error handling

## Persistence Testing

### TC-15: Data Persistence Across Restarts
- Upload documents
- Stop container
- Start container
- Verify documents still accessible

## Configuration Testing

### TC-16: Custom Storage Path
- Set DOCUMENT_STORAGE_PATH
- Verify documents stored in correct location

### TC-17: Custom Port
- Set DOCUMENT_SERVER_PORT
- Verify server listens on custom port

## Performance Smoke Tests

### TC-18: Bulk Upload
- Upload 50 documents
- Measure total time
- Verify all successful

### TC-19: Bulk Query
- With 100 documents stored
- Query all documents
- Measure response time

### TC-20: Concurrent Operations
- Simulate multiple clients
- Verify no race conditions
- Check data integrity
