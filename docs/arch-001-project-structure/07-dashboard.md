# Package 07: Dashboard

## Goal
Rename frontend to dashboard.

## Source → Target
```
agent-orchestrator-frontend/ → dashboard/
```

## Steps

1. **Rename directory**
   - Rename `agent-orchestrator-frontend/` → `dashboard/`

2. **Update package.json**
   - Update name to `agent-orchestrator-dashboard`

3. **Update Makefile**
   - Change frontend target path to `dashboard/`

4. **Update docker-compose.yml**
   - Change build context to `./dashboard`
   - Rename service to `dashboard`

## Note
API URL constants were already updated in Packages 03 and 04. No further code changes needed unless there are remaining hardcoded references.

## Verification
- Dashboard builds and runs from new location
- All features work: sessions, agents, documents

## References
- Target structure: See [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure) → `/dashboard/`
- Component details: See [ARCHITECTURE.md](./ARCHITECTURE.md#dashboard-web-ui)
