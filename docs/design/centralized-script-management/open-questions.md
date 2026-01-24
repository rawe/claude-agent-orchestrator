# Open Questions

**Status:** Active
**Last Updated:** 2025-01-24

---

## Phase 1 Questions

### Script Execution Environment

| Question | Context |
|----------|---------|
| Should UV scripts run with `--isolated`? | Dependency isolation vs. caching benefits |

### Security

| Question | Context |
|----------|---------|
| Should there be script validation before storage? | Prevent malicious or broken scripts |
| Is sandboxing needed for script execution? | Scripts run with runner's permissions |
| What permissions model for script creation? | Who can create/edit scripts? |

### Versioning

| Question | Context |
|----------|---------|
| Store version history or just current? | Storage vs. audit trail tradeoff |
| Support rollback to previous version? | Recovery from bad deployments |

### Migration

| Question | Context |
|----------|---------|
| How to handle existing runner-registered agents? | Backward compatibility |
| Auto-import legacy agents? | Migration path |

---

## Phase 2 Questions

See [Phase 2 Document](./phase-2-scripts-as-capabilities.md) for detailed open questions about:
- Script distribution to autonomous runners
- Execution mechanism (skill injection)
- Reliability and observability
- Security implications

---

## Resolved

| Question | Decision | Reference |
|----------|----------|-----------|
| How are scripts distributed? | Long-poll sync commands | [Phase 1](./phase-1-scripts-and-procedural-agents.md#sync-mechanism) |
| How do autonomous agents call scripts? | Via orchestrator MCP | [Phase 1](./phase-1-scripts-and-procedural-agents.md#execution-flow) |
| How to specify interpreter? | Via demand tags | [Phase 1](./phase-1-scripts-and-procedural-agents.md#script-model-scriptjson) |
| Selective deployment to runners? | Yes, Coordinator decides | [Phase 1](./phase-1-scripts-and-procedural-agents.md#when-sync-occurs) |
| Working directory for script execution? | Project dir (shared between runners) | [Phase 1](./phase-1-scripts-and-procedural-agents.md#deployment-shared-project-directory-for-file-access) |
