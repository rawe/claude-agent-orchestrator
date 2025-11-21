# Implementation Block 04: Integration & Docker

## Goal
Wire everything together, create comprehensive manual test scenarios, add Docker setup for consistent development environment, and validate the complete system works end-to-end.

## Benefit
🎯 **Production-Ready System** - Fully integrated, tested system that can run in Docker. Ready for real-world use in Claude Code sessions. You can confidently use it or share it with others.

## MVP Architecture Reference

**Document**: [`architecture-mvp.md`](../architecture-mvp.md)

**Relevant Sections**:
- `Complete Flow Diagram` (lines 836-870)
- `Deployment - Docker Setup` (lines 1000-1031)
- `Key MVP Design Decisions` (lines 873-887)
- `Environment Variables` (lines 766-787)

## What Gets Built

### 1. Docker Configuration
- **Dockerfile** for document-server
- **docker-compose.yml** for easy orchestration
- Volume mounting for persistent storage
- Health checks

### 2. Integration Test Suite
- Manual test scenarios document
- Test data fixtures
- Validation scripts

### 3. Documentation
- Complete README with quickstart
- Troubleshooting guide
- Environment variable reference

### 4. System Validation
- Cross-component testing
- Performance smoke tests
- Error scenario validation

## Session Flow

### Step 1: Create Docker Setup (~60min)

