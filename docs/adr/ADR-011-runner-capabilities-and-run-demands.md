# ADR-011: Runner Capabilities and Run Demands

**Status:** Accepted
**Date:** 2025-12-18
**Decision Makers:** Architecture Review

## Context

Currently, when a run is created, any registered runner can claim it on a first-come-first-serve basis. There is no logic to match runs to appropriate runners.

### Problems with Current Approach

1. **No placement control**: Cannot specify that an agent should run on a specific machine
2. **No project affinity**: Cannot ensure an agent runs in a specific project directory
3. **No capability matching**: Cannot require specific executor types or features
4. **Orchestration limitations**: Parent agents cannot ensure children run on the same host

### Use Case Example

> "I want an agent which runs on my local computer in a certain folder to help me coding with the project that is in this folder and this project is a Python project."

This requires:
- Specific hostname (my local machine)
- Specific project directory (the folder with my code)
- Specific capabilities (Python support)

Currently impossible to express or enforce.

## Decision

### 1. Runner Properties and Capabilities

Runners have two categories of attributes:

**Properties** (identity - see [ADR-012](./ADR-012-runner-identity-and-registration.md)):
- `hostname` - Which machine the runner is on
- `project_dir` - Which directory the runner operates in
- `executor_type` - Which executor the runner uses

**Capabilities** (features):
- `tags` - Arbitrary capability tags describing what the runner can do

```python
# Properties identify the runner (used for ID derivation per ADR-012)
# Capabilities describe what features the runner offers

class Runner(BaseModel):
    # Identity (derived by coordinator - see ADR-012)
    runner_id: str

    # Properties (WHERE/WHAT the runner is)
    hostname: str
    project_dir: str
    executor_type: str

    # Capabilities (WHAT the runner can do)
    tags: list[str] = []
```

Registration (runner_id returned by coordinator per ADR-012):
```
POST /runner/register
{
    "hostname": "my-macbook",
    "project_dir": "/Users/me/projects/my-python-app",
    "executor_type": "claude-code",
    "tags": ["python", "docker", "nodejs"]
}

Response:
{
    "runner_id": "lnch_a1b2c3d4e5f6"
}
```

### 2. Agent Blueprints Define Demands

Agent blueprints specify **demands** - what they need. Demands can target:
- **Properties**: hostname, project_dir, executor_type (exact match)
- **Capabilities**: tags (must have ALL demanded tags)

```python
class RunnerDemands(BaseModel):
    # Property demands (exact match required)
    hostname: Optional[str] = None       # Must run on this host
    project_dir: Optional[str] = None    # Must run in this directory
    executor_type: Optional[str] = None  # Must use this executor

    # Capability demands (must have ALL)
    tags: list[str] = []                 # Must have ALL these tags
```

Blueprint example:
```yaml
name: python-project-helper
description: Coding assistant for my Python project

demands:
  hostname: my-macbook
  project_dir: /Users/me/projects/my-python-app
  executor_type: claude-code
  tags: [python]
```

### 3. Run Requests Can Add (Not Override) Demands

When creating a run, additional demands can be specified. These are **additive only** - they can add constraints but never relax or override blueprint demands.

```
POST /runs
{
    "agent_name": "python-project-helper",
    "prompt": "Help me refactor this code",
    "additional_demands": {
        "tags": ["testing"]
    }
}
```

#### Merge Rules (Additive Only)

```python
def merge_demands(
    blueprint: RunnerDemands,
    additional: RunnerDemands
) -> RunnerDemands:
    """
    Merge demands additively.
    Additional demands can ADD constraints, never OVERRIDE or RELAX.
    """
    return RunnerDemands(
        # Only set if not already set by blueprint
        hostname=blueprint.hostname or additional.hostname,
        project_dir=blueprint.project_dir or additional.project_dir,
        executor_type=blueprint.executor_type or additional.executor_type,
        # Tags are always additive (union)
        tags=list(set(blueprint.tags) | set(additional.tags)),
    )
```

**Example:**
```
Blueprint demands:  { hostname: "my-mac", tags: ["python"] }
Additional demands: { project_dir: "/code", tags: ["testing"] }
                                    ↓
Merged demands:     { hostname: "my-mac", project_dir: "/code", tags: ["python", "testing"] }
```

