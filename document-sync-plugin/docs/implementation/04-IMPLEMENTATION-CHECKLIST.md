# Implementation Block 04: Integration & Docker - Detailed Checklist

## Project Structure Reference

```
document-sync-plugin/
├── skills/document-sync/           # Blocks 03, 05 (already complete)
│   └── commands/                   # CLI tools to test
├── document-server/                # THIS BLOCK - Add Docker & testing
│   ├── Dockerfile                  # NEW - Docker configuration
│   ├── .dockerignore               # NEW - Docker ignore file
│   ├── pyproject.toml              # Already exists
│   └── src/                        # Already complete from Blocks 01-02
├── docker-compose.yml              # NEW - At project root
├── test-data/                      # NEW - Test fixtures
├── run-integration-tests.sh        # NEW - Integration test script
├── test-scenarios.md               # NEW - Test documentation
├── README.md                       # UPDATE - Add Docker info
├── TROUBLESHOOTING.md              # NEW - Troubleshooting guide
└── USER-GUIDE.md                   # NEW - User documentation
```

**This block focuses on: Integration, Docker setup, and comprehensive testing**

## Overall Goal

Wire everything together with Docker, create comprehensive integration tests, and validate the complete document-sync system end-to-end. This block focuses on containerization, automated testing, comprehensive documentation, and ensuring the system works reliably in production-like conditions.

## Checkpoint Instructions

- Mark each checkpoint with `- [x]` when completed
- Work through phases sequentially
- Test thoroughly at each phase before proceeding
- Document any issues encountered in TROUBLESHOOTING.md

---

## Phase 1: Docker Setup

### 1.1 Create Dockerfile

- [ ] Create `document-server/Dockerfile`

```dockerfile
FROM python:3.11-slim

# Install UV package manager
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using UV
RUN uv pip install --system -e .

# Copy application code
COPY . .

# Expose port
EXPOSE 8766

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8766/health')" || exit 1

# Run the server
CMD ["python", "-m", "document_server.main"]
```

### 1.2 Create Docker Compose Configuration

- [ ] Create `docker-compose.yml` in project root

```yaml
version: '3.8'

services:
  document-server:
    build:
      context: ./document-server
      dockerfile: Dockerfile
    container_name: document-sync-server
    ports:
      - "8766:8766"
    volumes:
      - document-data:/app/data
    environment:
      - DOCUMENT_SERVER_HOST=0.0.0.0
      - DOCUMENT_SERVER_PORT=8766
      - DOCUMENT_STORAGE_PATH=/app/data
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8766/health')"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
    restart: unless-stopped

volumes:
  document-data:
    driver: local
```

### 1.3 Create .dockerignore

- [ ] Create `document-server/.dockerignore`

```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
.pytest_cache/
.coverage
htmlcov/
.env
.venv
venv/
data/
*.log
.DS_Store
```

### 1.4 Test Docker Build and Startup

- [ ] Build Docker image:
```bash
docker-compose build
```

- [ ] Start the service:
```bash
docker-compose up -d
```

- [ ] Check container status:
```bash
docker-compose ps
```

- [ ] Verify health check passes:
```bash
docker inspect --format='{{json .State.Health}}' document-sync-server
```

- [ ] Test basic connectivity:
```bash
curl http://localhost:8766/health
```

- [ ] Check logs for errors:
```bash
docker-compose logs document-server
```

---

## Phase 2: Integration Test Suite

### 2.1 Create Test Scenarios Documentation

- [ ] Create `document-sync-plugin/docs/test-scenarios.md`

```markdown
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

### TC-08: Large File
- Upload 5MB binary file
- Verify successful storage
- Download and verify integrity

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
```

### 2.2 Create Test Data Directory

- [ ] Create `document-sync-plugin/test-data/` directory:
```bash
mkdir -p document-sync-plugin/test-data
```

### 2.3 Generate Test Fixtures

- [ ] Create `document-sync-plugin/test-data/small.txt`:
```
Hello, this is a small test document.
```

- [ ] Create `document-sync-plugin/test-data/test.md`:
```markdown
# Test Document

This is a **markdown** test document with formatting.

## Features
- Lists
- Code blocks
- Headers
```

- [ ] Create `document-sync-plugin/test-data/test.json`:
```json
{
  "type": "test",
  "data": {
    "items": [1, 2, 3],
    "nested": {
      "value": true
    }
  }
}
```

- [ ] Create large binary file:
```bash
dd if=/dev/urandom of=document-sync-plugin/test-data/large.bin bs=1024 count=5120
```