1. **Create document-server/Dockerfile**
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   # Install uv
   RUN pip install --no-cache-dir uv

   # Copy project files
   COPY pyproject.toml uv.lock ./
   COPY src/ ./src/

   # Install dependencies
   RUN uv sync --frozen

   # Create storage directory
   RUN mkdir -p .document-storage

   # Expose port
   EXPOSE 8766

   # Health check
   HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8766/documents').read()" || exit 1

   # Run server
   CMD ["uv", "run", "src/main.py"]
   ```

2. **Create docker-compose.yml at project root**
   ```yaml
   version: '3.8'

   services:
     document-server:
       build:
         context: ./document-server
         dockerfile: Dockerfile
       ports:
         - "8766:8766"
       volumes:
         - document-storage:/app/.document-storage
       environment:
         - DOCUMENT_SERVER_HOST=0.0.0.0
         - DOCUMENT_SERVER_PORT=8766
       healthcheck:
         test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8766/documents').read()"]
         interval: 10s
         timeout: 3s
         retries: 3
       restart: unless-stopped

   volumes:
     document-storage:
       driver: local
   ```

3. **Test Docker build**
   ```bash
   # Build image
   docker-compose build

   # Start service
   docker-compose up -d

   # Check logs
   docker-compose logs -f document-server

   # Test health
   docker-compose ps
   # Should show "healthy" status

   # Test endpoint
   curl http://localhost:8766/documents

   # Stop service
   docker-compose down
   ```

4. **Create .dockerignore in document-server/**
   ```
   .document-storage/
   __pycache__/
   *.pyc
   .pytest_cache/
   .coverage
   htmlcov/
   ```

### Step 2: Integration Test Scenarios (~90min)

1. **Create test-scenarios.md**

   Document comprehensive test scenarios:

   **A. Basic CRUD Operations**
   - Upload single document
   - Query to find it
   - Download and verify content
   - Delete and verify removal

   **B. Multiple Document Management**
   - Upload 5 documents with varying tags
   - Query with different filters
   - Verify AND logic for tags
   - Bulk operations

   **C. Edge Cases**
   - Empty file upload
   - Large file (10MB+)
   - Special characters in filename
   - Unicode content
   - No tags specified
   - Empty description

   **D. Error Scenarios**
   - Upload to stopped server
   - Query non-existent document
   - Delete already deleted document
   - Path traversal attempts
   - Invalid document ID format

   **E. Persistence Testing**
   - Upload document
   - Stop server
   - Restart server
   - Verify document still exists

   **F. Configuration Testing**
   - Custom port via ENV
   - Custom storage directory
   - Custom timeout

   **G. Performance Smoke Tests**
   - Upload 100 small documents
   - Query with 100 results
   - Measure response times

2. **Create test-data/ directory**
   ```bash
   mkdir -p test-data
   ```

3. **Generate test fixtures**
   ```bash
   # Create test documents
   echo "Small text file" > test-data/small.txt

   echo "# Markdown Document

   This is a test markdown file with formatting.

   ## Section 1
   - Bullet 1
   - Bullet 2
   " > test-data/test.md

   # Create JSON test file
   echo '{"key": "value", "nested": {"data": [1,2,3]}}' > test-data/test.json

   # Create large file (10MB)
   dd if=/dev/zero of=test-data/large.bin bs=1M count=10

   # Create file with special chars
   echo "Content" > test-data/"file with spaces & special!.txt"

   # Create unicode content
   echo "Hello 世界 🌍" > test-data/unicode.txt
   ```

4. **Create run-integration-tests.sh**
   ```bash
   #!/bin/bash
   set -e

   echo "🧪 Document Sync Integration Tests"
   echo "=================================="
   echo

   # Ensure server is running
   echo "Checking server..."
   curl -s http://localhost:8766/documents > /dev/null || {
     echo "❌ Server not running on port 8766"
     exit 1
   }
   echo "✅ Server is running"
   echo

   cd skills/document-sync/commands

   # Test 1: Basic upload
   echo "Test 1: Upload document"
   RESULT=$(uv run doc-push ../../../test-data/small.txt --name "Small Test" --tags "test")
   DOC_ID=$(echo $RESULT | jq -r '.document_id')
   echo "✅ Uploaded: $DOC_ID"
   echo

   # Test 2: Query
   echo "Test 2: Query document"
   QUERY_RESULT=$(uv run doc-query --name "Small")
   COUNT=$(echo $QUERY_RESULT | jq 'length')
   [[ $COUNT -eq 1 ]] || { echo "❌ Expected 1 result, got $COUNT"; exit 1; }
   echo "✅ Query returned 1 result"
   echo

   # Test 3: Download
   echo "Test 3: Download document"
   uv run doc-pull $DOC_ID --output /tmp/downloaded.txt
   diff ../../../test-data/small.txt /tmp/downloaded.txt || {
     echo "❌ Content mismatch"
     exit 1
   }
   echo "✅ Content verified"
   echo

   # Test 4: Tag AND logic
   echo "Test 4: Tag AND logic"
   uv run doc-push ../../../test-data/test.md --name "MD Test" --tags "test,markdown"
   RESULTS=$(uv run doc-query --tags "test,markdown")
   COUNT=$(echo $RESULTS | jq 'length')
   [[ $COUNT -eq 1 ]] || { echo "❌ AND logic failed"; exit 1; }
   echo "✅ AND logic works"
   echo

   # Test 5: Delete
   echo "Test 5: Delete document"
   uv run doc-delete $DOC_ID
   QUERY_AFTER=$(uv run doc-query --name "Small")
   COUNT_AFTER=$(echo $QUERY_AFTER | jq 'length')
   [[ $COUNT_AFTER -eq 0 ]] || { echo "❌ Document not deleted"; exit 1; }
   echo "✅ Document deleted"
   echo

   # Test 6: Error handling
   echo "Test 6: Error handling"
   ERROR_RESULT=$(uv run doc-pull doc_nonexistent 2>&1 || true)
   echo $ERROR_RESULT | grep -q "error" || { echo "❌ Error not handled"; exit 1; }
   echo "✅ Error handling works"
   echo

   echo "=================================="
   echo "✅ All integration tests passed!"
   ```

5. **Make script executable and run**
   ```bash
   chmod +x run-integration-tests.sh
   ./run-integration-tests.sh
   ```

### Step 3: System Validation (~45min)

1. **Test with Docker**
   ```bash
   # Start with Docker
   docker-compose up -d

   # Wait for health check
   sleep 5

   # Run integration tests against Docker
   ./run-integration-tests.sh

   # Check storage volume
   docker exec -it $(docker-compose ps -q document-server) ls -la /app/.document-storage

   # Check database
   docker exec -it $(docker-compose ps -q document-server) sqlite3 /app/.document-storage/documents.db ".tables"

   # Stop and clean
   docker-compose down -v
   ```

2. **Test persistence with Docker**
   ```bash
   # Start server
   docker-compose up -d

   # Upload document
   cd skills/document-sync/commands
   DOC_ID=$(uv run doc-push ../../../test-data/test.md --name "Persist Test" --tags "persist" | jq -r '.document_id')
   cd ../../..

   # Stop server (keep volume)
   docker-compose stop

   # Start server again
   docker-compose start

   # Query - should still exist
   cd skills/document-sync/commands
   uv run doc-query --name "Persist"
   # Should return the document

   cd ../../..
   docker-compose down -v
   ```

3. **Performance smoke test**
   ```bash
   # Start server
   docker-compose up -d

   cd skills/document-sync/commands

   # Upload 50 documents and measure time
   echo "Uploading 50 documents..."
   time for i in {1..50}; do
     uv run doc-push ../../../test-data/small.txt \
       --name "Doc $i" \
       --tags "test,batch$((i % 5))" \
       > /dev/null
   done

   # Query all
   echo "Querying all documents..."
   time uv run doc-query --limit 100 > /dev/null

   # Clean up
   cd ../../..
   docker-compose down -v
   ```

### Step 4: Documentation (~45min)

1. **Create comprehensive README.md at project root**

   Include:
   - Project overview
   - Quick start guide
   - Installation instructions
   - Usage examples
   - Environment variables
   - Docker deployment
   - Troubleshooting
   - Architecture overview (link to docs)

2. **Create document-server/README.md**

   Server-specific documentation:
   - API endpoints
   - Running locally
   - Configuration
   - Storage structure

3. **Create skills/document-sync/README.md**

   CLI documentation:
   - Command reference
   - Examples
   - Configuration

4. **Create TROUBLESHOOTING.md**

   Common issues and solutions:
   - Server won't start
   - Connection refused
   - Database locked
   - Permission errors
   - Docker issues

### Step 5: Final Validation (~30min)

Run through complete user journey:

```bash
# 1. Fresh start
docker-compose down -v
rm -rf document-server/.document-storage

