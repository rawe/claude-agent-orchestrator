# Deep Dive: Connect — Capabilities

## Title
**"Capabilities"**

## Subtitle
"Plug agents into your existing systems"

## The Correct Term
**Capabilities** — The connections that give agents access to external tools and systems (Jira, databases, knowledge bases, APIs).

---

## The Metaphor: Universal Adapter

Think of USB-C: one port connects to monitors, drives, chargers, phones—anything.

**Capabilities work the same way.** They're adapters that let agents talk to your systems:
- Jira for tickets
- Confluence for documentation
- Databases for data
- Any system with an API

The agent doesn't need to know how Jira works. The capability handles the translation.

---

## Visual Concept

**SVG Illustration idea:** A central agent/hub with multiple "plug" connections radiating out to different system icons.

```
                    ┌───────┐
                    │ Jira  │
                    └───┬───┘
                        │
┌───────┐          ┌────┴────┐          ┌───────┐
│  DB   │──────────│  AGENT  │──────────│ Slack │
└───────┘          │    ●    │          └───────┘
                   └────┬────┘
                        │
                    ┌───┴───┐
                    │ APIs  │
                    └───────┘
```

**Alternative:** An adapter/plug icon with multiple prongs, each going to a different system logo.

---

## Key Points

1. **Pre-built connectors** — Common tools already supported
2. **Add without changing agents** — New capability = new power, same agent
3. **Your data stays yours** — Agents access systems, don't copy everything
4. **Extend as needed** — Build custom capabilities for proprietary systems

---

## Why It Matters (for the boss)

| Without Capabilities | With Capabilities |
|---------------------|-------------------|
| Agents work in isolation | Agents work with your tools |
| Manual data transfer | Direct system access |
| Rebuild for each integration | Add connectors, keep agents |

---

## One-Liner for Overview Slide

**"Plug into your systems—Jira, databases, any tool."**
