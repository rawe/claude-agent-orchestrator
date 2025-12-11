# Agent Filtering with Tags - Refinement Proposal

> **Status**: DRAFT - Proposal for review
> **Replaces**: [Original Visibility Architecture](./agent-visibility-architecture.md) (to be deprecated)

## Context for New Readers

### What is the Agent Orchestrator?

The Agent Orchestrator is a framework for managing AI agents. It allows:

- **Defining agent blueprints**: Reusable configurations with system prompts, MCP servers, and skills
- **Spawning agent sessions**: Running instances of blueprints that can execute tasks
- **Orchestrating multi-agent workflows**: A parent agent can spawn child agents to delegate specialized tasks

### The Discovery Problem

Different consumers need to see different agents:

| Consumer | Example | What they should see |
|----------|---------|---------------------|
| End users | Claude Desktop, Dashboard Chat | Entry-point agents (e.g., "agent-orchestrator") |
| Internal orchestration | Parent agent spawning workers | Specialist agents (e.g., "jira-researcher") |
| Project teams | Project-specific tooling | Agents relevant to their project |
| Administrators | Dashboard Agent Manager | All agents for configuration |

### The Initial Solution (Now Deprecated)

We implemented a `visibility` property with hardcoded values (`public`, `internal`, `all`) and a `context` query parameter (`external`, `internal`). This approach had several problems:

1. **Terminology confusion**: `public` vs `external`, `visibility` vs `context`
2. **Hardcoded semantics**: Only supported one filtering dimension
3. **Not extensible**: Adding new categories required code changes
4. **Confusing mental model**: Mixed concepts that should be separate

---

## The New Approach: Tags Only

### Core Principle

**One unified mechanism: Tags**

- Agents expose a list of tags: `tags: ["internal", "research", "jira"]`
- Queries filter by tags: `?tags=internal,research`
- Matching rule: **Agent must have ALL queried tags (AND logic only)**

No special semantics. No hardcoded values. No OR logic. No inheritance. Tags are freeform strings whose meaning is determined by the user configuring them.

**Design Principles (KISS/YAGNI):**
- AND logic only - no OR queries, no complex boolean expressions
- No tag inheritance - agents don't inherit tags from anywhere
- No autocomplete/suggestions - fully freeform
- No reserved/special tags - all tags are equal

### The Matching Rule

This is the most important concept to understand:

```
Query tags ⊆ Agent tags  →  Agent is shown
```

**Examples:**

| Agent tags | Query tags | Result | Reason |
|------------|------------|--------|--------|
| `[internal, jira, research]` | `[internal]` | ✅ Match | Agent has `internal` |
| `[internal, jira, research]` | `[internal, jira]` | ✅ Match | Agent has both |
| `[internal, jira, research]` | `[internal, confluence]` | ❌ No match | Agent missing `confluence` |
| `[internal, jira]` | `[internal, jira, async]` | ❌ No match | Agent missing `async` |
| `[]` (empty) | `[internal]` | ❌ No match | Agent has no tags |
| `[internal, jira]` | `[]` (empty) | ✅ Match | No filter = show all |

### Key Behaviors

| Scenario | Behavior |
|----------|----------|
| Query with no tags | Return all agents (no filtering) |
| Query with one tag | Return agents that have that tag |
| Query with multiple tags | Return agents that have **ALL** tags (AND only) |
| Agent with no tags | Only shown when query has no tags |
| Agent with many tags | Matches any query where query tags ⊆ agent tags |

**What we explicitly do NOT support:**
- OR logic (`?tags=jira|confluence`) - not supported
- Negation (`?tags=!experimental`) - not supported
- Tag inheritance from blueprints to sessions - not supported
- Wildcard tags (`?tags=project-*`) - not supported

---

## Specification

### Agent Configuration

**File**: `config/agents/*/agent.json`

```json
{
  "name": "jira-researcher",
  "description": "Specialist for Jira research tasks",
  "tags": ["internal", "research", "jira", "atlassian"]
}
```

Tags are:
- **Optional**: Omitted or empty `[]` means no tags
- **Freeform**: No predefined vocabulary - meaning is user-defined
- **Case-sensitive**: `Internal` ≠ `internal` (recommend lowercase)
- **Array of strings**: Simple list, no nested structure

### Data Model

**File**: `servers/agent-runtime/models.py`

```python
class Agent(AgentBase):
    name: str
    description: str
    system_prompt: Optional[str] = None
    mcp_servers: Optional[dict[str, MCPServerConfig]] = None
    skills: Optional[list[str]] = None
    tags: list[str] = []  # NEW - replaces visibility
    status: Literal["active", "inactive"] = "active"
    created_at: str
    modified_at: str
```