# 2. Build and start
docker-compose up -d
docker-compose logs -f document-server &

# 3. Wait for healthy
while [[ $(docker-compose ps document-server | grep "healthy") == "" ]]; do
  echo "Waiting for server..."
  sleep 2
done

# 4. Run full integration tests
./run-integration-tests.sh

# 5. Manual workflow test
cd skills/document-sync/commands

# Upload various documents
uv run doc-push ../../../test-data/test.md \
  --name "Architecture Doc" \
  --tags "docs,architecture,mvp"

uv run doc-push ../../../test-data/test.json \
  --name "Config File" \
  --tags "config,json"

uv run doc-push ../../../test-data/unicode.txt \
  --name "Unicode Test" \
  --tags "test,unicode"

# Query various ways
uv run doc-query | jq
uv run doc-query --tags "docs" | jq
uv run doc-query --tags "docs,architecture" | jq
uv run doc-query --name "Config" | jq

# Download and verify
DOC_ID=$(uv run doc-query --name "Config" | jq -r '.[0].document_id')
uv run doc-pull $DOC_ID --output /tmp/config.json
cat /tmp/config.json

# Clean up specific document
uv run doc-delete $DOC_ID

cd ../../..

# 6. Check logs for errors
docker-compose logs document-server | grep -i error

# 7. Clean shutdown
docker-compose down
```

## Success Criteria ✅

- [ ] Docker image builds successfully
- [ ] docker-compose up starts service with health check passing
- [ ] All integration test scenarios pass
- [ ] Persistence works across container restarts
- [ ] Performance smoke test completes (50 uploads < 30s)
- [ ] Documentation complete and accurate
- [ ] Error scenarios handled gracefully
- [ ] Volume mounting works correctly
- [ ] ENV variables configurable in docker-compose
- [ ] Clean shutdown with docker-compose down

## Implementation Hints & Gotchas

### Docker Networking
When running server in Docker, CLI commands from host must use `localhost:8766`:
```bash
# Server in Docker listening on 0.0.0.0:8766
# CLI from host connects to localhost:8766
DOCUMENT_SERVER_URL=http://localhost:8766 uv run doc-query
```

### Docker Volume Permissions
If permission errors occur:
```dockerfile
# In Dockerfile, create storage dir with correct permissions
RUN mkdir -p .document-storage && chmod 777 .document-storage
```

### Health Check Reliability
Use simple Python check instead of curl (curl not in slim image):
```dockerfile
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8766/documents').read()" || exit 1
```

### Integration Test Reliability
Always check server is running first:
```bash
curl -s http://localhost:8766/documents > /dev/null || {
  echo "Server not running"
  exit 1
}
```

### Test Data Cleanup
Between test runs:
```bash
# Full cleanup
docker-compose down -v  # -v removes volumes
rm -rf document-server/.document-storage

# Or reset database only
docker exec $(docker-compose ps -q document-server) rm /app/.document-storage/documents.db
docker-compose restart
```

### Performance Testing
Use `time` to measure:
```bash
time for i in {1..100}; do
  uv run doc-push test.txt --name "Doc $i" > /dev/null
done
```

### Docker Logs
Tail logs during testing:
```bash
docker-compose logs -f --tail=50 document-server
```

## Common Issues

**Issue**: Docker build fails on uv sync
- **Solution**: Ensure uv.lock is committed, or use `uv sync --no-lock`

**Issue**: Health check fails immediately
- **Solution**: Add `start-period` to give server time to start

**Issue**: Volume permissions denied
- **Solution**: Check volume ownership, may need to run as specific user

**Issue**: Integration tests fail intermittently
- **Solution**: Add sleep after docker-compose up to ensure server ready

**Issue**: Performance degradation after many uploads
- **Solution**: Check disk space, SQLite database size

## Dependencies for Next Block
- ✅ Docker setup complete
- ✅ Integration tests passing
- ✅ Documentation written
- ✅ System validated end-to-end

## Estimated Time
**3-4 hours** including Docker setup, test creation, validation, and documentation.

## Notes
- Docker is optional but recommended for consistent environment
- Manual testing is sufficient for MVP - automated tests can come later
- Performance smoke tests help identify bottlenecks early
- Good documentation prevents support burden
- Health checks are critical for production readiness