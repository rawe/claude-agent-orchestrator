# Post-Migration Cleanup

Tasks to complete after the Session Storage Migration feature is fully deployed and stable.

## Priority 1: Update Reference Documentation

### `plugins/agent-orchestrator/skills/agent-orchestrator/references/ENV_VARS.md`

**Current state:** Documents deprecated environment variables:
- `AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED`
- `AGENT_ORCHESTRATOR_OBSERVABILITY_URL`

**Action:**
1. Remove the "Observability Configuration" section (lines 86-136)
2. Add new "Session Manager Configuration" section documenting:
   - `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` (required, default: `http://127.0.0.1:8765`)
3. Update the quick reference table to remove old vars and add new one
4. Update "Pattern 2: Project-Specific with Observability" example to use new var name

### `plugins/agent-orchestrator/skills/agent-orchestrator/references/AGENT-ORCHESTRATOR.md`

**Action:** Review and update any "Observability" section to reference "Session Manager" instead.

## Priority 2: Update Configuration Files

### `plugins/agent-orchestrator/mcp-server/.mcp-agent-orchestrator.json`

**Current state:**
```json
"AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED": "true"
```

**Action:**
1. Remove `AGENT_ORCHESTRATOR_OBSERVABILITY_ENABLED`
2. Add `AGENT_ORCHESTRATOR_SESSION_MANAGER_URL` if needed (or rely on default)

## Priority 3: Clean Up Legacy Documentation

### `agent-orchestrator-observability/docs/`

These files document the old hook-based observability system that has been replaced:

| File | Action |
|------|--------|
| `USAGE.md` | Update to document Session Manager API usage |
| `HOOKS_SETUP.md` | Delete or mark as deprecated (hooks no longer required for session tracking) |
| `hooks.example.json` | Delete (hooks are internal to claude_client.py now) |
| `OBSERVABILITY_ARCHITECTURE_DRAFT.md` | Archive or delete (superseded by session manager) |

## Priority 4: Backend API Cleanup

### Remove Deprecated Endpoints from `agent-orchestrator-observability/backend/main.py`

| Endpoint | Status | Action |
|----------|--------|--------|
| `POST /events` | Deprecated | Remove after confirming no clients use it |
| `GET /events/{session_id}` | Deprecated | Remove (use `GET /sessions/{id}/events`) |
| `PATCH /sessions/{id}/metadata` | Deprecated | Remove (use `PATCH /sessions/{id}`) |

**Before removing:** Verify no external systems depend on these endpoints.

## Priority 5: Infrastructure Updates (Optional)

### `docker-compose.yml`

**Current state:** Uses old naming:
- `VITE_OBSERVABILITY_BACKEND_URL`
- Comments reference "OBSERVABILITY BACKEND/FRONTEND"

**Action:**
1. Rename `VITE_OBSERVABILITY_BACKEND_URL` to `VITE_SESSION_MANAGER_URL`
2. Update comments to reference "Session Manager"
3. Update frontend to use new env var name

**Note:** This is a breaking change for anyone using docker-compose. Consider doing this as part of a major version bump.

## Verification Checklist

After cleanup, verify:

- [ ] `ao-new` creates sessions successfully
- [ ] `ao-resume` resumes sessions successfully
- [ ] `ao-status` returns correct status
- [ ] `ao-get-result` returns session results
- [ ] `ao-list-sessions` shows all sessions
- [ ] `ao-clean` removes sessions
- [ ] Frontend displays sessions in real-time
- [ ] WebSocket updates work correctly
- [ ] No "observability" references in command code or client libraries

## Notes

- The folder `agent-orchestrator-observability` can be renamed to `agent-session-manager` in a future major version
- File backup functionality (`FILE_BACKUP_ENABLED`) should be kept for disaster recovery
- The unified frontend in `agent-orchestrator-frontend` is the primary UI going forward