**Override attempt (rejected):**
```
Blueprint demands:  { hostname: "my-mac" }
Additional demands: { hostname: "server-1" }  # Tries to override
                                    ↓
Merged demands:     { hostname: "my-mac" }    # Blueprint wins, additional ignored
```

### 4. Matching Logic

A runner can claim a run only if its capabilities satisfy all demands:

```python
def capabilities_satisfy_demands(
    capabilities: RunnerCapabilities,
    demands: RunnerDemands
) -> bool:
    """
    Check if runner capabilities satisfy run demands.
    All specified demands must be met (hard requirements).
    """
    # Hostname check (if demanded)
    if demands.hostname and capabilities.hostname != demands.hostname:
        return False

    # Project directory check (if demanded)
    if demands.project_dir and capabilities.project_dir != demands.project_dir:
        return False

    # Executor type check (if demanded)
    if demands.executor_type and capabilities.executor_type != demands.executor_type:
        return False

    # Tags check - runner must have ALL demanded tags
    if demands.tags:
        if not set(demands.tags).issubset(set(capabilities.tags)):
            return False

    return True
```

### 5. No Matching Runner Behavior

When no registered runner satisfies the demands:

1. **Run stays pending** with status `pending_no_match`
2. **Timeout applies** (configurable, default: 5 minutes)
3. **On timeout**: Run transitions to `failed` with error "No matching runner available"
4. **If runner registers**: Pending runs are re-evaluated for matches

