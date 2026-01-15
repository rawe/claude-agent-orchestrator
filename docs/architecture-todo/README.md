# Architecture TODO

This folder tracks open architectural questions and decisions that need to be tackled.

## Purpose

Capture architectural uncertainties, open questions, and decisions that impact the system design. Items here represent things that need clarification or decision before moving forward with implementation.

## Files

| File | Description |
|------|-------------|
| `open-questions.md` | All open architectural questions and decisions |

## Item Format

Each item in `open-questions.md` follows this structure:

```markdown
### COMPONENT-NNN: Short Title

**Component:** Component name(s)
**Tags:** #tag1 #tag2
**Status:** open | in-discussion | decided
**Created:** YYYY-MM-DD

#### Question

What is the architectural question or uncertainty?

#### Context

Why does this matter? What does it affect? What triggered this question?

#### Options (if known)

1. **Option A**: Description
   - Pros: ...
   - Cons: ...

2. **Option B**: Description
   - Pros: ...
   - Cons: ...

#### Decision (when decided)

The chosen approach and rationale.

---
```

## Status Definitions

| Status | Meaning |
|--------|---------|
| `open` | Question identified, not yet discussed |
| `in-discussion` | Actively being explored or debated |
| `decided` | Decision made, documented in "Decision" section |

## Tag Taxonomy

Use these tags consistently. Add new tags here when needed.

### Concern Tags
| Tag | Meaning |
|-----|---------|
| `#lifecycle` | Object lifetime, cleanup, retention |
| `#data-model` | Schema, storage structure, relationships |
| `#api-design` | API contracts, endpoints, protocols |
| `#security` | Authentication, authorization, access control |
| `#scalability` | Performance, capacity, growth considerations |
| `#ux` | User/developer experience implications |

### Scope Tags
| Tag | Meaning |
|-----|---------|
| `#fundamental` | Core assumption or foundational decision |
| `#cross-cutting` | Affects multiple components |
| `#breaking` | Would require breaking changes if changed later |

## Components

Valid component names (update as system evolves):

- `Context Store` - Document storage and sharing
- `Agent Coordinator` - Session management, agent runs, runner registry
- `Agent Runner` - Agent execution, polling, executor management
- `Dashboard` - Web UI for monitoring
- `MCP Servers` - Model Context Protocol integrations
- `Plugins` - Claude Code skills (orchestrator, context-store)

## How to Add Items

1. Open `open-questions.md`
2. Find the next available ID for the component (e.g., `CONTEXT-002`)
3. Copy the template from "Item Format" above
4. Fill in all sections (leave "Decision" empty for new items)
5. Set status to `open`

## How to Resolve Items

When a decision is made:
1. Update status to `decided`
2. Fill in the "Decision" section with the chosen approach and rationale
3. Optionally link to any design docs or ADRs created as a result