### API Endpoint

**File**: `servers/agent-runtime/main.py`

```python
@app.get("/agents")
def list_agents(
    tags: Optional[str] = Query(
        default=None,
        description="Comma-separated tags. Returns agents that have ALL specified tags (AND logic)."
    )
):
    """
    List agents, optionally filtered by tags.

    - No tags parameter: Returns all agents
    - tags=foo: Returns agents with tag "foo"
    - tags=foo,bar: Returns agents with BOTH "foo" AND "bar" tags
    """
    agents = agent_storage.list_agents()

    if tags:
        required_tags = set(tag.strip() for tag in tags.split(",") if tag.strip())
        agents = [a for a in agents if required_tags.issubset(set(a.tags))]

    return agents
```

### MCP Server Configuration

**File**: `mcps/agent-orchestrator/libs/constants.py`

```python
# HTTP Header for tag filtering (in HTTP mode)
HEADER_AGENT_TAGS = "X-Agent-Tags"

# Environment variable for tag filtering (in stdio mode)
ENV_AGENT_TAGS = "AGENT_TAGS"
```

**Usage in MCP config** (`agent.mcp.json`):

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "type": "http",
      "url": "http://localhost:9500/mcp",
      "headers": {
        "X-Agent-Session-Name": "${AGENT_SESSION_NAME}",
        "X-Agent-Tags": "internal,research"
      }
    }
  }
}
```

**Usage in stdio mode** (Claude Desktop):

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "python",
      "args": ["-m", "mcps.agent-orchestrator"],
      "env": {
        "AGENT_TAGS": "external"
      }
    }
  }
}
```

### MCP Core Functions

**File**: `mcps/agent-orchestrator/libs/core_functions.py`

```python
def get_filter_tags(http_headers: Optional[dict] = None) -> Optional[str]:
    """
    Get filter tags from environment or HTTP headers.

    Returns comma-separated tag string or None if not set.
    """
    if http_headers:
        header_key_lower = HEADER_AGENT_TAGS.lower()
        tags = http_headers.get(header_key_lower)
        if tags:
            return tags

    return os.environ.get(ENV_AGENT_TAGS)


async def list_agent_blueprints_impl(
    config: ServerConfig,
    response_format: Literal["markdown", "json"] = "markdown",
    http_headers: Optional[dict] = None,
) -> str:
    """List available agent blueprints filtered by tags."""

    tags = get_filter_tags(http_headers)

    client = get_api_client(config)
    agents = await client.list_agents(tags=tags)

    # Filter to active agents only
    active_agents = [a for a in agents if a.get("status") == "active"]

    # ... formatting logic
```

---

## Example Configurations

### Entry-Point Agent (for end users via Claude Desktop)

```json
{
  "name": "agent-orchestrator",
  "description": "Agent able to spawn other agents",
  "tags": ["external"]
}
```

MCP configured with `X-Agent-Tags: external` will see this agent.

### Internal Worker Agent (for orchestration)

```json
{
  "name": "jira-researcher",
  "description": "Specialist for Jira research tasks",
  "tags": ["internal", "research", "jira"]
}
```

- MCP configured with `X-Agent-Tags: internal` will see this agent.
- MCP configured with `X-Agent-Tags: internal,jira` will see this agent.
- MCP configured with `X-Agent-Tags: external` will NOT see this agent.

### Agent Visible to Multiple Contexts

```json
{
  "name": "context-store-agent",
  "description": "Agent for context store operations",
  "tags": ["external", "internal", "utility"]
}
```

Both `X-Agent-Tags: external` and `X-Agent-Tags: internal` will see this agent.

### Project-Specific Agent

```json
{
  "name": "project-alpha-helper",
  "description": "Helper for Project Alpha",
  "tags": ["internal", "project-alpha"]
}
```

Only MCP configured with tags including both `internal` AND `project-alpha` will see this.

---

## Filtering Matrix

