# Session 3: Agent Coordinator

**Component:** `servers/agent-coordinator/` + `config/agents/`

## Objective

Rename `executor_type` to `executor_profile` across the coordinator, add new registration fields (`executor` object, `require_matching_tags`), update demand matching, and update agent blueprints.

## Prerequisites

- **Session 2 complete**: Runner sends new registration payload

## Files to Modify

| File | Change |
|------|--------|
| `models.py` | Rename `executor_type` → `executor_profile` in models |
| `database.py` | Rename column, update queries |
| `services/runner_registry.py` | Update `RunnerInfo`, registration logic |
| `services/run_queue.py` | Update demand matching, add tag filtering |
| `main.py` | Update API endpoints |
| `config/agents/*/agent.json` | Update `demands.executor_type` → `demands.executor_profile` |

## Scope of Rename

Search for `executor_type` in the codebase. Expected locations:

| Location | Count | Change |
|----------|-------|--------|
| `models.py` | ~7 | Field rename in dataclasses/models |
| `database.py` | ~7 | Column name + SQL queries |
| `runner_registry.py` | ~13 | `RunnerInfo`, `register_runner()`, `derive_runner_id()` |
| `run_queue.py` | ~2 | `DemandFields`, matching logic |
| `main.py` | ~8 | API request/response models |

## Key Changes

### 1. Models (models.py)

```python
class RunnerDemands(BaseModel):
    executor_profile: Optional[str] = None  # Was executor_type
    tags: List[str] = []
```

Apply same rename to: `SessionBind`, `SessionMetadataUpdate`, any other models using `executor_type`.

### 2. Database (database.py)

Rename column in schema and all queries:

```sql
-- Was: executor_type TEXT
CREATE TABLE sessions (
    ...
    executor_profile TEXT,
    ...
)
```

Update all SQL queries that reference `executor_type`.

### 3. Runner Registry (services/runner_registry.py)

Update `RunnerInfo` to include new fields:

```python
@dataclass
class RunnerInfo:
    runner_id: str
    hostname: str
    project_dir: str
    executor_profile: str      # Was executor_type
    executor: dict             # NEW: { type, command, config }
    tags: list[str]
    require_matching_tags: bool = False  # NEW
    # ... other fields
```

Update `derive_runner_id()` if it uses executor_type.

### 4. Run Queue / Demand Matching (services/run_queue.py)

```python
class DemandFields:
    EXECUTOR_PROFILE = "executor_profile"  # Was EXECUTOR_TYPE
    # ...

def capabilities_satisfy_demands(runner: RunnerInfo, demands: Optional[dict]) -> bool:
    # Rename field access
    demanded_profile = demands.get(DemandFields.EXECUTOR_PROFILE)
    if demanded_profile and runner.executor_profile != demanded_profile:
        return False

    # NEW: require_matching_tags logic
    if runner.require_matching_tags:
        run_tags = set(demands.get("tags", []))
        runner_tags = set(runner.tags)
        if not run_tags or not run_tags.intersection(runner_tags):
            return False

    # ... existing tag matching ...
```

### 5. API Endpoints (main.py)

Update registration request model:

```python
class RunnerRegisterRequest(BaseModel):
    hostname: str
    project_dir: str
    executor_profile: str           # Was executor_type
    executor: dict                  # NEW
    tags: Optional[list[str]] = []
    require_matching_tags: bool = False  # NEW
```

Update all endpoints that return runner data to include new fields.

### 6. Agent Blueprints (config/agents/)

Update each `agent.json`:

```json
{
  "demands": {
    "executor_profile": "coding"
  }
}
```

Was:
```json
{
  "demands": {
    "executor_type": "claude-code"
  }
}
```

## Design Doc References

- **Registration payload**: lines 195-236
- **Coordinator Behavior**: lines 239-257
- **Demand Matching**: lines 259-294
- **Tagged-Only Mode**: lines 296-336
- **Migration notes**: lines 639-669

## Tagged-Only Mode Logic

New `require_matching_tags` field on runners:

| Runner Tags | Run Tags | `require_matching_tags` | Result |
|-------------|----------|------------------------|--------|
| `["python", "docker"]` | `["python"]` | `true` | Match |
| `["python", "docker"]` | `["nodejs"]` | `true` | No match |
| `["python", "docker"]` | `[]` | `true` | Rejected |
| `["python", "docker"]` | `[]` | `false` | Accepted |

Rule: Require **at least one** matching tag (not all).

## Testing

```bash
# Start coordinator
cd servers/agent-coordinator && AUTH_ENABLED=false uv run python -m main

# Register runner with new fields
curl -X POST http://localhost:8765/runner/register \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "test",
    "project_dir": "/tmp",
    "executor_profile": "coding",
    "executor": {"type": "claude-code", "command": "...", "config": {}},
    "tags": ["python"]
  }'

# Verify runner list shows new fields
curl http://localhost:8765/runners

# Test demand matching with updated blueprint
```

## Definition of Done

- [ ] `executor_type` renamed to `executor_profile` everywhere
- [ ] New `executor` object field stored and returned in API
- [ ] New `require_matching_tags` field with filtering logic
- [ ] Database schema updated (column rename)
- [ ] All SQL queries updated
- [ ] Demand matching uses `executor_profile`
- [ ] Agent blueprints updated
- [ ] API responses include new fields
- [ ] Integration test with runner + blueprint

## Database Migration Note

For existing databases, you may need a migration:

```sql
ALTER TABLE sessions RENAME COLUMN executor_type TO executor_profile;
```

Or recreate the database for development.
