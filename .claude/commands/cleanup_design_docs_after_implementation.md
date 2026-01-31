---
description: Convert design docs to feature docs after implementation, extracting ADRs
argument-hint: <design-docs-path>
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Task
  - AskUserQuestion
---

# Cleanup Design Docs After Implementation

Convert design documentation into status quo documentation after a feature has been implemented. This workflow extracts architectural decisions into ADRs, creates user-facing feature documentation, and updates related documentation.

## Arguments

- `$ARGUMENTS[0]` - Path to design docs (file or folder, e.g., `docs/design/mcp-server-registry`)

## Key Principles

1. **Feature docs describe status quo** - What IS, not how we got here or what might come
2. **ADRs document decisions** - WHY decisions were made, understandable without reading the feature doc
3. **No implementation code** - Exception: data model definitions (classes, enums, schemas) when more concise
4. **ADRs never reference feature docs** - But feature docs MAY reference ADRs
5. **Concise and understandable** - No filler words, no verbosity, but must be followable

## Documentation Locations

Different content belongs in different places:

| Content Type | Location | Purpose |
|--------------|----------|---------|
| Architectural decisions | `docs/adr/ADR-NNN-*.md` | WHY decisions were made |
| Feature documentation | `docs/features/*.md` | WHAT the feature does and HOW to use it |
| API endpoint details | `docs/components/{component}/API.md` | Full request/response specs |
| Setup/usage guidance | `docs/guides/*.md` | Step-by-step guides |
| Feature index | `docs/features/README.md` | List of all features |
| ADR index | `docs/adr/README.md` | List of all ADRs |

---

## Feature Document Structure

A feature document follows this structure. Sections marked **required** should always be present; **conditional** sections depend on the feature.

### Header (Required)

```markdown
# Feature Name

**Status:** Implemented | Draft | Active
**Affects:** Agent Coordinator, Agent Runner, Dashboard, ...
```

- **Status**: `Implemented` (complete), `Draft` (WIP), `Active` (live, evolving)
- **Affects**: List main components this feature touches

### Overview (Required)

Brief description of what the feature does. Start directly with the content, no "This document describes...". Optionally include **Key Characteristics** if the feature has distinct properties.

### Motivation (Required)

Explain the problem and solution. Use this structure:

```markdown
## Motivation

### The Problem

[Concise description of what was wrong/missing]

### The Solution

[Brief description of how this feature solves it]
```

Format (tables, bullets, prose) depends on the feature. Keep it concise.

### Key Concepts (Required if new concepts exist)

Define terminology and core abstractions. Should NOT contain how-tos. Use tables for structured comparisons, bold terms on first definition.

### Configuration (Conditional: when feature is configurable)

Describe WHAT is configurable and reference data models. Include:
- WHERE configuration lives (filesystem, database, inline)
- Configuration options with descriptions
- Enumeration values with explanations
- Reference to Data Model section for detailed structures

### Data Model (Conditional: when significant data structures exist)

Describe actual data structures (enums, schemas, state transitions).

**Code is acceptable here** for data model definitions (classes, enums, schemas) when it's more concise and unambiguous. Only the model definition itself, no implementation code. Prefer JSON/JSON Schema when possible.

### API (Conditional: when feature adds/uses API endpoints)

Brief overview only - table of endpoints with purpose. Must specify WHICH API (Coordinator, Runner Gateway, Context Store, etc.).

```markdown
## API

This feature uses the following Agent Coordinator endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/example` | GET | Brief description |

See [Agent Coordinator API Reference](../components/agent-coordinator/API.md) for full details.
```

**Important:** Full endpoint details must be documented in the API reference, not here.

### Architecture (Conditional: when multi-component)

Only when feature involves multiple components. Must explain:
- Component relationships (ASCII diagrams for simple, Mermaid for complex)
- Handovers between components
- Data models for transfer

### Examples (Optional)

Use-case driven examples. Not too long, must be explained. Show the scenario, then the configuration.

### Execution Flow (Conditional: for async/multi-step processes)

Show runtime behavior. Format depends on complexity:
- Simple overview → ASCII
- Complex flows → Mermaid
- Specialized diagrams (sequence, state) → Mermaid

### Error Handling & Edge Cases (Optional)

Document error behavior AND non-obvious edge cases. Focus on:
- Corner cases that are deliberately handled or NOT handled
- Race conditions, failure modes
- Recovery behavior

API error responses belong in API reference, not here.

### Feature-Specific Sections (As needed)

Some features need specific sections:
- **CLI Usage** - when feature has CLI interface
- **Dashboard Integration** - when feature has UI
- Other sections as the feature requires

### References (Recommended)

Links to related ADRs, other feature docs, architecture docs.

```markdown
## References