```
┌──────────────────────────────┬─────────────┬─────────────┬───────────────────┬─────────────┐
│ Agent tags                   │ Query:      │ Query:      │ Query:            │ Query:      │
│                              │ (none)      │ external    │ internal          │ internal,   │
│                              │             │             │                   │ jira        │
├──────────────────────────────┼─────────────┼─────────────┼───────────────────┼─────────────┤
│ [external]                   │ ✅ Shown    │ ✅ Shown    │ ❌ Hidden         │ ❌ Hidden   │
│ [internal]                   │ ✅ Shown    │ ❌ Hidden   │ ✅ Shown          │ ❌ Hidden   │
│ [internal, jira]             │ ✅ Shown    │ ❌ Hidden   │ ✅ Shown          │ ✅ Shown    │
│ [external, internal]         │ ✅ Shown    │ ✅ Shown    │ ✅ Shown          │ ❌ Hidden   │
│ [internal, jira, research]   │ ✅ Shown    │ ❌ Hidden   │ ✅ Shown          │ ✅ Shown    │
│ []                           │ ✅ Shown    │ ❌ Hidden   │ ❌ Hidden         │ ❌ Hidden   │
└──────────────────────────────┴─────────────┴─────────────┴───────────────────┴─────────────┘
```

---

## Dashboard UI Changes

### Agent Table

- **Remove**: `VisibilityBadge` component with Globe/Lock/Layers icons
- **Remove**: Visibility column
- **Add**: Tags column displaying tag chips/badges
- **Add**: Click on tag to filter table by that tag (optional enhancement)

### Agent Editor

- **Remove**: Visibility dropdown with "All Contexts", "External Only", "Internal Only"
- **Remove**: Visibility help text with Info icon
- **Add**: `TagSelector` component for tags input
  - Chip-based input (not a dropdown)
  - Add tags by typing and pressing Enter or comma
  - Remove tags by clicking X on chip or Backspace
  - No autocomplete (freeform)

### Chat Page

- **Change**: Use `?tags=external` instead of `?context=external`
- Or configure which tags to filter by

---

## Implementation TODO

### Phase 1: Remove Current Visibility System

#### Backend: `servers/agent-runtime/`

| File | Action | Details |
|------|--------|---------|
| `models.py` | **Remove** | `visibility: Literal["public", "internal", "all"]` from `Agent`, `AgentCreate`, `AgentUpdate` |
| `models.py` | **Add** | `tags: list[str] = []` to `Agent`, `AgentCreate`, `AgentUpdate` |
| `agent_storage.py` | **Remove** | `visibility = data.get("visibility", "all")` in `_read_agent_from_dir()` |
| `agent_storage.py` | **Remove** | `visibility` writing in `create_agent()` and `update_agent()` |
| `agent_storage.py` | **Add** | `tags = data.get("tags", [])` in `_read_agent_from_dir()` |
| `agent_storage.py` | **Add** | `tags` writing in `create_agent()` and `update_agent()` |
| `main.py` | **Remove** | `context` query parameter from `list_agents()` |
| `main.py` | **Remove** | Context-based filtering logic (`if context == "external"`, etc.) |
| `main.py` | **Add** | `tags` query parameter |
| `main.py` | **Add** | Tag-based AND filtering logic |

#### MCP Server: `mcps/agent-orchestrator/libs/`

| File | Action | Details |
|------|--------|---------|
| `constants.py` | **Remove** | `HEADER_AGENT_VISIBILITY_CONTEXT` |
| `constants.py` | **Remove** | `ENV_AGENT_VISIBILITY_CONTEXT` |
| `constants.py` | **Add** | `HEADER_AGENT_TAGS = "X-Agent-Tags"` |
| `constants.py` | **Add** | `ENV_AGENT_TAGS = "AGENT_TAGS"` |
| `core_functions.py` | **Remove** | `get_visibility_context()` function |
| `core_functions.py` | **Remove** | Import of `HEADER_AGENT_VISIBILITY_CONTEXT`, `ENV_AGENT_VISIBILITY_CONTEXT` |
| `core_functions.py` | **Add** | `get_filter_tags()` function |
| `core_functions.py` | **Add** | Import of `HEADER_AGENT_TAGS`, `ENV_AGENT_TAGS` |
| `core_functions.py` | **Change** | `list_agent_blueprints_impl()` to use `get_filter_tags()` instead of `get_visibility_context()` |
| `api_client.py` | **Change** | `list_agents(context=...)` → `list_agents(tags=...)` |
| `server.py` | **Change** | Update `list_agent_blueprints` tool docstring (remove visibility context mention) |

#### Skills: `plugins/orchestrator/skills/orchestrator/commands/`

| File | Action | Details |
|------|--------|---------|
| `ao-list-blueprints` | **Remove** | `--context` / `-c` flag |
| `ao-list-blueprints` | **Add** | `--tags` / `-t` flag (comma-separated string) |
| `ao-list-blueprints` | **Change** | Update help text and examples |
| `lib/agent_api.py` | **Change** | `list_agents_api(context=...)` → `list_agents_api(tags=...)` |
| `lib/agent_api.py` | **Change** | API call from `?context=...` to `?tags=...` |

