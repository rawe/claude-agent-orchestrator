# Open Architectural Questions

See [README.md](./README.md) for format documentation and how to add items.

---

## Context Store

### CONTEXT-001: Document Lifetime Semantics

**Component:** Context Store
**Tags:** #lifecycle #data-model #fundamental
**Status:** open
**Created:** 2026-01-15

#### Question

What is the intended lifetime of documents in the Context Store? Are they temporal working artifacts or persistent knowledge?

#### Context

The Context Store was **originally designed for temporal use** - sharing working artifacts between agents during a session tree (workflow). Documents would be created during agent execution and serve as intermediate results or shared context.

However, there's now interest in **also supporting persistent documents** for additional use cases:

1. **Human access via Dashboard UI**: Users want to view and manage documents directly through the web interface, without going through AI agents. This requires documents to persist beyond agent sessions.

2. **Reference documentation**: Architecture docs, specifications, and other reference material that should remain accessible across unrelated sessions.

3. **Accumulated knowledge**: Insights or artifacts that agents produce which have value beyond the immediate workflow.

The current design documents focus on **access control** (who can see which documents) but don't define **document lifecycle** (how long documents live).

This ambiguity makes it difficult to move forward architecturally:

1. **Access control vs lifecycle**: Are visibility boundaries also lifetime boundaries? Or are they independent concerns?

2. **Storage strategy**: Do we need retention policies and cleanup jobs, or is everything permanent until explicitly deleted?

3. **Mixed use cases**: The original temporal purpose and new persistent use cases need to coexist clearly.

#### Options (if known)

1. **Temporal Only**
   - All documents are working artifacts, cleaned up after the workflow completes
   - Pros: Clear lifecycle, no unbounded growth, simpler mental model
   - Cons: Can't build persistent knowledge, no human access to documents after workflow ends, loses accumulated insights

2. **Hybrid (Explicit Lifecycle Marker)**
   - Documents have an explicit `lifecycle` attribute: `temporal` or `persistent`
   - Temporal documents are cleaned up automatically (e.g., when workflow ends)
   - Persistent documents remain until explicitly deleted
   - Pros: Supports both use cases explicitly, clear intent at creation time
   - Cons: More complexity, need cleanup infrastructure, creators must decide lifecycle upfront

3. **Hybrid (Implicit via Visibility Scope)**
   - Documents scoped to a specific workflow are temporal (cleaned up when workflow ends)
   - Documents visible across workflows (namespace-wide) are persistent
   - Pros: No new field needed, leverages existing access control model
   - Cons: Implicit behavior may be confusing, ties visibility to lifetime (may not always be desired)

#### Decision

*To be determined.*

---

### CONTEXT-002: Context Store Scoping Implementation Strategy

**Component:** Context Store, Agent Coordinator
**Tags:** #api-design #security #cross-cutting
**Status:** open
**Created:** 2026-01-15

#### Question

Should Context Store scoping use explicit API parameters, token-based authentication, or both? How do these two design patterns interact?

#### Context

Two design documents describe different approaches to implementing data scoping in the Context Store:

1. **Explicit API Parameters** (`docs/design/context-store-scoping/context-store-scoping.md`):
   - Namespace in URL path: `/namespaces/{namespace}/documents`
   - Scope filters as query/body parameters
   - MCP server receives context from executor via env vars
   - Context Store server API is explicit (no header magic)

2. **Token-Based Scoping** (`docs/design/external-service-auth/`):
   - Coordinator issues signed JWT tokens with embedded scope
   - Services extract namespace and scope_filters from token
   - Single token for multiple services
   - MCP server receives token from executor, passes to services

The README states these "can be implemented independently" but doesn't clarify:
- Which should be implemented first?
- Are both needed, or is one sufficient?
- How do they compose if both are implemented?

#### Options (if known)

1. **Explicit API Only**
   - Simpler to implement
   - Relies on MCP server configuration to enforce scope
   - Pros: Straightforward, works without token infrastructure
   - Cons: No cryptographic proof of authorization

2. **Token-Based Only**
   - More secure (cryptographic verification)
   - Scope embedded in signed token
   - Pros: Strong security, audit trail via token subject
   - Cons: Requires key management, token refresh logic

