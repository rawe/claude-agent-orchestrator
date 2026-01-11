# ADR-012: Runner Identity and Registration

**Status:** Accepted
**Date:** 2025-12-18
**Decision Makers:** Architecture Review
**Related:** [ADR-011: Runner Capabilities and Run Demands](./ADR-011-runner-capabilities-and-run-demands.md)

## Context

The Agent Runner registration process needs to handle:

1. **Initial registration**: Runner connects for the first time
2. **Reconnection**: Runner restarts and connects again
3. **Lifecycle management**: Detecting stale/offline runners
4. **Identity**: How runners are identified across sessions

### Current Behavior

- Runner calls `POST /runner/register` without an ID
- Coordinator generates a random `runner_id` and returns it
- Runner uses this ID for subsequent calls

### Problems

1. **No reconnection recognition**: If a runner restarts, it gets a NEW runner_id
2. **Stale accumulation**: Old runner_ids accumulate without cleanup
3. **Identity confusion**: Same physical runner appears as multiple runners after restarts

## Decision

### 1. Runner Identity Model

**External API**: Runners receive a `runner_id` from the coordinator and use it for all API interactions.

**Internal Implementation**: The `runner_id` is deterministically derived from the runner's identifying properties:

```
runner_id = f"lnch_{deterministic_hash(hostname, project_dir, executor_type)[:12]}"
```

This is an **encapsulated implementation detail** - runners don't know how the ID is generated.

### 2. Identifying Properties

Three properties uniquely identify a runner:

| Property | Purpose | Example |
|----------|---------|---------|
| `hostname` | Which machine | `"my-macbook"` |
| `project_dir` | Which directory | `"/Users/me/projects/app"` |
| `executor_type` | Which executor | `"claude-code"` |

**Constraint**: Only ONE runner can exist per (hostname, project_dir, executor_type) tuple.