#### Dashboard: `dashboard/src/`

| File | Action | Details |
|------|--------|---------|
| `types/agent.ts` | **Remove** | `AgentVisibility` type |
| `types/agent.ts` | **Remove** | `VISIBILITY_OPTIONS` constant |
| `types/agent.ts` | **Remove** | `visibility: AgentVisibility` from `Agent` interface |
| `types/agent.ts` | **Remove** | `visibility?: AgentVisibility` from `AgentCreate` and `AgentUpdate` |
| `types/agent.ts` | **Add** | `tags: string[]` to `Agent` interface |
| `types/agent.ts` | **Add** | `tags?: string[]` to `AgentCreate` and `AgentUpdate` |
| `services/agentService.ts` | **Remove** | `VisibilityContext` type |
| `services/agentService.ts` | **Change** | `getAgents(context?)` → `getAgents(tags?)` |
| `services/agentService.ts` | **Change** | Query param from `?context=...` to `?tags=...` |
| `services/chatService.ts` | **Change** | `?context=external` → `?tags=external` (or appropriate tags) |
| `utils/mcpTemplates.ts` | **Remove** | `'X-Agent-Visibility-Context': '${AGENT_VISIBILITY_CONTEXT}'` |
| `utils/mcpTemplates.ts` | **Add** | `'X-Agent-Tags': '${AGENT_TAGS}'` |

| File | Action | Details |
|------|--------|---------|
| `components/features/agents/AgentTable.tsx` | **Remove** | `VisibilityBadge` component (entire function) |
| `components/features/agents/AgentTable.tsx` | **Remove** | Globe, Lock, Layers icon imports |
| `components/features/agents/AgentTable.tsx` | **Remove** | Visibility column definition |
| `components/features/agents/AgentTable.tsx` | **Add** | Tags column with chip display |
| `components/features/agents/AgentEditor.tsx` | **Remove** | Visibility dropdown (`<select {...register('visibility')}>`) |
| `components/features/agents/AgentEditor.tsx` | **Remove** | `VISIBILITY_OPTIONS` import |
| `components/features/agents/AgentEditor.tsx` | **Remove** | Visibility help text with Info icon |
| `components/features/agents/AgentEditor.tsx` | **Remove** | `visibility` from form default values and reset |
| `components/features/agents/AgentEditor.tsx` | **Add** | `TagSelector` component for tags |
| `components/features/agents/AgentEditor.tsx` | **Add** | `tags` to form default values and reset |
| `pages/AgentManager.tsx` | **Remove** | `visibility: data.visibility` from save handler |
| `pages/AgentManager.tsx` | **Add** | `tags: data.tags` to save handler |

#### New Component: `dashboard/src/components/common/TagSelector.tsx`

Create a reusable tag input component:

```typescript
interface TagSelectorProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
}
```

Features:
- Displays current tags as removable chips
- Text input to add new tags
- Add on Enter key or comma key
- Remove on chip X click
- Remove last tag on Backspace when input is empty
- No autocomplete/suggestions (freeform)

### Phase 2: Migrate Agent Configurations

#### All `config/agents/*/agent.json` files

| Current | Migration |
|---------|-----------|
| `"visibility": "public"` | Remove, add `"tags": ["external"]` |
| `"visibility": "internal"` | Remove, add `"tags": ["internal"]` |
| `"visibility": "all"` | Remove, add `"tags": ["external", "internal"]` |
| No visibility field | Add `"tags": []` or appropriate tags |

**Files to update:**
- `config/agents/agent-orchestrator/agent.json`
- `config/agents/jira-researcher/agent.json`
- `config/agents/web-researcher/agent.json`
- `config/agents/confluence-researcher/agent.json`
- `config/agents/context-store-agent/agent.json`
- `config/agents/simple-agent/agent.json`
- (and all other agent configurations)

### Phase 3: Update Documentation

| File | Action |
|------|--------|
| `docs/features/agent-visibility-architecture.md` | Add DEPRECATED notice at top, link to this document |
| `docs/features/agent-visibility-implementation-report.md` | Add DEPRECATED notice at top |
| This document (`agent-visibility-refinement.md`) | Update status to IMPLEMENTED |

---

## Mental Model Summary

When explaining tag-based filtering:

### One Simple Rule

> **An agent is shown if it has ALL the tags being queried for. (AND logic only)**

### The Formula

```
Query tags ⊆ Agent tags  →  Show agent
```

