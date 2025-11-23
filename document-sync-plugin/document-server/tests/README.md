# Integration Tests

Comprehensive test suite for the Document Sync Server.

## Running Tests

**Requirements**: Server must be running on `http://localhost:8766`

**Run**:
```bash
# From document-server/tests/ directory
./run-integration-tests.sh
```

## Test Coverage

The test suite includes 14 scenarios covering:
- Basic CRUD operations (upload, query, download, delete)
- Edge cases (empty files, unicode content, special characters)
- Error handling (404 responses, invalid inputs)
- Tag filtering with AND logic
- Metadata handling

For detailed test case documentation, see [test-scenarios.md](test-scenarios.md).
