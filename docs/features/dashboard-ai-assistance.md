# Dashboard AI Assistance

**Status:** Implemented
**Created:** 2025-01-24

## Overview

The Dashboard includes built-in AI assistance features that help users create and edit content. These features are powered by "system agents" - internal agents managed by the dashboard itself, separate from user-defined project agents.

## Architecture

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Coordinator Client SDK | `dashboard/src/lib/coordinator-client/` | Programmatic API interaction |
| System Agents Registry | `dashboard/src/lib/system-agents/` | Agent definitions and provisioning |
| AI Assist Hook | `dashboard/src/hooks/useAiAssist.ts` | Reusable React hook for AI interactions |

### Data Flow

```
User interacts with AI button
         │
         ▼
useAiAssist hook manages state
         │
         ▼
CoordinatorClient sends request
         │
         ▼
System agent processes request
         │
         ▼
Structured output returned
         │
         ▼
Component applies result to form
```

## System Agents

System agents are internal agents that the dashboard requires for AI features. They are:

- Defined in code (not manually created)
- Tagged with `internal` for identification
- Provisioned via Settings page
- Have defined input/output schemas

### Registry Structure

```
dashboard/src/lib/system-agents/
├── index.ts              # Main exports
├── registry.ts           # Aggregates all agent definitions
├── manager.ts            # Provisioning service
└── agents/
    └── script-assistant.ts   # Agent definition + types
```

### Current System Agents

| Agent | Purpose | Used By |
|-------|---------|---------|
| `script-assistant` | Create new scripts or review/improve existing scripts | ScriptEditor |

## Coordinator Client SDK

Lightweight SDK for programmatic interaction with the Coordinator API.

**Location:** `dashboard/src/lib/coordinator-client/`

**Key exports:**
- `CoordinatorClient` - Main client class
- `RunHandle` - Handle to track/wait for runs

**Documentation:** `dashboard/src/lib/coordinator-client/README.md`

## useAiAssist Hook

Reusable React hook that encapsulates AI assist state and interactions.

**Location:** `dashboard/src/hooks/useAiAssist.ts`

**Manages:**
- Input visibility toggle
- User request text
- Loading state
- Result state
- Error state
- Cancellation

**Documentation:** `dashboard/src/hooks/README.md`

## Cancellation and UI Protection

### Cancel Functionality

The `useAiAssist` hook provides a `cancel()` function to abort ongoing AI requests:

- Sets `isLoading` to false immediately
- Clears pending state (result, error, userRequest)
- Ignores any results that arrive after cancellation

**Usage:**
```tsx
{ai.isLoading ? (
  <button onClick={ai.cancel}>Cancel</button>
) : (
  <button onClick={ai.toggle}>AI</button>
)}
```

### UI Protection Pattern

When AI is loading, the UI must be protected to prevent accidental actions:

| Element | Protection |
|---------|------------|
| Save button | `disabled={ai.isAnyLoading}` |
| Close button | `disabled={ai.isAnyLoading}` |
| X button (header) | `disabled={ai.isAnyLoading}` |
| Modal backdrop | `onClose={() => { if (!ai.isAnyLoading) onClose(); }}` |

Users must explicitly click Cancel to abort the AI operation before they can close or save.

### API Cancellation

**Status:** Implemented

The `cancel()` function sends a stop request to the Coordinator API via `RunHandle.stop()` to terminate the agent run.

**Implementation:** `dashboard/src/hooks/useAiAssist.ts`, inside the `cancel` callback:

```typescript
// Send stop request to Coordinator to terminate the agent run
if (currentRunRef.current) {
  currentRunRef.current.stop().catch((err) => {
    // Log but don't surface to user - UI is already reset
    console.warn('Failed to stop run:', err);
  });
}
```

**How it works:**
1. The `currentRunRef` stores the active `RunHandle` during a run
2. When `cancel()` is called, it invokes `RunHandle.stop()` which POSTs to `/sessions/{sessionId}/stop`
3. The Coordinator queues a stop command for the runner
4. Errors are logged but not surfaced to the user since the UI has already reset

