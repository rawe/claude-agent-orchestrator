# Troubleshooting

## Common Errors

### Connection Refused
```json
{"error": "Network error: Connection refused"}
```
**Fix**: Start document server in the correct folder document-server with: (`docker-compose up -d`)

### File Not Found
```json
{"error": "File not found: /path/to/file"}
```
**Fix**: Check file path is correct

### Document Not Found
```json
{"error": "Document not found: doc_xxx"}
```
**Fix**: Run `doc-query` to find correct document ID