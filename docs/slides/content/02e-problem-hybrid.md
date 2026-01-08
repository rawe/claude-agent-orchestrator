---
id: hybrid-gap
title: "The AI-Program Gap"
subtitle: "Two worlds that don't easily connect"
parentId: motivation-problem
---

## Two Different Paradigms

### AI Agents
- **Flexible**: Handle ambiguity, reason about problems
- **Natural language**: Communicate in human terms
- **Slow**: LLM inference takes time
- **Unpredictable**: Same input may yield different outputs
- **Expensive**: Token costs add up

### Traditional Programs
- **Rigid**: Follow explicit rules
- **Structured I/O**: JSON, APIs, databases
- **Fast**: Millisecond response times
- **Deterministic**: Same input = same output
- **Cheap**: Compute is inexpensive

## The Gap

No clean way to combine them as equals:

### AI Calling Programs
- AI agent needs to format requests correctly
- Error handling becomes prompt engineering
- Type mismatches cause failures

### Programs Calling AI
- How do you wait for slow AI responses?
- How do you handle non-deterministic outputs?
- How do you validate AI-generated content?

### Orchestration Challenges
- Different execution models (async vs sync)
- Different error patterns
- Different scaling characteristics

## Real Example

A research workflow needs:
1. **AI Agent**: Decide what to research
2. **Web Crawler**: Fetch pages (fast, deterministic)
3. **AI Agent**: Analyze content
4. **Database**: Store results (fast, reliable)
5. **AI Agent**: Synthesize findings

Currently: AI agent tries to do everything itself, poorly.

**We need both types of agents as first-class citizens.**
