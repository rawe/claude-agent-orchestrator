# Refactoring

This folder contains documented refactoring proposals, consistency fixes, and technical improvements that have been identified but are not immediately prioritized.

## Purpose

Unlike feature requests or new functionality, items here focus on:

- **Consistency** - Aligning naming conventions, patterns, and terminology across the codebase
- **Refactoring** - Improving code structure without changing behavior
- **Technical Debt** - Addressing accumulated shortcuts or workarounds
- **Documentation Alignment** - Ensuring docs match implementation

## Item Format

Each item follows a standard format:

```
# [Title]

**Status:** Open | In Progress | Completed
**Priority:** Low | Medium | High
**Created:** YYYY-MM-DD

## Context
[Why this item exists, background information]

## Problem
[What is inconsistent, unclear, or needs improvement]

## Proposed Solution
[How to address the problem]

## Affected Files
[List of files that need changes]

## Acceptance Criteria
[How to verify the work is complete]
```

## Current Items

| ID | Title | Status | Priority |
|----|-------|--------|----------|
| 001 | [Event Type Naming Consistency](./001-event-type-naming-consistency.md) | Open | Medium |

## When to Add Items

Add items here when you identify:

1. Naming inconsistencies between code and documentation
2. Patterns that should be unified across components
3. Technical debt acknowledged in TODO comments
4. Documentation that has drifted from implementation

## When to Implement

Items should be tackled when:

1. Working in a related area (opportunistic cleanup)
2. The inconsistency is causing confusion or bugs
3. During dedicated maintenance windows
4. Before major releases to reduce technical debt