Read as: "Query tags is a subset of (or equal to) Agent tags"

There is no OR. There is no NOT. Just AND.

### Quick Reference

| You want to... | Configure MCP with | Agent needs tags including |
|----------------|-------------------|----------------------------|
| See entry-point agents | `X-Agent-Tags: external` | `external` |
| See internal workers | `X-Agent-Tags: internal` | `internal` |
| See Jira-capable internal agents | `X-Agent-Tags: internal,jira` | `internal` AND `jira` |
| See all agents (admin) | No header / empty | (any - no filtering) |

### Two Dimensions

| Field | Purpose | Type |
|-------|---------|------|
| `tags` | Filter which agents are discoverable | `string[]` |
| `status` | Toggle agent on/off operationally | `"active" \| "inactive"` |

---

## Files Reference

### To Modify (Remove Visibility, Add Tags)

```
servers/agent-runtime/models.py
servers/agent-runtime/agent_storage.py
servers/agent-runtime/main.py
mcps/agent-orchestrator/libs/constants.py
mcps/agent-orchestrator/libs/core_functions.py
mcps/agent-orchestrator/libs/api_client.py
mcps/agent-orchestrator/libs/server.py
plugins/orchestrator/skills/orchestrator/commands/ao-list-blueprints
plugins/orchestrator/skills/orchestrator/commands/lib/agent_api.py
dashboard/src/types/agent.ts
dashboard/src/services/agentService.ts
dashboard/src/services/chatService.ts
dashboard/src/components/features/agents/AgentTable.tsx
dashboard/src/components/features/agents/AgentEditor.tsx
dashboard/src/pages/AgentManager.tsx
dashboard/src/utils/mcpTemplates.ts
```

### To Create

```
dashboard/src/components/common/TagSelector.tsx
```

### To Migrate (Agent Configs)

```
config/agents/*/agent.json (all agent configuration files)
```

### To Deprecate

```
docs/features/agent-visibility-architecture.md
docs/features/agent-visibility-implementation-report.md
```

---

## Implementation Strategy: Start Fresh vs. Modify

### Option A: Checkout Pre-Visibility Commit and Start Fresh

**Pros:**
- Clean slate - no risk of leftover visibility code
- Simpler mental model - just add tags, don't think about what to remove
- No accidental partial removals
- Git history shows clean "add tags feature" commit

**Cons:**
- Loses some useful changes (e.g., `http_headers` parameter already added to `list_agent_blueprints_impl`)
- Must re-implement the plumbing (header reading, API parameter, etc.)
- Dashboard changes like the Dropdown component may be unrelated and useful

### Option B: Modify Current Staged Changes

**Pros:**
- Infrastructure already in place (header reading, API parameters, MCP config)
- Just need to rename/repurpose: `visibility` → `tags`, `context` → `tags`
- Dashboard components partially usable (though TagSelector needs to be created)

**Cons:**
- Risk of missing a visibility reference somewhere
- More cognitive load - must track what to remove vs. keep
- Potential for bugs from incomplete removal

### Recommendation: **Option A - Start Fresh**

The visibility implementation touches many files with specific semantics (`public`, `internal`, `all`, `context`, `external`). Trying to surgically remove and replace creates risk of:

1. Leaving behind a `context` parameter somewhere
2. Missing a `visibility` field in a model
3. Forgetting to remove the `VisibilityBadge` component
4. Leaving hardcoded strings like `"external"` or `"internal"` with old semantics

**The tags implementation is conceptually simpler** - it's just a string array with subset matching. Starting fresh means:

- Read the TODO list in this document
- Implement each item cleanly
- No mental overhead of "did I remove everything?"

### How to Start Fresh

```bash
# Find the commit before visibility was added
git log --oneline | head -20

# The commit before visibility changes (based on git status)
# Look for commit before "feat: add agent visibility..."

# Create a new branch from that point
git checkout <commit-hash> -b feature/agent-tags

# Or if visibility changes are staged but not committed:
git stash  # or git checkout -- . to discard
```

Then implement tags following this document's specification.

### Files to Preserve (Cherry-Pick or Re-implement)

If there are useful non-visibility changes in the staged files, consider cherry-picking or manually re-implementing:

| File | Useful Changes? |
|------|-----------------|
| `dashboard/src/components/common/Dropdown.tsx` | Possibly - check if unrelated to visibility |
| MCP `http_headers` plumbing | Re-implement for tags (similar pattern) |
| API query parameter pattern | Re-implement for tags (similar pattern) |

Most of the staged changes are visibility-specific and should be discarded.