```
Run created with demands
        ↓
    ┌───────────────────────────────────────┐
    │ Poll: Any runner satisfies demands?   │◄─── Runner registers
    │                                       │     (re-evaluate)
    │   YES → Runner claims run             │
    │   NO  → Wait (up to timeout)          │
    └───────────────────────────────────────┘
        ↓ (timeout)
    Run fails: "No matching runner"
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. RUNNER REGISTRATION                                                     │
│                                                                             │
│  POST /runner/register                                                      │
│  {                                                                          │
│      "runner_id": "lnch_abc",                                               │
│      "capabilities": {                                                      │
│          "hostname": "my-macbook",                                          │
│          "project_dir": "/Users/me/projects/app",                           │
│          "executor_type": "claude-code",                                    │
│          "tags": ["python", "docker"]                                       │
│      }                                                                      │
│  }                                                                          │
│                                                                             │
│  Coordinator stores runner with capabilities                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. RUN CREATION                                                            │
│                                                                             │
│  POST /runs                                                                 │
│  {                                                                          │
│      "agent_name": "python-helper",     # Blueprint has base demands        │
│      "prompt": "Help me code",                                              │
│      "additional_demands": {            # Additive only                     │
│          "tags": ["testing"]                                                │
│      }                                                                      │
│  }                                                                          │
│                                                                             │
│  Coordinator:                                                               │
│    1. Loads blueprint demands                                               │
│    2. Merges with additional_demands (additive)                             │
│    3. Stores final demands on run                                           │
│    4. Returns { run_id, session_id }                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. RUN CLAIMING (with matching)                                            │
│                                                                             │
│  Runner polls: GET /runner/runs?runner_id=lnch_abc                          │
│                                                                             │
│  Coordinator:                                                               │
│    FOR each pending run:                                                    │
│      IF capabilities_satisfy_demands(runner.capabilities, run.demands):     │
│        claim_run(run, runner)                                               │
│        RETURN run                                                           │
│                                                                             │
│  Only matching runners can claim runs                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Relationship to Session Affinity (ADR-010)

This ADR covers **initial placement** - where a NEW session is created.

[ADR-010](./ADR-010-session-identity-and-executor-abstraction.md) covers **resume affinity** - where an EXISTING session must be resumed.

| Concern | Governed By | Logic |
|---------|-------------|-------|
| Where to CREATE a session | This ADR (Demands) | Match runner properties/capabilities to run demands |
| Where to RESUME a session | ADR-010 (Affinity) | Must be same hostname + project_dir where created |

**Flow:**
1. New run → Match demands to runner properties/capabilities → Runner claims → Session created
2. Session stores: `hostname`, `project_dir`, `executor_type` (affinity info)
3. Resume run → Must go to runner matching stored affinity (not just demands)

## Schema Changes

### Runner Table (expanded)

```sql
CREATE TABLE runners (
    runner_id TEXT PRIMARY KEY,
    registered_at TEXT NOT NULL,
    last_heartbeat TEXT NOT NULL,

    -- Properties (identity - see ADR-012)
    hostname TEXT NOT NULL,
    project_dir TEXT NOT NULL,
    executor_type TEXT NOT NULL,

    -- Capabilities (features)
    tags TEXT,  -- JSON array: ["python", "docker"]

    -- Status
    status TEXT NOT NULL  -- online, stale
);
```

### Agent Blueprint (expanded)

```sql
-- Stored as JSON in agent files
{
    "name": "python-helper",
    "description": "...",
    "demands": {
        "hostname": "my-macbook",
        "project_dir": "/path/to/project",
        "executor_type": "claude-code",
        "tags": ["python"]
    }
}
```

### Run (expanded)

```sql
-- In-memory run queue
{
    "run_id": "run_abc123",
    "session_id": "ses_xyz789",
    "demands": {
        "hostname": "my-macbook",
        "project_dir": "/path/to/project",
        "executor_type": "claude-code",
        "tags": ["python", "testing"]
    },
    "status": "pending",
    "created_at": "...",
    "timeout_at": "..."  -- For no-match timeout
}
```

## Rationale

### Why Capabilities/Demands Terminology?

| Term | Meaning | Clarity |
|------|---------|---------|
| **Capabilities** | What runners CAN do / HAVE | Clear - it's what they offer |
| **Demands** | What runs MUST have | Clear - non-negotiable requirements |

"Demands" was chosen over "requirements" because:
- Demands are inherently non-negotiable (fits hard-only model)
- Clear pairing with capabilities
- No ambiguity about soft vs hard

### Why Additive-Only Merging?

Allowing overrides would create interpretation problems:
- "Does the run trust the blueprint or not?"
- "Which value takes precedence?"
- "Can a run bypass security constraints?"

Additive-only is unambiguous:
- Blueprint sets the baseline
- Run can only add constraints
- Security: runs cannot escape blueprint restrictions

### Why Hard Requirements Only?

Soft/preferred requirements add complexity:
- Scoring algorithms
- "Good enough" vs "best" matching
- Non-deterministic behavior

Hard requirements are simple:
- Binary match: yes or no
- Deterministic: same demands always match same runners
- Easy to debug: "Why didn't my run get claimed?" → Check demands vs runner properties/capabilities

## Consequences

### Positive

- **Controlled placement**: Runs go to appropriate runners
- **Orchestration support**: Parents can ensure children run on same host
- **Clear semantics**: Properties/capabilities vs demands is intuitive
- **Predictable**: Hard requirements, additive merging, deterministic matching
- **Extensible**: Tags allow arbitrary capability/demand matching

### Negative

- **More configuration**: Blueprints need demands section
- **Runner setup**: Runners must be configured with correct properties and capabilities
- **Potential deadlock**: Overly specific demands may never find a match
- **No load balancing**: First matching runner wins (no scoring)

### Neutral

- Runners must register with properties and capabilities (currently optional metadata becomes required)
- Blueprints gain optional `demands` section
- Run creation gains optional `additional_demands` field

## Future Considerations

### Potential Enhancements (Not in Scope)

1. **Soft preferences**: Preferred but not required demands
2. **Load-aware scheduling**: Consider runner load when multiple match
3. **Resource demands**: Memory, CPU requirements
4. **Geographic affinity**: Region/zone-based placement
5. **Anti-affinity**: "Don't run on the same host as X"

These are intentionally deferred to keep the initial implementation simple.

## References

- [ADR-010: Session Identity and Executor Abstraction](./ADR-010-session-identity-and-executor-abstraction.md) - Session affinity for resume
- [ADR-012: Runner Identity and Registration](./ADR-012-runner-identity-and-registration.md) - Runner identity, properties, and registration
- [ADR-002: Agent Runner Architecture](./ADR-002-agent-runner-architecture.md) - Runner design