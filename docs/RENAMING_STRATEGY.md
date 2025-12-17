# Codebase Renaming Strategy

This document captures insights and strategies for systematically renaming terms across the codebase, learned from the "Agent Runtime → Agent Coordinator" rename.

## Overview

Renaming a term across a large codebase requires a systematic approach to:
1. Find all occurrences (including variations)
2. Classify which need changing vs. which are unrelated
3. Update them without breaking functionality
4. Verify completeness

## Phase 1: Discovery - Understanding the Scope

### Step 1: Identify All Variations

A single term appears in multiple forms:

| Form | Example |
|------|---------|
| Title Case | `Agent Runtime` |
| kebab-case | `agent-runtime` |
| snake_case | `agent_runtime` |
| PascalCase | `AgentRuntime` |
| In compound terms | `RuntimeAPIClient`, `--runtime-url`, `logs-runtime` |

**Action:** Create a list of all pattern variations before starting.

### Step 2: Initial Exploration with Subagent

Use an explorer subagent to get a quick overview:
- What files contain the term?
- What types of references exist (code, docs, config)?
- What should be excluded?

This gives context before building tooling.

### Step 3: Identify Exclusions

Determine what should NOT be changed:

| Exclusion Type | Reason |
|----------------|--------|
| Documentation about the rename | `terminology*.md`, `implementation*.md` |
| Historical tickets | `tickets/` folder |
| System folders | `node_modules/`, `.venv/`, `.git/` |
| Lock files | `package-lock.json`, `uv.lock`, `*.lock` |
| Build artifacts | `dist/`, `build/`, `__pycache__/` |
| Same word, different meaning | `RuntimeError`, `at runtime`, `chrome.runtime` |

## Phase 2: Build a Search Script

### Why a Script?

1. **Repeatability** - Run multiple times during the rename process
2. **Classification** - Automatically categorize matches
3. **Verification** - Confirm completion after changes
4. **Future use** - Catch regressions later

### Script Design Principles

```python
# 1. Configure exclusions upfront
EXCLUDED_FOLDERS = {"node_modules", ".venv", ".git", "tickets", ...}
EXCLUDED_FILES = {"package-lock.json", "uv.lock", ...}
EXCLUDED_PATTERNS = [r"^terminology.*\.md$", r"^implementation.*\.md$", ...]

# 2. Search relevant file types only
SEARCHABLE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".md", ".yml", ...}

# 3. Classify matches by type
def classify_match(line: str) -> str:
    # Service-related (NEEDS FIXING)
    if "agent-runtime" in line.lower():
        return "AGENT-RUNTIME-SERVICE"
    # Generic usage (OK TO KEEP)
    if "at runtime" in line.lower():
        return "GENERIC-AT-RUNTIME"
    ...
```

### Classification Categories

**Need Fixing:**
- `AGENT-RUNTIME-SERVICE` - Direct service references
- `RUNTIME-URL-FLAG` - CLI flags like `--runtime-url`
- `RUNTIME-URL-VAR` - Variables like `runtime_url`
- `RUNTIME-API-CLIENT` - Class names like `RuntimeAPIClient`
- `RUNTIME-MAKE-TARGET` - Makefile targets like `logs-runtime`
- `RUNTIME-DATA-VOLUME` - Docker volumes like `runtime-data`

**OK to Keep:**
- `GENERIC-AT-RUNTIME` - "at runtime", "during runtime"
- `GENERIC-ENVIRONMENT` - "runtime environment"
- `NPM-PACKAGE` - "@babel/runtime"
- `BROWSER-URL` - "chrome.runtime", browser APIs
- `GENERIC-OTHER` - `RuntimeError`, exceptions

### Script Output Modes

```bash
# Detailed report (default)
uv run scripts/find-runtime-refs.py

# Count by category
uv run scripts/find-runtime-refs.py --count-only

# JSON for programmatic use
uv run scripts/find-runtime-refs.py --json
```

## Phase 3: Systematic Updates

### Order of Updates

1. **Directories first** - Use `git mv` to preserve history
2. **Core code** - Python/TypeScript source files
3. **Configuration** - Docker, Makefile, env files
4. **Documentation** - README, guides, ADRs
5. **Tests** - Test files and test commands

### Update Strategies

| Scenario | Strategy |
|----------|----------|
| Single occurrence | `Edit` tool with exact match |
| Multiple occurrences in file | `Edit` with `replace_all: true` |
| Bulk documentation updates | Delegate to subagent |
| Mermaid diagrams | Update participant names |

