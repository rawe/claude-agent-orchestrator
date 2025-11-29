# Troubleshooting

## Common Errors

### Connection Refused
```json
{"error": "Network error: Connection refused"}
```
**Fix**: Start Context Store server with: `docker-compose up -d` (from project root or `servers/context-store`)

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