## useAiGroup Hook

Aggregates multiple `useAiAssist` instances for unified state management.

**Location:** `dashboard/src/hooks/useAiGroup.ts`

**Purpose:** When a component has multiple AI buttons (e.g., one for script, one for schema), the group provides unified protection state.

**Usage:**
```tsx
// Individual named AI instances
const scriptAssistantAi = useAiAssist({ agentName: 'script-assistant', ... });
const schemaAssistantAi = useAiAssist({ agentName: 'schema-assistant', ... });

// Aggregate for unified protection
const ai = useAiGroup([scriptAssistantAi, schemaAssistantAi]);

// Individual buttons use their own instance
<button onClick={scriptAssistantAi.toggle}>Script AI</button>
<button onClick={schemaAssistantAi.toggle}>Schema AI</button>

// Protection uses aggregated state
<Button disabled={ai.isAnyLoading}>Save</Button>
```

**Returns:**
| Property | Type | Description |
|----------|------|-------------|
| `isAnyLoading` | `boolean` | True if any AI instance is loading |
| `hasAnyResult` | `boolean` | True if any AI instance has a pending result |
| `hasAnyError` | `boolean` | True if any AI instance has an error |
| `cancelAll` | `() => void` | Cancel all loading AI instances |
| `count` | `number` | Number of registered AI instances |

## Extending with New Agents

### Step 1: Create Agent Definition

Create a new file in `dashboard/src/lib/system-agents/agents/`:

**Required exports:**
- TypeScript interfaces for input and output
- Type-safe key constants for field access
- Agent definition object with:
  - `name` - unique identifier
  - `description` - human-readable description
  - `tags` - should include `internal`
  - `systemPrompt` - agent instructions
  - `inputSchema` - JSON Schema for input
  - `outputSchema` - JSON Schema for output

**Reference:** `dashboard/src/lib/system-agents/agents/script-assistant.ts`

### Step 2: Register Agent

1. Export from `dashboard/src/lib/system-agents/index.ts`
2. Add to `systemAgentRegistry` in `dashboard/src/lib/system-agents/registry.ts`

### Step 3: Use in Component

1. Import types and keys from `@/lib/system-agents`
2. Use `useAiAssist` hook with agent name and `buildInput` function
3. Implement accept handler to apply structured output to form
4. Render UI using hook state (toggle, input, result, error)

**Reference:** `dashboard/src/components/features/scripts/ScriptEditor.tsx`

### Step 4: Provision Agent

Navigate to Settings page and click "Provision System Agents" to create/update the agent in the Coordinator.

## Provisioning

System agents can be provisioned (created or updated) from the Settings page.

**Location:** `dashboard/src/pages/Settings.tsx` (System Agents section)

**Behavior:**
- Creates agent if it doesn't exist
- Updates agent if definition changed
- Shows result for each agent (created/updated/error)

## Key Design Decisions

### Why System Agents?

- Agents needed by dashboard are application-specific, not project-specific
- Ensures required agents exist with correct configuration
- Separates infrastructure concerns from user-managed agents

### Why Structured Output?

- Differentiates actionable content from AI remarks
- Enables precise field updates (e.g., update both script and schema)
- Type-safe handling in TypeScript

### Why useAiAssist Hook?

- Separates state management from UI rendering
- Reusable across different components
- Components control their own preview/accept UI

## Related Files

| File | Description |
|------|-------------|
| `dashboard/src/lib/coordinator-client/` | SDK for Coordinator API |
| `dashboard/src/lib/system-agents/` | System agent definitions and provisioning |
| `dashboard/src/hooks/useAiAssist.ts` | Reusable AI assist hook |
| `dashboard/src/hooks/useAiGroup.ts` | Aggregates multiple AI instances |
| `dashboard/src/hooks/README.md` | Hook documentation |
| `dashboard/src/components/features/scripts/ScriptEditor.tsx` | Example integration |
| `dashboard/src/pages/Settings.tsx` | Provisioning UI |
