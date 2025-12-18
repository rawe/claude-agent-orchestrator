# Configuration

## Environment Variables

- `DOC_SYNC_HOST` - Server hostname (default: `localhost`)
- `DOC_SYNC_PORT` - Server port (default: `8766`)
- `DOC_SYNC_SCHEME` - http or https (default: `http`)

## Example (only when overriding defaults is needed!!!)

```bash
DOC_SYNC_HOST=example.com DOC_SYNC_PORT=443 DOC_SYNC_SCHEME=https \
  uv run --script commands/doc-push file.txt
```
