#!/bin/bash

# Integration test script for Document Sync Plugin
# Tests all CRUD operations, edge cases, and error scenarios

set -e  # Exit on error

# Configuration
SERVER_URL="${SERVER_URL:-http://localhost:8766}"
TEST_DATA_DIR="./test-data"
RESULTS_FILE="./test-results.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_test() {
    echo -e "\n${YELLOW}[TEST] $1${NC}"
    TESTS_RUN=$((TESTS_RUN + 1))
}

log_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

cleanup() {
    echo -e "\n${YELLOW}Cleaning up test documents...${NC}"
    # Query all documents and delete them
    doc_ids=$(curl -s "${SERVER_URL}/documents" | jq -r '.[].id' 2>/dev/null || echo "")
    if [ -n "$doc_ids" ]; then
        for doc_id in $doc_ids; do
            curl -s -X DELETE "${SERVER_URL}/documents/${doc_id}" > /dev/null 2>&1 || true
        done
    fi
}

# Check server is running
check_server() {
    log_test "TC-00: Server Health Check"
    response=$(curl -s "${SERVER_URL}/health")
    if echo "$response" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
        log_pass "Server is healthy and responding"
    else
        log_fail "Server health check failed"
        exit 1
    fi
}

# TC-01: Upload Document
test_upload_document() {
    log_test "TC-01: Upload Document"

    response=$(curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/small.txt" \
        -F "tags=test,sample")

    doc_id=$(echo "$response" | jq -r '.id')

    if [ -n "$doc_id" ] && [ "$doc_id" != "null" ]; then
        log_pass "Document uploaded successfully with ID: $doc_id"
        echo "$doc_id" > /tmp/test_doc_id.txt
    else
        log_fail "Failed to upload document"
    fi
}

# TC-02: Query Documents
test_query_documents() {
    log_test "TC-02: Query Documents"

    # Upload a few documents first
    curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/test.md" \
        -F "tags=markdown" > /dev/null

    curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/test.json" \
        -F "tags=json,data" > /dev/null

    # Query all documents
    response=$(curl -s "${SERVER_URL}/documents")
    count=$(echo "$response" | jq '. | length')

    if [ "$count" -ge 2 ]; then
        log_pass "Query returned $count documents"
    else
        log_fail "Expected at least 2 documents, got $count"
    fi
}

# TC-03: Get Document Metadata
test_get_metadata() {
    log_test "TC-03: Get Document Metadata"

    # Upload a document
    upload_response=$(curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/small.txt" \
        -F "tags=meta,test")
    doc_id=$(echo "$upload_response" | jq -r '.id')

    # Get metadata
    metadata_response=$(curl -s "${SERVER_URL}/documents/${doc_id}/metadata")

    # Verify metadata fields
    meta_id=$(echo "$metadata_response" | jq -r '.id')
    meta_filename=$(echo "$metadata_response" | jq -r '.filename')
    meta_content_type=$(echo "$metadata_response" | jq -r '.content_type')
    meta_size=$(echo "$metadata_response" | jq -r '.size_bytes')

    # Verify no file content in response (should be JSON metadata only)
    is_json=$(echo "$metadata_response" | jq -e 'type == "object"' > /dev/null 2>&1 && echo "true" || echo "false")

    if [ "$meta_id" = "$doc_id" ] && [ -n "$meta_filename" ] && [ "$is_json" = "true" ] && [ "$meta_size" -gt 0 ]; then
        log_pass "Metadata retrieved successfully (id: $meta_id, size: $meta_size bytes)"
    else
        log_fail "Failed to retrieve correct metadata"
    fi
}

# TC-04: Download Document
test_download_document() {
    log_test "TC-04: Download Document"

    # Upload a document
    upload_response=$(curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/small.txt")
    doc_id=$(echo "$upload_response" | jq -r '.id')

    # Download it
    downloaded_content=$(curl -s "${SERVER_URL}/documents/${doc_id}")
    original_content=$(cat "${TEST_DATA_DIR}/small.txt")

    if [ "$downloaded_content" = "$original_content" ]; then
        log_pass "Downloaded content matches original"
    else
        log_fail "Downloaded content does not match original"
    fi
}

# TC-05: Delete Document
test_delete_document() {
    log_test "TC-05: Delete Document"

    # Upload a document
    upload_response=$(curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/small.txt")
    doc_id=$(echo "$upload_response" | jq -r '.id')

    # Delete it
    delete_response=$(curl -s -X DELETE "${SERVER_URL}/documents/${doc_id}")
    success=$(echo "$delete_response" | jq -r '.success')

    # Try to download (should fail)
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "${SERVER_URL}/documents/${doc_id}")

    if [ "$success" = "true" ] && [ "$http_code" = "404" ]; then
        log_pass "Document deleted successfully and not accessible"
    else
        log_fail "Delete operation failed or document still accessible"
    fi
}

# TC-06: Upload Multiple Documents
test_upload_multiple() {
    log_test "TC-06: Upload Multiple Documents"

    doc_ids=()
    for i in {1..10}; do
        echo "Test document $i" > /tmp/test_doc_$i.txt
        response=$(curl -s -X POST "${SERVER_URL}/documents" \
            -F "file=@/tmp/test_doc_$i.txt" \
            -F "tags=bulk,test$i")
        doc_id=$(echo "$response" | jq -r '.id')
        doc_ids+=("$doc_id")
        rm /tmp/test_doc_$i.txt
    done

    # Check all IDs are unique
    unique_count=$(printf '%s\n' "${doc_ids[@]}" | sort -u | wc -l)

    if [ "$unique_count" -eq 10 ]; then
        log_pass "All 10 documents uploaded with unique IDs"
    else
        log_fail "Expected 10 unique IDs, got $unique_count"
    fi
}

# TC-07: Mixed Operations
test_mixed_operations() {
    log_test "TC-07: Mixed Operations"

    cleanup

    # Upload 5 documents
    doc_ids=()
    for i in {1..5}; do
        echo "Mixed test $i" > /tmp/mixed_$i.txt
        response=$(curl -s -X POST "${SERVER_URL}/documents" \
            -F "file=@/tmp/mixed_$i.txt")
        doc_id=$(echo "$response" | jq -r '.id')
        doc_ids+=("$doc_id")
        rm /tmp/mixed_$i.txt
    done

    # Delete 2 documents
    curl -s -X DELETE "${SERVER_URL}/documents/${doc_ids[0]}" > /dev/null
    curl -s -X DELETE "${SERVER_URL}/documents/${doc_ids[1]}" > /dev/null

    # Upload 3 more
    for i in {6..8}; do
        echo "Mixed test $i" > /tmp/mixed_$i.txt
        curl -s -X POST "${SERVER_URL}/documents" \
            -F "file=@/tmp/mixed_$i.txt" > /dev/null
        rm /tmp/mixed_$i.txt
    done

    # Query and verify count (should be 6: 5 - 2 + 3)
    response=$(curl -s "${SERVER_URL}/documents")
    count=$(echo "$response" | jq '. | length')

    if [ "$count" -eq 6 ]; then
        log_pass "Mixed operations completed successfully, count is 6"
    else
        log_fail "Expected 6 documents, got $count"
    fi
}

# TC-08: Empty File
test_empty_file() {
    log_test "TC-08: Empty File"

    response=$(curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/empty.txt")
    doc_id=$(echo "$response" | jq -r '.id')

    if [ -n "$doc_id" ] && [ "$doc_id" != "null" ]; then
        # Download and verify it's empty
        downloaded_content=$(curl -s "${SERVER_URL}/documents/${doc_id}")
        if [ -z "$downloaded_content" ]; then
            log_pass "Empty file uploaded and downloaded successfully"
        else
            log_fail "Downloaded content is not empty"
        fi
    else
        log_fail "Failed to upload empty file"
    fi
}


# TC-09: Special Characters in Filename
test_special_chars_filename() {
    log_test "TC-09: Special Characters in Filename"

    response=$(curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/special-chars.txt")
    doc_id=$(echo "$response" | jq -r '.id')
    filename=$(echo "$response" | jq -r '.filename')

    if [ -n "$doc_id" ] && [ "$doc_id" != "null" ] && [ "$filename" = "special-chars.txt" ]; then
        log_pass "File with special chars in name uploaded successfully"
    else
        log_fail "Failed to handle special characters in filename"
    fi
}

# TC-10: Unicode Content
test_unicode_content() {
    log_test "TC-10: Unicode Content"

    response=$(curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/unicode.txt")
    doc_id=$(echo "$response" | jq -r '.id')

    if [ -n "$doc_id" ] && [ "$doc_id" != "null" ]; then
        # Download and verify content
        downloaded_content=$(curl -s "${SERVER_URL}/documents/${doc_id}")
        original_content=$(cat "${TEST_DATA_DIR}/unicode.txt")

        if [ "$downloaded_content" = "$original_content" ]; then
            log_pass "Unicode content preserved correctly"
        else
            log_fail "Unicode content not preserved"
        fi
    else
        log_fail "Failed to upload unicode file"
    fi
}

# TC-11: Get Metadata for Non-existent Document
test_metadata_nonexistent() {
    log_test "TC-11: Get Metadata for Non-existent Document"

    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${SERVER_URL}/documents/nonexistent-doc-id-12345/metadata")

    if [ "$http_code" = "404" ]; then
        log_pass "Correctly returned 404 for non-existent document metadata"
    else
        log_fail "Expected 404, got $http_code"
    fi
}

# TC-12: Download Non-existent Document
test_download_nonexistent() {
    log_test "TC-12: Download Non-existent Document"

    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${SERVER_URL}/documents/nonexistent-doc-id-12345")

    if [ "$http_code" = "404" ]; then
        log_pass "Correctly returned 404 for non-existent document"
    else
        log_fail "Expected 404, got $http_code"
    fi
}

# TC-13: Delete Non-existent Document
test_delete_nonexistent() {
    log_test "TC-13: Delete Non-existent Document"

    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X DELETE "${SERVER_URL}/documents/nonexistent-doc-id-12345")

    if [ "$http_code" = "404" ]; then
        log_pass "Correctly returned 404 for non-existent document deletion"
    else
        log_fail "Expected 404, got $http_code"
    fi
}

# TC-14: Query with Filters
test_query_with_filters() {
    log_test "TC-14: Query with Filters"

    cleanup

    # Upload documents with different tags
    curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/test.md" \
        -F "tags=markdown,doc" > /dev/null

    curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/test.json" \
        -F "tags=json,data" > /dev/null

    curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/small.txt" \
        -F "tags=text,doc" > /dev/null

    # Query by tag
    response=$(curl -s "${SERVER_URL}/documents?tags=doc")
    count=$(echo "$response" | jq '. | length')

    if [ "$count" -eq 2 ]; then
        log_pass "Tag filtering returned correct number of documents"
    else
        log_fail "Expected 2 documents with tag 'doc', got $count"
    fi
}

# TC-15: Metadata in Upload
test_metadata_upload() {
    log_test "TC-15: Metadata in Upload"

    metadata='{"author": "test", "version": "1.0"}'
    response=$(curl -s -X POST "${SERVER_URL}/documents" \
        -F "file=@${TEST_DATA_DIR}/small.txt" \
        -F "metadata=$metadata")

    doc_id=$(echo "$response" | jq -r '.id')
    returned_metadata=$(echo "$response" | jq -r '.metadata')

    if [ -n "$doc_id" ] && echo "$returned_metadata" | jq -e '.author == "test"' > /dev/null 2>&1; then
        log_pass "Metadata uploaded and returned correctly"
    else
        log_fail "Metadata not handled correctly"
    fi
}

# Summary
print_summary() {
    echo -e "\n${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Test Summary${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo -e "Total Tests:  $TESTS_RUN"
    echo -e "${GREEN}Passed:       $TESTS_PASSED${NC}"
    echo -e "${RED}Failed:       $TESTS_FAILED${NC}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}✗ Some tests failed${NC}"
        exit 1
    fi
}

# Main execution
main() {
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Document Sync Integration Tests${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo -e "Server URL: $SERVER_URL"
    echo -e "Test Data Directory: $TEST_DATA_DIR"

    # Check prerequisites
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is not installed. Please install jq to run tests.${NC}"
        exit 1
    fi

    if [ ! -d "$TEST_DATA_DIR" ]; then
        echo -e "${RED}Error: Test data directory not found: $TEST_DATA_DIR${NC}"
        exit 1
    fi

    # Run tests
    check_server
    test_upload_document
    test_query_documents
    test_get_metadata
    test_download_document
    test_delete_document
    test_upload_multiple
    test_mixed_operations
    test_empty_file
    test_special_chars_filename
    test_unicode_content
    test_metadata_nonexistent
    test_download_nonexistent
    test_delete_nonexistent
    test_query_with_filters
    test_metadata_upload

    # Cleanup and print summary
    cleanup
    print_summary
}

# Run main
main
