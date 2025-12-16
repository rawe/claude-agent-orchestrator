# Integration Tests

Comprehensive test suite for the Context Store Server.

## Running Tests

### 1. Start Elasticsearch

```bash
cd servers/context-store
docker compose up -d
```

Wait for healthy status:
```bash
curl http://localhost:9200/_cluster/health
```

### 2. Start Context Store Server

```bash
cd servers/context-store
SEMANTIC_SEARCH_ENABLED=true uv run python -m src.main
```

### 3. Run Tests

```bash
cd servers/context-store/tests
./run-integration-tests.sh
```

### Cleanup

```bash
# Stop server: Ctrl+C
# Stop Elasticsearch:
cd servers/context-store && docker compose down
```

## Test Coverage

The test suite includes 35 scenarios covering:
- Basic CRUD operations (upload, query, download, delete)
- Edge cases (empty files, unicode content, special characters)
- Error handling (404 responses, invalid inputs)
- Tag filtering with AND logic
- Metadata handling
- Document create/write operations (placeholder creation, content writing)
- Checksum verification
- Document edit operations (string replacement, offset-based edits)
- Edit error handling (not found, ambiguous match, out of bounds)

For detailed test case documentation, see [test-scenarios.md](test-scenarios.md).
