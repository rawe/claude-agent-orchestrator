# Phase 2: Scripts as Capabilities for Autonomous Agents

**Status:** Future Consideration
**Created:** 2025-01-24

## Overview

This document captures the intent and open questions for enabling scripts to be used as capabilities/skills by autonomous agents, allowing local execution within the agent's filesystem context.

---

## The Problem

In Phase 1, autonomous agents invoke scripts via the orchestrator MCP:

```
Autonomous Agent
    │
    │ start_agent_session(agent_name="notifier", parameters={...})
    │ (via orchestrator MCP)
    ▼
Procedural Runner executes script
    │
    ▼
Result returned
```

**Limitation:** The script runs on a **different runner** with a **different filesystem**. The autonomous agent cannot:
- Pass local files it created to the script
- Have the script process files in the agent's working directory
- Receive output files from the script directly

---

## The Intent

Scripts as capabilities would allow autonomous agents to execute scripts **locally**, in the same filesystem context:

```
Autonomous Agent (on Runner A)
    │
    │ Agent creates /tmp/data.csv
    │ Agent uses "data-processor" skill
    │
    ▼
Script executes locally (on Runner A)
    │ Script reads /tmp/data.csv
    │ Script writes /tmp/result.json
    │
    ▼
Agent continues with /tmp/result.json
```

**Key benefit:** Same filesystem, direct file access, no intermediate storage needed.

---

## Why This Matters

### Use Cases Requiring Local Access

| Use Case | Why Remote Execution Fails |
|----------|---------------------------|
| Agent creates temp file, needs processing | File doesn't exist on procedural runner |
| Agent downloads data, needs transformation | Would require re-uploading to remote |
| Agent needs script output as local file | Would require downloading result |
| Low-latency iterative processing | Network round-trip per iteration |

### The Claude Code Skills Parallel

Claude Code skills demonstrate this pattern:
- Skills can include executable scripts in their folder
- The skill description explains how to use them
- Claude executes scripts locally via bash
- Scripts have access to the same filesystem as Claude

---

## Context Store Consideration

One approach: Use Context Store as intermediate storage.

```
Agent creates file
    │
    ▼
Upload to Context Store (doc-push equivalent)
    │
    ▼
Script downloads from Context Store
    │
    ▼
Script processes, uploads result
    │
    ▼
Agent downloads result
```

**Why this is incomplete:**

| Issue | Problem |
|-------|---------|
| Requires explicit upload/download | Agent must know which files to sync |
| Adds latency | Multiple network round-trips |
| Requires orchestration | Who decides what to upload/download? |
| Doesn't solve local output | Script output still needs download |

Context Store could help for **specific documents** that need sharing, but it doesn't solve the general local filesystem access problem.

**If we had a download feature** (agent starts with specific documents downloaded):
- Good for input documents
- Still doesn't solve: output files, temp files, iterative workflows
- Requires pre-configuration of which documents

**Conclusion:** Context Store integration is a separate concern. Local script execution is more fundamental and provides direct filesystem access without orchestration overhead.

---

## Potential Approach

### Scripts Synced to Autonomous Runners

Autonomous runners would sync scripts (like procedural runners in Phase 1):

```
Autonomous Runner
├── Scripts directory
│   └── {script_name}/
│       ├── script.json
│       └── {script_file}
│
└── Executor (Claude Code)
    └── Can execute local scripts via bash
```

### Script as Capability/Skill

A capability references a script and provides execution guidance:

```json
{
  "name": "data-processing-skill",
  "type": "script",
  "script": "process-data",
  "description": "Process data files locally"
}
```

When assigned to an autonomous agent:
- Script is available locally
- System prompt includes usage instructions
- Agent can execute via bash: `uv run --script {path} --args`

### Parameters Schema as Skill Description

The script's `parameters_schema` would be transformed into a skill description:

```
Script parameters_schema:
{
  "required": ["message", "channel"],
  "properties": {
    "message": { "type": "string", "description": "The message to send" },
    "channel": { "type": "string", "enum": ["slack", "email"] }
  }
}

Becomes skill description:
"To use this skill, run the script with:
  --message: (required) The message to send
  --channel: (required) One of: slack, email"
```

---

## Open Questions

### Distribution

| Question | Context |
|----------|---------|
| Same sync mechanism as Phase 1? | Reuse long-poll sync commands |
| Which scripts go to autonomous runners? | Based on capability assignment? All scripts? |
| Storage location on runner? | Same as procedural: `{project_dir}/.agent-orchestrator/scripts/` |

### Execution

| Question | Context |
|----------|---------|
| How does agent know how to invoke the script? | System prompt injection? Skill description? |
| How to transform parameters_schema to CLI guidance? | Template generation |
| How to handle errors? | Agent sees stderr, retries? |
| Working directory for script? | Agent's current directory? Script directory? |

### Reliability

| Question | Context |
|----------|---------|
| What if agent invokes script incorrectly? | Bad flags, wrong arguments |
| How to validate invocation before execution? | Pre-check mechanism? |
| Security implications? | Agent with bash could be manipulated |

### Observability

| Question | Context |
|----------|---------|
| How to track script executions? | Buried in agent's bash calls |
| Should script calls be separate events? | For auditing |
| How to correlate script results with agent actions? | Traceability |

---

## Relationship to Phase 1

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| Script storage | Coordinator | Coordinator (same) |
| Script sync | Procedural runners | Autonomous runners (additional) |
| Invocation | Orchestrator MCP | Direct bash execution |
| Filesystem | Script's runner | Agent's runner (same) |
| Observability | Procedural session tracked | Embedded in agent session |

Phase 2 builds on Phase 1 - scripts remain stored in Coordinator, but are additionally synced to autonomous runners for local execution.

---

## Not Addressed Here

- **Context Store integration** - Separate concern for document sharing
- **MCP-based script tools** - Rejected due to dynamic tool limitations
- **Detailed implementation** - Deferred until Phase 1 is complete and validated

---

## Next Steps

1. Complete Phase 1 implementation
2. Gather real use cases requiring local script execution
3. Validate that Phase 1 doesn't cover these use cases
4. Design detailed Phase 2 implementation based on learnings
