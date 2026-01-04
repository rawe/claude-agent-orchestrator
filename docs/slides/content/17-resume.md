---
id: resume
title: "Resuming Agents"
subtitle: "Continue where you left off"
---

## The Problem

After a child agent completes, you realize you forgot to ask something. Without resume, you would have to:

- **Start a new session** - lose all previous context
- **Redo the work** - expensive and time-consuming
- **Hope for consistent results** - no guarantee

## The Solution: Resume

The `resume_agent_session` tool lets you continue an existing session:

- **Context preserved** - the agent remembers everything
- **No redundant work** - computation already done
- **Ask follow-up questions** - get what was missing

## Example: Research Agent

1. **Initial task**: "Research competitor pricing strategies"
2. **Agent completes**: Returns summary of findings
3. **You realize**: Forgot to ask about specific competitor X
4. **Without resume**: Start over, redo all research
5. **With resume**: "What about competitor X's pricing?" - agent already has the data in context

## Why This Matters

| Without Resume | With Resume |
|----------------|-------------|
| Full restart | Continue conversation |
| Duplicate API calls | Reuse existing context |
| Inconsistent results | Build on previous work |
| Expensive | Cost-efficient |

## Key Insight

The child agent's context window likely contains more information than what was returned in the final result. Resume unlocks that hidden value.
