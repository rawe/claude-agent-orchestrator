# Session 5: Dashboard

**Component:** `dashboard/src/`

## Objective

Update TypeScript types and UI components to reflect the renamed `executor_profile` field and display the new `executor` object details.

## Prerequisites

- **Session 3 complete**: Coordinator API returns new fields

## Files to Modify

| File | Change |
|------|--------|
| `types/runner.ts` | Rename field, add `executor` type |
| `types/agent.ts` | Update demands type |
| `types/session.ts` | Rename field |
| `types/run.ts` | Update demands type |
| `pages/Runners.tsx` | Display executor details |
| `components/features/agents/AgentEditor.tsx` | Update demand form field |
| `utils/mcpTemplates.ts` | Update demand template |
| `services/runnerService.ts` | Update if needed |
| `services/unifiedViewService.ts` | Update field mappings |

## Key Changes

### 1. Types (types/runner.ts)

```typescript
export interface ExecutorDetails {
  type: string;
  command: string;
  config: Record<string, unknown>;
}

export interface Runner {
  runner_id: string;
  hostname: string;
  project_dir: string;
  executor_profile: string | null;  // Was executor_type
  executor?: ExecutorDetails;       // NEW
  tags: string[];
  require_matching_tags?: boolean;  // NEW
  // ... other fields
}
```

### 2. Types (types/agent.ts, run.ts)

Update demands interface:

```typescript
export interface Demands {
  executor_profile?: string;  // Was executor_type
  tags?: string[];
  hostname?: string;
  project_dir?: string;
}
```

### 3. Runners Page (pages/Runners.tsx)

Display the new executor details. Current display likely shows:

```tsx
<div>Executor: {runner.executor_type}</div>
```

Update to show profile and details:

```tsx
<div>Profile: {runner.executor_profile}</div>
{runner.executor && (
  <div>
    <div>Type: {runner.executor.type}</div>
    <div>Command: {runner.executor.command}</div>
    {Object.keys(runner.executor.config || {}).length > 0 && (
      <details>
        <summary>Config</summary>
        <pre>{JSON.stringify(runner.executor.config, null, 2)}</pre>
      </details>
    )}
  </div>
)}
```

### 4. Agent Editor (components/features/agents/AgentEditor.tsx)

Update the demands form field:

- Label: "Executor Type" → "Executor Profile"
- Field name: `executor_type` → `executor_profile`
- Help text: Update to explain profiles

### 5. MCP Templates (utils/mcpTemplates.ts)

Update the demand template JSON:

```typescript
// Was
demands: { executor_type: "claude-code", tags: [] }

// Now
demands: { executor_profile: "coding", tags: [] }
```

## Search for All References

Run this to find all `executor_type` references:

```bash
grep -r "executor_type" dashboard/src/ --include="*.ts" --include="*.tsx"
```

Update each occurrence.

## Design Doc References

- **Registration payload**: `docs/design/executor-profiles.md` lines 195-236
- **Coordinator Behavior** (what's exposed in API): lines 239-257

## Testing

1. Start coordinator with new fields
2. Register a runner with profile
3. Open dashboard at `http://localhost:3000`
4. Verify:
   - Runners page shows `executor_profile` and `executor` details
   - Agent editor has "Executor Profile" field
   - No TypeScript errors (`npm run build`)

```bash
cd dashboard
npm run build  # Check for type errors
npm run dev    # Visual verification
```

## Definition of Done

- [ ] All `executor_type` references renamed to `executor_profile`
- [ ] New `ExecutorDetails` type defined
- [ ] Runner interface includes `executor` and `require_matching_tags`
- [ ] Runners page displays executor details
- [ ] Agent editor form field updated
- [ ] MCP templates updated
- [ ] No TypeScript compilation errors
- [ ] Visual verification in browser
