# Deep Dive: Define — Agent Blueprints

## Title
**"Agent Blueprints"**

## Subtitle
"Describe what agents do—in plain language"

## The Correct Term
**Agent Blueprints** — The definition files that specify what an agent does, how it behaves, and what it's good at.

---

## The Metaphor: Job Description

When you hire someone, you don't write code. You write a job description:
- What's the role?
- What should they do?
- What are they responsible for?

**Agent Blueprints work the same way.** You describe what you want the agent to do in plain language. The framework handles the rest.

---

## Visual Concept

**SVG Illustration idea:** A document/notepad with text lines, transforming into or connected to a robot/agent figure.

```
┌─────────────────┐          ┌─────────────┐
│ JOB DESCRIPTION │          │             │
│ ═══════════════ │    →     │    🤖       │
│ ─────────────── │          │   Agent     │
│ ─────────────── │          │             │
│ ─────────────── │          └─────────────┘
└─────────────────┘
   Plain text              Working agent
```

**Alternative:** A person writing on a notepad, with an agent "coming to life" from the page.

---

## Key Points

1. **No code required** — Write in plain language, not programming languages
2. **Anyone can contribute** — PMs, domain experts, not just developers
3. **Fast iteration** — Change behavior by editing text, test immediately
4. **Version controlled** — Track changes like any document

---

## Why It Matters (for the boss)

| Without Blueprints | With Blueprints |
|--------------------|-----------------|
| Developer bottleneck | Anyone can define agents |
| Slow iteration | Change and test in minutes |
| Technical barrier | Business people contribute directly |

---

## One-Liner for Overview Slide

**"Describe agents in plain language—like writing a job description."**
