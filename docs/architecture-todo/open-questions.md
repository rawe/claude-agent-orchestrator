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
