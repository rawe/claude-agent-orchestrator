---
description: Break down a design document into phased implementation prompts with handover reports
argument-hint: <path-to-design-document>
---

# Implementation Phases Generator

Generate phased implementation prompts from a design document.

## Variables

```
DESIGN_DOCUMENT_PATH = $ARGUMENTS
```

## Instructions

You are helping the user break down a design document into implementation phases, then creating reusable prompts for each phase.

### Step 1: Read and Understand

Read the design document at: `DESIGN_DOCUMENT_PATH`

Summarize:
- What is being built
- Key components/sections
- Implementation tasks (if listed)

### Step 2: Discuss Phase Division

Propose how to divide the implementation into **3-5 sessions**. Present as a table:

| Session | Focus | Deliverable |
|---------|-------|-------------|
| 1 | ... | ... |
| ... | ... | ... |

Ask the user: "Does this division make sense? Would you like to adjust?"

Wait for user approval before proceeding.

### Step 3: Create Implementation Folder

Once phases are approved, create a subfolder next to the design document:

```
[design-doc-folder]/[design-doc-name]-implementation/
```

Example: If design doc is `docs/design/my-feature/my-feature.md`, create `docs/design/my-feature/my-feature-implementation/`

### Step 4: Generate Phase Prompts

Create one prompt file per phase in the implementation folder:

**Naming:** `phase-[N]-prompt.md` (e.g., `phase-1-prompt.md`)

**Structure for Phase 1:**

```markdown
# Phase 1: [Focus Title]

## Context

Read the design document: `[relative path to design doc]`

## Objective

[One sentence describing what this phase delivers]

## Deliverable

[Bullet list of concrete outputs]

## Instructions

1. Enter plan mode to create an implementation plan
2. Reference the design document sections relevant to this phase
3. Implement the planned changes
4. Create a report file when done

## Report

When complete, create: `[implementation-folder]/phase-1-report.md`

Report format:
```
# Phase 1 Report: [Focus Title]

## Status: COMPLETE | PARTIAL | BLOCKED

## Completed
- [What was done]

## Files Changed
- `path/to/file.ts` - [brief description]

## Not Completed (if any)
- [What remains, why]

## Notes for Next Phase
- [Anything the next session needs to know]
```
```

**Structure for Phase 2+ (follow-up phases):**

```markdown
# Phase [N]: [Focus Title]

## Context

Design document: `[relative path to design doc]`
Previous phase report: `[relative path to phase-(N-1)-report.md]`

Read both files to understand what was done and what remains.

## Objective

[One sentence describing what this phase delivers]

## Deliverable

[Bullet list of concrete outputs]

## Instructions

1. Read the previous phase report to understand current state
2. Enter plan mode to create an implementation plan
3. Reference the design document sections relevant to this phase
4. Implement the planned changes
5. Create a report file when done

## Report

When complete, create: `[implementation-folder]/phase-[N]-report.md`

[Same report format as above]
```

### Step 5: Create Index

Create a `README.md` in the implementation folder:

```markdown
# [Feature Name] - Implementation Phases

Design document: `[relative path]`

## Phases

| Phase | Focus | Prompt | Report |
|-------|-------|--------|--------|
| 1 | [Focus] | [phase-1-prompt.md](phase-1-prompt.md) | phase-1-report.md |
| 2 | [Focus] | [phase-2-prompt.md](phase-2-prompt.md) | phase-2-report.md |
| ... | ... | ... | ... |

## Progress

- [ ] Phase 1: [Focus]
- [ ] Phase 2: [Focus]
- ...
```

### Step 6: Summary

Tell the user:
- What folder was created
- How many phase prompts were generated
- How to use them (copy-paste prompt content to new AI session)
