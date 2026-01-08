---
id: accessibility
title: "The Programmer Barrier"
subtitle: "Only developers can build and contribute agents"
parentId: motivation-problem
---

## Who Builds Agents Today?

Only people who can:
- Write Python/TypeScript code
- Understand API integrations
- Configure development environments
- Debug complex async systems

This excludes:
- **Product Managers** who know the requirements
- **Domain Experts** who understand the business
- **Designers** who envision the experience
- **Support Staff** who know customer needs

## The Knowledge Bottleneck

### Domain Expert Has Knowledge
"The CRM system uses these entities: Customer, Opportunity, Contact. They're related by..."

### Developer Has to Translate
```python
# Somehow encode this in prompts
# Hope the AI understands
# Debug when it doesn't
```

### Knowledge Gets Lost
- Simplified for code
- Outdated as domain evolves
- Scattered across files

## Current State

To define an agent, you must:
1. Write code (system prompts embedded in Python)
2. Configure tools (JSON/YAML with specific syntax)
3. Set up MCP servers (Docker, networking, APIs)
4. Test and debug (development environment)

**Every change requires a developer.**

## The Cost

- **Slow iteration**: Domain experts wait for developers
- **Lost nuance**: Translation loses detail
- **Bottlenecks**: Developers become gatekeepers
- **Limited contribution**: Most team members can't help

## What We Need

- **Text-first definitions**: Markdown and JSON, not code
- **Separation of concerns**: Domain knowledge separate from implementation
- **Clear contribution paths**: Different roles, different files
- **Automatic integration**: System merges everything at runtime
