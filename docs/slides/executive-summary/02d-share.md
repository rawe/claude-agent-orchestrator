# Deep Dive: Share — Context Store

## Title
**"Context Store"**

## Subtitle
"Share context efficiently between agents"

## The Correct Term
**Context Store** — A shared storage system where agents can store and retrieve documents, data, and context. Agents pass references, not full content—keeping context windows small and costs low.

---

## The Metaphor: Shared Notebook

Imagine a team working on a project. Instead of emailing documents back and forth:
- Everyone writes in a shared notebook
- Reference page numbers, don't copy pages
- One source of truth
- No version confusion

**Context Store works the same way.** Agents write results to a shared location. Other agents read by reference—no wasteful copying.

---

## Visual Concept

**SVG Illustration idea:** A central "notebook" or "folder" with multiple agents pointing to it / reading from it.

```
      Agent A                    Agent B
         │                          │
         │ writes                   │ reads
         ▼                          ▼
    ┌─────────────────────────────────┐
    │         CONTEXT STORE           │
    │  ┌─────┐ ┌─────┐ ┌─────┐       │
    │  │Doc 1│ │Doc 2│ │Doc 3│       │
    │  └─────┘ └─────┘ └─────┘       │
    │                                 │
    │   "Reference, don't copy"       │
    └─────────────────────────────────┘
                    │
                    │ reads
                    ▼
                Agent C
```

**Alternative:** A library metaphor—agents check out books by ID, not by carrying the whole library.

---

## Key Points

1. **Efficient handover** — Pass references, not full documents
2. **Reduced costs** — Smaller context windows = fewer tokens = lower bills
3. **No duplication** — One source of truth for shared knowledge
4. **Clean coordination** — Agent A produces, Agent B consumes, no copy-paste

---

## Why It Matters (for the boss)

| Without Context Store | With Context Store |
|----------------------|-------------------|
| Copy-paste between agents | Reference by ID |
| Large context = high cost | Small context = low cost |
| Version confusion | Single source of truth |
| Manual handover | Automatic sharing |

---

## One-Liner for Overview Slide

**"Efficient knowledge handover—no wasted tokens, no lost context."**