- [ ] Create `document-sync-plugin/test-data/unicode.txt`:
```
Unicode test: 你好世界 🌍 Émojis and spëcial çhars
```

- [ ] Create `document-sync-plugin/test-data/special-chars.txt`:
```
File with special chars: !@#$%^&*()_+-=[]{}|;':",./<>?
```

### 2.4 Create Integration Test Script

- [ ] Create `document-sync-plugin/run-integration-tests.sh` (see implementation notes for full script)

### 2.5 Make Script Executable and Run Initial Test

- [ ] Make script executable:
```bash
chmod +x document-sync-plugin/run-integration-tests.sh
```

- [ ] Run tests:
```bash
cd document-sync-plugin && ./run-integration-tests.sh
```

---

## Phase 3: System Validation

### 3.1 Test with Docker

- [ ] Clean environment:
```bash
docker-compose down -v
```

- [ ] Build fresh:
```bash
docker-compose build --no-cache
```

- [ ] Start services:
```bash
docker-compose up -d
```

- [ ] Wait for health check:
```bash
sleep 10 && docker inspect --format='{{json .State.Health}}' document-sync-server
```

- [ ] Run integration tests:
```bash
cd document-sync-plugin && ./run-integration-tests.sh
```

### 3.2 Test Persistence Across Restarts

- [ ] Upload test documents
- [ ] Note document IDs
- [ ] Restart container:
```bash
docker-compose restart document-server
```

- [ ] Wait for startup
- [ ] Verify documents still exist

### 3.3 Run Performance Smoke Tests

- [ ] Test bulk operations (100 documents)
- [ ] Measure query performance
- [ ] Check memory usage:
```bash
docker stats --no-stream document-sync-server
```

### 3.4 Verify Volume Mounting

- [ ] Check volume path
- [ ] Verify files in volume
- [ ] Check permissions

### 3.5 Test Configuration via Environment Variables

- [ ] Update docker-compose.yml with custom config
- [ ] Restart with new configuration
- [ ] Verify custom port/path in use
- [ ] Revert to default configuration

---

## Phase 4: Documentation

### 4.1 Create Project Root README

- [ ] Create `README.md` in project root with sections:
  - Project overview and purpose
  - Quick start (Docker Compose)
  - Installation instructions
  - Basic usage examples
  - Environment variables reference
  - Docker commands cheat sheet
  - Links to detailed documentation

### 4.2 Create Document Server README

- [ ] Create `document-server/README.md` with sections:
  - Server overview
  - API endpoints documentation
  - Request/response examples
  - Running locally
  - Configuration options
  - Storage structure

### 4.3 Create Skills Documentation

- [ ] Create `skills/document-sync/README.md` with sections:
  - Skill overview
  - Available commands
  - Command reference
  - Usage examples
  - Configuration
  - Troubleshooting

### 4.4 Create Troubleshooting Guide

- [ ] Create `TROUBLESHOOTING.md` with common issues and solutions

---

## Phase 5: Final Validation

### 5.1 Fresh Start Test

- [ ] Complete teardown
- [ ] Remove test artifacts
- [ ] Build from scratch
- [ ] Start services

### 5.2 Run Full Integration Test Suite

- [ ] Execute complete test suite
- [ ] Verify all tests pass
- [ ] Review test output
- [ ] Check test execution time

### 5.3 Manual Workflow Test

- [ ] Upload a document
- [ ] Query all documents
- [ ] Download specific document
- [ ] Delete document
- [ ] Verify deletion

### 5.4 Check Logs for Errors

- [ ] Review server logs
- [ ] Check for warnings
- [ ] Verify no exceptions

### 5.5 Clean Shutdown Test

- [ ] Graceful shutdown
- [ ] Verify clean exit
- [ ] Check no orphaned containers

---

## Success Criteria

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

---

## Implementation Notes

### Docker Networking
- Server accessible at `localhost:8766` from host
- Container uses `0.0.0.0:8766` for binding
- Health check runs inside container

### Volume Permissions
- Docker volumes owned by container user
- SQLite must be writable
- Use `docker exec` to fix permissions if needed

### Health Check Reliability
- Use simple HTTP check
- Allow adequate start period (5s minimum)
- Set reasonable timeout (3s)
- Retry 3 times before unhealthy

### Test Data Cleanup
```bash
# Clean all
docker-compose down -v

# Clean documents only
docker exec document-sync-server rm -rf /app/data/documents/*
```

### Performance Testing
```bash
# Measure time
time ./run-integration-tests.sh

# Monitor resources
docker stats document-sync-server
```
