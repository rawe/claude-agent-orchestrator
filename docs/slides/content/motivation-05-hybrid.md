---
id: motivation-hybrid
title: "Hybrid Execution"
subtitle: "Bridging AI and programs"
section: motivation
status: next-priority
---

## Key Message

AI agents are powerful but slow and unpredictable. Traditional programs are fast and reliable but can't reason. Why choose? Use both - as equals.

**The problem it solves:** There's a gap between the AI world (prompts, natural language) and the program world (structured input/output). No clean way to combine them.

**The solution:** Treat AI agents and deterministic agents as peers. Both can be orchestrated, both can call each other.

## Diagram Description

**Visual: Two Worlds Connected**

Show two sides with a bridge:

**Left Side: "AI Agents"**
- Boxes labeled "Research Agent", "Analysis Agent"
- Icon: brain or sparkle
- Characteristics listed below: "Reasoning, Flexible, Natural language"

**Right Side: "Deterministic Agents"**
- Boxes labeled "Crawler", "Indexer", "Database"
- Icon: gear or code brackets
- Characteristics: "Fast, Reliable, Structured I/O"

**Center: "Schema Bridge"**
- A connecting element between both sides
- Bidirectional arrows
- Shows: "Prompt ↔ Structured Data"

Both sides at the SAME LEVEL - neither is subordinate.

## Why Deterministic Agents?

- **Faster:** No LLM inference overhead
- **Reliable:** Same input = same output
- **Efficient:** Optimized for specific tasks

## Example

A Research Agent needs website data. Instead of crawling itself (slow, error-prone), it calls a Crawler agent (fast, reliable) that stores results in a database. The Research Agent then queries the structured data.

## Status

Next Priority (Vision - not yet implemented)

## Talking Points

- "This is our next focus"
- "Combines the best of both worlds"
- "The bridge is the key challenge we're solving"