3. **Both (Layered)**
   - Token provides authorization proof
   - Explicit parameters enable flexibility
   - Pros: Defense in depth
   - Cons: Complexity, potential inconsistency

#### Decision

*To be determined.*

---

## Agent Coordinator

### COORDINATOR-001: Parent-Child Session Deletion Strategy

**Component:** Agent Coordinator
**Tags:** #data-model #lifecycle #breaking
**Status:** open
**Created:** 2026-01-15

#### Question

What should happen to child sessions when a parent session is deleted?

#### Context

The current database schema uses `ON DELETE SET NULL` for the `parent_session_id` foreign key constraint:

```sql
parent_session_id TEXT REFERENCES sessions(session_id) ON DELETE SET NULL
```

This creates problems documented in `docs/refactoring/002-parent-child-session-deletion-strategy.md`:

- **Silent Orphaning**: Child sessions survive with `parent_session_id = NULL`
- **Lost Hierarchy**: Parent-child relationships are permanently broken
- **Callback Failures**: Pending callbacks to deleted parents fail
- **Data Accumulation**: Database fills with orphaned records
- **UI Confusion**: Dashboard displays orphaned sessions without context

ADR-003, ADR-005, and ADR-010 establish that children exist to serve their parent's orchestration goals, suggesting CASCADE DELETE would align with architectural intent.

#### Options (if known)

1. **CASCADE DELETE**
   - Delete children when parent is deleted
   - Pros: Clean, matches architectural intent, no orphans
   - Cons: Data loss risk if user accidentally deletes parent

2. **SET NULL + Cleanup** (Current + Enhancement)
   - Keep current behavior, add cleanup logic
   - Pros: More control, explicit cleanup
   - Cons: Complex, risk of orphans if cleanup fails

3. **Prevent Deletion**
   - Block parent deletion if children exist
   - Pros: Safest, no unintended deletions
   - Cons: Tedious for deep hierarchies

#### Decision

*To be determined. See `docs/refactoring/002-parent-child-session-deletion-strategy.md` for detailed analysis.*

---

### COORDINATOR-002: Structured Output Schema Enforcement

**Component:** Agent Coordinator, Agent Runner
**Tags:** #api-design #data-model #fundamental
**Status:** open
**Created:** 2026-01-15

#### Question

How should the framework enforce structured output from agent runs? Should this be implemented at the Coordinator level (prompt injection + validation loop) or rely on native AI API features?

#### Context

The `docs/design/structured-output-schema-enforcement.md` document describes a comprehensive design for enforcing JSON Schema-compliant outputs from agents. Key features include:

- Callers specify `output_schema` when creating runs
- Coordinator enriches prompt with schema requirements
- Validation loop retries on schema violations
- Named schema registry for reusable schemas
- Framework-level enforcement (API-independent)

The design is marked "Draft" and implementation status shows "Design" in the unified task model overview. No code exists for:
- `SchemaEnforcer` service
- `output_schema` field in run model
- Schema registry endpoints (`/schemas`)
- Retry mechanism for schema violations

This blocks type-safe orchestration where parent agents need predictable outputs from children.

#### Options (if known)

1. **Framework-Level Enforcement** (as designed)
   - Prompt injection + validation loop
   - Pros: API-independent, works with any executor
   - Cons: Additional latency from retries, implementation effort

2. **Native AI API Features**
   - Use Claude's structured output capabilities
   - Pros: Lower latency, higher reliability
   - Cons: Framework lock-in, not all models support it

3. **Hybrid Approach**
   - Use native features when available, fall back to framework enforcement
   - Pros: Best of both worlds
   - Cons: Complex implementation, inconsistent behavior

#### Decision

*To be determined.*

---

### COORDINATOR-003: Horizontal Scaling SSE Strategy

**Component:** Agent Coordinator, Dashboard
**Tags:** #scalability #cross-cutting
**Status:** open
**Created:** 2026-01-15

#### Question

How should SSE (Server-Sent Events) be broadcast across multiple Coordinator instances for horizontal scaling?

