# Package 08: Cleanup

## Goal
Remove deprecated components and verify final structure.

## Steps

1. **Delete deprecated frontend**
   - Remove `agent-orchestrator-observability/frontend/` (replaced by unified dashboard)

2. **Delete test hooks**
   - Remove `agent-orchestrator-observability/hooks/` (functionality now in ao-* commands)

3. **Delete empty directories**
   - Remove `agent-orchestrator-observability/` (should be empty after Package 04)
   - Remove any other empty remnant directories

4. **Verify final structure**
   - Confirm structure matches [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure)

5. **Update root README.md**
   - Update paths and component names
   - Add quick start guide
   - Reference docs/ for detailed documentation

6. **Update environment variable names**
   | Old | New |
   |-----|-----|
   | `OBSERVABILITY_BACKEND_URL` | `AGENT_RUNTIME_URL` |
   | `AGENT_MANAGER_URL` | `AGENT_REGISTRY_URL` |
   | `DOCUMENT_SERVER_URL` | `CONTEXT_STORE_URL` |

7. **Final Makefile review**
   - Ensure all targets use new paths
   - Add convenience targets if missing

8. **Final docker-compose review**
   - Ensure all services use new names and paths
   - Verify network configuration

## Verification
- Full system start via docker-compose
- Full system start via Makefile
- All features work end-to-end

## References
- Target structure: See [ARCHITECTURE.md](./ARCHITECTURE.md#project-structure)
