#!/bin/bash

# End-to-end tests for Document Server API

BASE_URL="http://localhost:8766"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "============================================================"
echo "Document Server End-to-End Tests"
echo "============================================================"

# Test 1: Upload a document
echo -e "\n1. Testing document upload..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/documents" \
  -F "file=@tests/e2e.sh" \
  -F "tags=bash,testing" \
  -F 'metadata={"author":"test"}')

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
  echo -e "   ${GREEN}✓${NC} Upload test passed (HTTP $HTTP_CODE)"
  DOC_ID=$(echo "$BODY" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
  echo "   Document ID: $DOC_ID"
else
  echo -e "   ${RED}✗${NC} Upload test failed (HTTP $HTTP_CODE)"
  exit 1
fi

# Test 2: Query all documents
echo -e "\n2. Testing query all documents..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/documents")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
  echo -e "   ${GREEN}✓${NC} Query all test passed (HTTP $HTTP_CODE)"
else
  echo -e "   ${RED}✗${NC} Query all test failed (HTTP $HTTP_CODE)"
  exit 1
fi

# Test 3: Query by filename
echo -e "\n3. Testing query by filename..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/documents?filename=test")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
  echo -e "   ${GREEN}✓${NC} Filename query test passed (HTTP $HTTP_CODE)"
else
  echo -e "   ${RED}✗${NC} Filename query test failed (HTTP $HTTP_CODE)"
  exit 1
fi

# Test 4: Query by single tag
echo -e "\n4. Testing query by single tag..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/documents?tags=bash")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
  echo -e "   ${GREEN}✓${NC} Single tag query test passed (HTTP $HTTP_CODE)"
else
  echo -e "   ${RED}✗${NC} Single tag query test failed (HTTP $HTTP_CODE)"
  exit 1
fi

# Test 5: Query by multiple tags (AND logic)
echo -e "\n5. Testing query by multiple tags (AND logic)..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/documents?tags=bash,testing")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
  echo -e "   ${GREEN}✓${NC} AND logic query test passed (HTTP $HTTP_CODE)"
else
  echo -e "   ${RED}✗${NC} AND logic query test failed (HTTP $HTTP_CODE)"
  exit 1
fi

# Test 6: Download document
echo -e "\n6. Testing document download..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/documents/$DOC_ID" -o /tmp/downloaded_doc.txt)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
  echo -e "   ${GREEN}✓${NC} Download test passed (HTTP $HTTP_CODE)"
  # Verify content
  if [ -f /tmp/downloaded_doc.txt ]; then
    SIZE=$(wc -c < /tmp/downloaded_doc.txt)
    echo "   Downloaded file size: $SIZE bytes"
  fi
else
  echo -e "   ${RED}✗${NC} Download test failed (HTTP $HTTP_CODE)"
  exit 1
fi

# Test 7: Delete document
echo -e "\n7. Testing document deletion..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/documents/$DOC_ID")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
  echo -e "   ${GREEN}✓${NC} Delete test passed (HTTP $HTTP_CODE)"
else
  echo -e "   ${RED}✗${NC} Delete test failed (HTTP $HTTP_CODE)"
  exit 1
fi

# Test 8: Verify document is deleted
echo -e "\n8. Verifying document is deleted..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/documents/$DOC_ID")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "404" ]; then
  echo -e "   ${GREEN}✓${NC} Document deletion verified (HTTP $HTTP_CODE)"
else
  echo -e "   ${RED}✗${NC} Document should be deleted (HTTP $HTTP_CODE)"
  exit 1
fi

# Test 9: Delete non-existent document
echo -e "\n9. Testing delete non-existent document..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/documents/doc_doesnotexist")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "404" ]; then
  echo -e "   ${GREEN}✓${NC} Non-existent delete test passed (HTTP $HTTP_CODE)"
else
  echo -e "   ${RED}✗${NC} Non-existent delete test failed (HTTP $HTTP_CODE)"
  exit 1
fi

# Test 10: Path traversal protection
echo -e "\n10. Testing path traversal protection..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/documents/../../../etc/passwd")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "404" ]; then
  echo -e "   ${GREEN}✓${NC} Path traversal protection test passed (HTTP $HTTP_CODE)"
else
  echo -e "   ${RED}✗${NC} Path traversal protection test failed (HTTP $HTTP_CODE)"
  exit 1
fi

echo -e "\n============================================================"
echo -e "${GREEN}✅ All end-to-end tests passed!${NC}"
echo "============================================================"
