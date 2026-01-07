---
id: motivation-accessibility
title: "Everyone Can Contribute"
subtitle: "Not just for programmers"
section: motivation
parentId: motivation-vision
status: implemented
---

## Key Message

Agent Orchestrator separates **what** from **how** - enabling different roles to contribute their expertise without writing code.

## Who Contributes What

| Role | Contributes | How |
|------|-------------|-----|
| **PM / PO** | Agent descriptions, requirements, use cases | Edit `agent.json` and `agent.system-prompt.md` (pure text) |
| **Concept / Domain Expert** | Ontologies, entity definitions, schemas, relationships | Edit `capability.text.md` (structured markdown) |
| **Developer** | Tool implementations, deterministic agents, specialized runners | Implement MCP servers, build runners |

## Why This Works

- **Text-first design:** Blueprints and capabilities are JSON + Markdown, not code
- **Clear separation:** Domain knowledge lives separately from implementation
- **Automatic integration:** The coordinator merges everything at runtime
- **Change once, update all:** Modify a capability → all agents using it get the update

## The Building Blocks

**Blueprints** (what an agent is):
- `agent.json` - Name, description, tags (editable by anyone)
- `agent.system-prompt.md` - Role and behavior in natural language
- References capabilities by name

**Capabilities** (reusable knowledge + tools):
- `capability.text.md` - Ontology, schemas, domain knowledge (concept person)
- `capability.mcp.json` - Tool endpoints (developer)

**At runtime:** Coordinator automatically merges blueprint + capabilities into a complete agent.

## Diagram Description

**Visual: Three Roles Contributing to One Agent**

Show three columns flowing into a central "Agent":

**Left Column: PM / PO**
- Icon: clipboard or user
- Box: "Agent Description"
- Box: "System Prompt"
- Label: "Defines WHAT the agent does"

**Middle Column: Concept / Domain Expert**
- Icon: diagram or brain
- Box: "Ontology"
- Box: "Entity Schemas"
- Box: "Relationships"
- Label: "Defines the KNOWLEDGE"

**Right Column: Developer**
- Icon: code brackets
- Box: "MCP Servers"
- Box: "Deterministic Agents"
- Box: "Runners"
- Label: "Builds the TOOLS"

**Center: The Agent**
- All three columns flow with arrows into a central "Agent" box
- The agent combines: Description + Knowledge + Tools
- Below it: "Ready to run"

Visual message: Different expertise, different contributions, one integrated agent.

## Example

A knowledge graph agent:
- **PM** writes: "This agent helps developers find related modules and tickets"
- **Concept expert** defines: Module, Ticket, ConfluencePage entities and their relationships
- **Developer** implements: Neo4j MCP server with query capabilities

Result: A working agent that none of them could have built alone.

## Talking Points

- "You don't need to code to define an agent"
- "Your domain expertise becomes part of the system"
- "Developers focus on tools, not agent definitions"
