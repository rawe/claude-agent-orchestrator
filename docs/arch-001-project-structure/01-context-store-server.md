# Package 01: Context Store Server

## Goal
Extract document server from plugin into `/servers/context-store/`.

## Source → Target
```
plugins/document-sync/document-server/ → servers/context-store/
```

## Steps

1. **Create target directory**
   - Create `/servers/context-store/`

2. **Move server files**
   - Move `plugins/document-sync/document-server/src/` → `servers/context-store/src/`
   - Move `plugins/document-sync/document-server/pyproject.toml` → `servers/context-store/`
   - Move `plugins/document-sync/document-server/tests/` → `servers/context-store/tests/`

3. **Update server identity**
   - Update `pyproject.toml`: name = `context-store`
   - Update `main.py`: FastAPI title = "Context Store"

4. **Update plugin references**
   - Update `plugins/document-sync/skills/document-sync/commands/lib/config.py`: server URL/path if hardcoded

5. **Update Makefile**
   - Change document-server target path to `servers/context-store/`

6. **Update docker-compose.yml**
   - Change build context to `./servers/context-store`
   - Rename service to `context-store`

7. **Delete old location**
   - Remove `plugins/document-sync/document-server/` (now empty)

## Verification
- Start Context Store server from new location
- Run doc-* commands → should work unchanged
- Dashboard document features → should work unchanged

## References
- Target structure: See [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure) → `/servers/context-store/`
- Component details: See [ARCHITECTURE.md](./ARCHITECTURE.md#context-store)