### 3. Registration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Runner registers:                                                          │
│                                                                             │
│  POST /runner/register                                                      │
│  {                                                                          │
│      "hostname": "my-macbook",                                              │
│      "project_dir": "/Users/me/projects/app",                               │
│      "executor_type": "claude-code",                                        │
│      "tags": ["python", "docker"]                                           │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Coordinator (internal):                                                    │
│                                                                             │
│  1. Derive runner_id from properties:                                       │
│     runner_id = derive_runner_id(hostname, project_dir, executor_type)      │
│                                                                             │
│  2. Check if runner exists:                                                 │
│     EXISTS  → Reconnection: update status to 'online', update heartbeat     │
│     NEW     → First registration: create runner record                      │
│                                                                             │
│  3. Return runner_id to runner                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Response:                                                                  │
│                                                                             │
│  { "runner_id": "lnch_abc123def4" }                                         │
│                                                                             │
│  Runner uses this ID for all subsequent API calls                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. ID Derivation (Internal)

```python
import hashlib

def derive_runner_id(hostname: str, project_dir: str, executor_type: str) -> str:
    """
    Deterministically derive runner_id from identifying properties.

    Same properties always produce same ID (enables reconnection recognition).
    This is an internal implementation detail, not exposed to runners.
    """
    # Normalize inputs
    key = f"{hostname}:{project_dir}:{executor_type}"

    # Generate deterministic hash
    hash_bytes = hashlib.sha256(key.encode()).hexdigest()

    # Format with prefix
    return f"lnch_{hash_bytes[:12]}"
```

**Example:**
```
hostname="my-macbook", project_dir="/code", executor_type="claude-code"
    ↓
key = "my-macbook:/code:claude-code"
    ↓
hash = sha256(key) = "a1b2c3d4e5f6..."
    ↓
runner_id = "lnch_a1b2c3d4e5f6"
```

Same input always produces same output → automatic reconnection recognition.

### 5. Lifecycle States

Simple three-state model:

```
┌──────────┐     heartbeat      ┌──────────┐
│  online  │◄───────────────────│  online  │
└────┬─────┘                    └──────────┘
     │
     │ no heartbeat for X minutes
     ▼
┌──────────┐
│  stale   │
└────┬─────┘
     │
     │ no heartbeat for Y minutes
     ▼
┌──────────┐
│ (removed)│  ← Runner record deleted
└──────────┘
```

**Thresholds (configurable):**
- `online` → `stale`: No heartbeat for 2 minutes
- `stale` → removed: No heartbeat for 10 minutes

**Reconnection:**
- Runner with same (hostname, project_dir, executor_type) registers
- Same runner_id is derived
- Status updated to `online`
- If record was removed: recreated with same runner_id

### 6. Data Model

```python
class Runner(BaseModel):
    # Identity (derived internally, exposed externally)
    runner_id: str

    # Identifying properties (used for ID derivation)
    hostname: str
    project_dir: str
    executor_type: str

    # Capabilities (what the runner can do)
    tags: list[str] = []

    # Status
    status: Literal["online", "stale"]
    registered_at: str
    last_heartbeat: str
```

### 7. API Contract

**Registration:**
```
POST /runner/register
Request:
{
    "hostname": "my-macbook",
    "project_dir": "/Users/me/projects/app",
    "executor_type": "claude-code",
    "tags": ["python", "docker"]
}

Response:
{
    "runner_id": "lnch_a1b2c3d4e5f6"
}
```

**Subsequent calls use runner_id:**
```
GET /runner/runs?runner_id=lnch_a1b2c3d4e5f6
POST /runner/heartbeat?runner_id=lnch_a1b2c3d4e5f6
```

**List runners (includes derived ID):**
```
GET /runners

Response:
{
    "runners": [
        {
            "runner_id": "lnch_a1b2c3d4e5f6",
            "hostname": "my-macbook",
            "project_dir": "/Users/me/projects/app",
            "executor_type": "claude-code",
            "tags": ["python", "docker"],
            "status": "online",
            "last_heartbeat": "2025-12-18T10:30:00Z"
        }
    ]
}
```

## Rationale

### Why Deterministic ID Derivation?

| Approach | Reconnection | Complexity | Security |
|----------|--------------|------------|----------|
| Random ID each time | ❌ No recognition | Simple | N/A |
| Runner-provided ID | ✅ Works | Simple | ❌ Impersonation risk |
| Shared secret exchange | ✅ Works | Complex | ✅ Secure |
| **Deterministic derivation** | ✅ Works | Simple | ✅ No impersonation |

Deterministic derivation gives us reconnection recognition without shared secrets:
- Same runner always gets same ID (recognition works)
- Can't impersonate (would need same hostname + project_dir + executor_type)
- Simple implementation (no secret storage/exchange)

### Why Remove Instead of Archive?

Keeping history adds complexity:
- Need archive table
- Need cleanup policies
- Queries become more complex

Simple removal is sufficient:
- If runner reconnects, record is recreated with same derived ID
- No history needed for current use cases
- Can add archival later if needed

### Why These Three Identifying Properties?

```
hostname      → Physical/virtual machine boundary
project_dir   → Working directory boundary
executor_type → Executor implementation boundary
```

Together they answer: "WHERE is this runner, and WHAT type is it?"

This tuple is:
- **Unique enough**: Can't have two identical runners
- **Stable**: Doesn't change during runner lifetime
- **Meaningful**: Maps to physical deployment reality

## Consequences

### Positive

- **Automatic reconnection**: Same runner properties = same ID
- **Clean lifecycle**: Simple states, automatic cleanup
- **No secrets**: Deterministic derivation without authentication complexity
- **Stable IDs**: Runner ID survives restarts
- **Simple API**: Runner just provides properties, gets ID back

### Negative

- **No true authentication**: A malicious actor with same hostname/project/executor could impersonate
- **Property changes = new runner**: Changing project_dir creates a "new" runner
- **Single runner per tuple**: Can't have two runners with same (hostname, project_dir, executor_type)

### Neutral

- ID derivation is an internal detail (could change without API impact)
- Cleanup runs periodically (background task needed)

## Future Enhancements

### Shared Secret Authentication (Not in Scope)

For production deployments requiring stronger security:

```
1. First registration:
   Runner → POST /runner/register { hostname, project_dir, executor_type }
   Coordinator → { runner_id, shared_secret }  # One-time secret

2. Subsequent connections:
   Runner → POST /runner/connect { runner_id, proof_of_secret }
   Coordinator → Validates secret, returns session token
```

This adds:
- Protection against impersonation
- Revocation capability (invalidate secret)
- Audit trail (which secret was used)

Deferred because:
- Adds significant complexity
- Current deployment model (single user, local network) doesn't require it
- Can be added later without breaking existing runners

## References

- [ADR-006: Runner Registration with Health Monitoring](./ADR-006-runner-registration-health-monitoring.md) - Current registration (superseded)
- [ADR-011: Runner Capabilities and Run Demands](./ADR-011-runner-capabilities-and-run-demands.md) - Capability matching
- [ADR-010: Session Identity and Executor Abstraction](./ADR-010-session-identity-and-executor-abstraction.md) - Session affinity