- [ADR-0XX: Decision Title](../adr/ADR-0XX-decision-title.md)
- [Related Feature](./related-feature.md)
```

### What to EXCLUDE from Feature Docs

- Implementation code (except data model definitions)
- Migration paths (feature docs describe status quo)
- Backward compatibility notes
- Future considerations/enhancements
- Known issues/limitations
- Internal implementation details
- Test code or test output

---

## Workflow Steps

### Step 1: Analyze Design Documents

Read and understand all design documents at the specified path:

1. Read the design docs README (if exists) for overview
2. Read all design document files (`.md` files)
3. Read any implementation reports (`*-report.md` files)
4. Identify key concepts, decisions, and implemented functionality

**Source path:** `$ARGUMENTS[0]`

### Step 2: Extract Architectural Decision Records (ADRs)

Identify potential ADRs from the design docs. Look for:

- Major architectural decisions with explicit alternatives considered
- Decisions that affect multiple components or have long-term implications
- Trade-offs that were deliberately made
- "Key Design Decisions" sections in design docs

For each potential ADR:

1. Present the decision to the user with context
2. Ask if it should become an ADR using AskUserQuestion
3. If approved, create the ADR file in `docs/adr/` following the format:
   - Status, Date, Decision Makers
   - Context (what prompted the decision)
   - Decision (what was decided)
   - Rationale (why, what alternatives were considered)
   - Consequences (positive, negative, neutral)
4. Add the new ADR to `docs/adr/README.md` index table

**ADR naming:** `ADR-NNN-short-title.md` where NNN is the next available number.

**Important:** ADRs document decisions, not features. They should be understandable without reading the feature doc.

### Step 3: Create Feature Documentation

Create feature documentation in `docs/features/` following the structure defined above.

**Process:**

1. Draft each section, discussing with user via AskUserQuestion
2. For each section, identify if content belongs elsewhere:
   - Key design decisions → already extracted as ADRs in Step 2
   - Detailed API specs → will update API reference in Step 4
   - Substantial guidance → will create guide in Step 4
3. Present complete draft to user for approval
4. If approved, create the file in `docs/features/`
5. Add the feature to `docs/features/README.md` index table

### Step 4: Update Related Documentation

Based on what was identified during feature doc creation:

**API Reference** (if feature adds/changes endpoints):
- Update `docs/components/{component}/API.md` with full endpoint details
- Include request/response examples, error responses

**Guides** (if substantial guidance needed):
- Create guide in `docs/guides/` if step-by-step instructions are needed
- Link from feature doc

**Other docs that may need updates:**
- `docs/components/` - Component-specific technical details
- `docs/reference/` - Schemas, syntax references
- `docs/architecture/` - Cross-cutting architectural concerns
- Related feature docs - Cross-references

For each update:
1. Present the suggested change to the user
2. Ask for approval via AskUserQuestion
3. If approved, make the edit

### Step 5: Add Implementation References (Optional)

Review recent commits and consider adding brief doc references in tricky implementation areas.

**Use sparingly** - Only where:
- Implementation is non-obvious
- Understanding requires knowing the feature design
- Future maintainers would benefit

For each potential reference:
1. Present location and suggested reference to user
2. Ask for approval via AskUserQuestion
3. If approved, add reference (e.g., `# See docs/features/feature-name.md`)

### Step 6: Summary

Provide a summary of all changes made:

- ADRs created (with links)
- Feature docs created (with links)
- API reference updates
- Guides created
- Other docs updated
- Implementation references added (if any)

## Example Usage

```
/cleanup_design_docs_after_implementation docs/design/mcp-server-registry
```

This will:

1. Read all docs in `docs/design/mcp-server-registry/`
2. Extract potential ADRs (discuss with user)
3. Create feature doc `docs/features/mcp-server-registry.md` (section by section)
4. Update `docs/components/agent-coordinator/API.md` if new endpoints
5. Update indexes in `docs/adr/README.md` and `docs/features/README.md`
6. Optionally add implementation references

## Notes

- Always get user approval before creating/modifying files
- Feature docs describe the status quo, not history or future plans
- ADRs are for decisions that affect the architecture long-term
- Keep design docs in place as historical record
- When in doubt about where content belongs, ask the user