#### Context

From `docs/production-readiness/PR-004-coordinator-scaling.md`:

SSE connections are managed in-memory by each Coordinator instance. When events are created on instance A, they must reach clients connected to instance B. Current single-instance design doesn't address this.

This blocks horizontal scaling and zero-downtime deployments.

Prerequisites: PR-001 (PostgreSQL migration), PR-002 (Run queue simplification).

#### Options (if known)

1. **Redis Pub/Sub**
   - Each instance subscribes to Redis channels
   - Events published to Redis, broadcast to local connections
   - Pros: Low latency, proven pattern
   - Cons: Additional infrastructure (Redis)

2. **Sticky Sessions**
   - Load balancer routes client to same instance
   - Pros: Simple, no cross-instance messaging
   - Cons: Uneven load, instance failure disrupts clients

3. **Database Polling**
   - Instances poll events table for new events
   - Pros: Simple, no additional infrastructure
   - Cons: Added latency, database load

#### Decision

*To be determined. Defer until load requires horizontal scaling.*

---

## Agent Runner

### RUNNER-001: MCP Proxy Configuration and Routing

**Component:** Agent Runner
**Tags:** #api-design #cross-cutting
**Status:** open
**Created:** 2026-01-15

#### Question

How should the Agent Runner determine where to proxy external MCP server requests?

#### Context

From `docs/architecture/mcp-runner-integration.md` (Phase 2b - MCP Proxy for External MCP Servers):

The architecture proposes that Runner proxies ALL MCP traffic, not just the orchestrator MCP. This provides:
- Single interception point for all MCP calls
- Future auth hook for external MCPs
- Executor isolation
- Centralized logging/monitoring

Open questions identified in the document:
1. How does Runner know where to proxy each MCP? (config file? Coordinator registry?)
2. Should proxy support both HTTP and stdio MCP backends?

The `${AGENT_ORCHESTRATOR_MCP_URL}` placeholder is recognized, but no pattern exists for other MCPs.

#### Options (if known)

1. **Configuration File**
   - Runner config maps MCP names to URLs
   - Pros: Simple, explicit
   - Cons: Duplicates blueprint info, manual sync

2. **Blueprint Resolution**
   - Extract original URLs from blueprint, store for routing
   - Pros: Single source of truth
   - Cons: More complex, blueprint must have original URLs

3. **Coordinator Registry**
   - Register MCP endpoints with Coordinator
   - Pros: Centralized management
   - Cons: Additional API, Coordinator complexity

#### Decision

*To be determined.*

---

### RUNNER-002: External MCP Server Authentication

**Component:** Agent Runner
**Tags:** #security #cross-cutting
**Status:** open
**Created:** 2026-01-15

#### Question

How should the Agent Runner authenticate with external MCP servers when proxying requests?

#### Context

From `docs/architecture/mcp-runner-integration.md`:

> **Open:** Authentication for external MCP servers
> - How to authenticate with external MCPs (Atlassian, etc.) when proxying?
> - Options: Runner holds credentials, per-MCP M2M, credential injection
> - Decision deferred

Current orchestrator MCP uses Runner's existing Auth0 M2M credentials. External MCPs (Context Store, Atlassian, Neo4j) may have different auth mechanisms:
- Some may use the external service token architecture (JWT from Coordinator)
- Some may have their own API keys or OAuth flows
- Some may be unauthenticated (internal services)

#### Options (if known)

1. **Runner Holds Credentials**
   - Configure credentials in runner startup
   - Pros: Simple, centralized
   - Cons: Security risk, secret management complexity

2. **External Service Token** (as designed)
   - Use Coordinator-signed JWT for all services
   - Pros: Uniform, cryptographic proof
   - Cons: All services must implement token validation

3. **Per-MCP Configuration**
   - Each MCP definition includes auth config
   - Pros: Flexible, supports heterogeneous systems
   - Cons: Complex configuration, credential distribution

4. **Credential Injection from Executor**
   - Executor provides credentials per-request
   - Pros: Dynamic, no runner config
   - Cons: Credentials exposed to executor

#### Decision

*To be determined.*

---
