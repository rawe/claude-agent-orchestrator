# Architectural Structure Change

## Change Summary

**Changed from**: `bin/` + `lib/` as sibling directories
**Changed to**: `commands/` directory containing both scripts and `lib/` subdirectory

## Directory Structure

### Before
```
agent-orchestrator-cli/
├── bin/
│   ├── ao-new
│   ├── ao-resume
│   └── ... (all commands)
├── lib/
│   ├── config.py
│   ├── session.py
│   └── ... (shared modules)
└── docs/
```

### After
```
agent-orchestrator-cli/
├── commands/
│   ├── ao-new
│   ├── ao-resume
│   ├── ... (all commands)
│   └── lib/
│       ├── config.py
│       ├── session.py
│       └── ... (shared modules)
└── docs/
```

## Rationale

### Problem with Previous Structure
Commands in `bin/` needed to import from sibling `lib/` directory using:
```python
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
```

When distributing as a skill or installing in Claude Code skills folder, maintaining sibling directory relationship was fragile.

### Benefits of New Structure

1. **Self-Contained Distribution**
   - `commands/` folder is fully self-contained
   - Can copy entire folder to `.claude/skills/` or any location
   - No external dependencies on sibling directories

2. **Simpler Import Path**
   - Scripts now use: `Path(__file__).parent / "lib"`
   - One level instead of two - clearer relationship
   - Commands and their dependencies are obviously co-located

3. **Better for `uv` + Skills Pattern**
   - Each script already uses `uv` shebang for dependencies
   - Now `lib/` is clearly "part of" the command distribution
   - Natural fit for Claude Code skills folder structure

4. **Cleaner PATH Management**
   - Add to PATH: `export PATH="$PATH:.../commands"`
   - Everything executable is in one place
   - No confusion about where scripts vs. libraries live

## Technical Changes Made

1. **Directory Operations**
   - Renamed `bin/` → `commands/`
   - Moved `lib/` → `commands/lib/`

2. **Import Path Updates** (all 8 command scripts)
   ```python
   # Before
   sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

   # After
   sys.path.insert(0, str(Path(__file__).parent / "lib"))
   ```

3. **Documentation Updates**
   - All references to `bin/` → `commands/`
   - PATH examples updated
   - Directory structure diagrams updated
   - Import examples updated

## Impact on External Documents

**Architects maintaining separate documentation should update**:

- Directory structure diagrams
- Installation instructions that reference `bin/`
- PATH configuration examples
- Import path examples
- Any references to "bin directory" → "commands directory"

## Backward Compatibility

⚠️ **Breaking change** if anyone has:
- Hardcoded paths to `bin/` directory
- Scripts that import from `lib/` as sibling
- PATH configurations pointing to `bin/`

**Migration**: Update all references from `bin/` to `commands/`

## Design Principle Reinforced

This change strengthens the **progressive disclosure** architecture by making the command collection truly portable and self-contained - ideal for distribution as Claude Code skills where each skill folder should be independent.

---

**Action Required**: If you maintain architectural documentation separately, update all `bin/` references to `commands/` and note that `lib/` is now a subdirectory of `commands/`, not a sibling.