### Watch for Dependencies

Before renaming CLI flags or API parameters:
1. Search for callers that use the old flag
2. Check if environment variables provide backwards compatibility
3. Consider if external scripts depend on it

Example finding: `--runtime-url` flag rename was safe because:
- All test scripts used `-x` (executor) flag instead
- Environment variable `AGENT_ORCHESTRATOR_API_URL` unchanged
- No external shell scripts called the launcher with this flag

## Phase 4: Verification

### Run Script After Each Batch

```bash
# Quick check
uv run scripts/find-runtime-refs.py --count-only

# Detailed check excluding script itself
uv run scripts/find-runtime-refs.py 2>&1 | grep -v "find-runtime-refs.py"
```

### Final Verification Checklist

- [ ] Script shows 0 "NEEDS FIXING" references
- [ ] Services still start correctly
- [ ] Tests pass
- [ ] Documentation renders correctly (Mermaid diagrams)

## Key Insights

### 1. Same Word, Different Meanings

The word "runtime" appears in multiple contexts:
- **Service name** - "Agent Runtime" (rename)
- **Execution time** - "at runtime" (keep)
- **Exceptions** - `RuntimeError` (keep)
- **Browser APIs** - `chrome.runtime` (keep)
- **NPM packages** - `@babel/runtime` (keep)

**Lesson:** Classification logic in the script is critical.

### 2. Mermaid Diagrams Need Attention

Sequence diagrams use participant aliases:
```mermaid
participant Runtime as Agent Coordinator
```
The short name "Runtime" appears throughout the diagram. Must update both the alias and all references.

### 3. CLI Flags Have Ripple Effects

Renaming `--runtime-url` to `--coordinator-url` requires checking:
- Documentation examples
- Test scripts
- Any automation that calls the CLI

### 4. Lock Files Are Read-Only

`uv.lock` contains the package name from `pyproject.toml`. After updating `pyproject.toml`, the lock file updates automatically on next `uv run`.

### 5. Iterative Approach Works Best

1. Run script → Find issues
2. Fix a batch of issues
3. Run script → Verify and find remaining
4. Repeat until clean

### 6. Subagents for Detection Only, Not Modification

Use subagents only for discovery and verification, never for making changes:

| Subagent Should | Subagent Should NOT |
|-----------------|---------------------|
| Search for occurrences | Edit files |
| Classify matches | Create new files |
| Report findings | Rename files |
| Verify completion | Run `git mv` |

**Why:** When subagents modify files, the main agent loses awareness of what changed. Mistakes happen silently and are harder to catch. Keeping all modifications in the main agent ensures full control and immediate verification.

### 7. "OK to Keep" Requires Scrutiny in Project Docs

Terms in our own project's documentation/comments often need changing even when they look generic:

| Example | Looks Like | Actually Is |
|---------|-----------|-------------|
| "Jobs not executing" (troubleshooting section) | Generic troubleshooting | Our Jobs/Runs terminology |
| "sessions, events, jobs" (env comment) | Feature list | Our Jobs/Runs terminology |
| "Jobs API" (code comment) | Generic API mention | Our Jobs/Runs API |

**Lesson:** If it's in our codebase describing our system, it probably needs changing.

## Template for Future Renames

```bash
# 1. Create search script (copy and modify find-runtime-refs.py)
cp scripts/find-runtime-refs.py scripts/find-TERM-refs.py

# 2. Update the script:
#    - Change search pattern
#    - Update classification logic
#    - Adjust exclusions if needed

# 3. Run initial scan
uv run scripts/find-TERM-refs.py --count-only

# 4. Fix in batches, verify after each
uv run scripts/find-TERM-refs.py

# 5. Final verification
uv run scripts/find-TERM-refs.py --count-only
# Should show 0 in "NEEDS FIXING" categories
```

## Files Created

- `scripts/find-runtime-refs.py` - Reusable search script (modify for other terms)
- `docs/RENAMING_STRATEGY.md` - This document

## Summary

| Phase | Action |
|-------|--------|
| Discovery | Explore with subagent, identify variations and exclusions |
| Tooling | Build a search script with classification |
| Updates | Systematic changes in order (dirs → code → config → docs → tests) |
| Verification | Run script repeatedly until clean |

The script-based approach transforms a tedious manual search into a repeatable, verifiable process.
