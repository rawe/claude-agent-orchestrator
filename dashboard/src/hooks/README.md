# Hooks

## useAiAssist

Reusable hook for AI-assisted field editing via Agent Coordinator.

### Basic Usage

```tsx
import { useAiAssist } from '@/hooks/useAiAssist';

// Define your input/output types
interface MyInput {
  content: string;
  user_request?: string;
}

interface MyOutput {
  result: string;
  remarks?: string;
}

function MyComponent() {
  const ai = useAiAssist<MyInput, MyOutput>({
    agentName: 'my-assistant',
    buildInput: (userRequest) => ({
      content: getFieldValue(),
      user_request: userRequest,
    }),
    defaultRequest: 'Check for issues',
  });

  const handleAccept = () => {
    if (ai.result) {
      setFieldValue(ai.result.result);
    }
    ai.accept();
  };

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={ai.toggle}
        disabled={!ai.available || ai.checkingAvailability || ai.isLoading}
        title={ai.unavailableReason || 'AI Assistant'}
      >
        {ai.isLoading || ai.checkingAvailability ? 'Loading...' : 'AI'}
      </button>

      {/* User input */}
      {ai.showInput && (
        <input
          value={ai.userRequest}
          onChange={(e) => ai.setUserRequest(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ai.submit()}
        />
        <button onClick={ai.submit}>Send</button>
      )}

      {/* Error */}
      {ai.error && <div>{ai.error} <button onClick={ai.clearError}>×</button></div>}

      {/* Result preview */}
      {ai.result && (
        <div>
          <pre>{ai.result.result}</pre>
          <button onClick={handleAccept}>Accept</button>
          <button onClick={ai.reject}>Reject</button>
        </div>
      )}
    </>
  );
}
```

### Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `agentName` | `string` | Yes | Agent to call |
| `buildInput` | `(userRequest: string) => TInput` | Yes | Build input from user request |
| `defaultRequest` | `string` | No | Default if user input empty (default: "Check for issues") |

### Return Values

| Property | Type | Description |
|----------|------|-------------|
| `available` | `boolean` | Whether agent exists and is ready |
| `checkingAvailability` | `boolean` | Initial availability check in progress |
| `unavailableReason` | `string \| null` | Message explaining why unavailable |
| `showInput` | `boolean` | Whether input field is visible |
| `userRequest` | `string` | Current user input |
| `isLoading` | `boolean` | Request in progress |
| `result` | `TOutput \| null` | AI result (structured) |
| `error` | `string \| null` | Error message |
| `setUserRequest` | `(v: string) => void` | Update user input |
| `toggle` | `() => void` | Show/hide input |
| `submit` | `() => Promise<void>` | Send request |
| `cancel` | `() => void` | Cancel ongoing request |
| `accept` | `() => void` | Clear result (call after applying) |
| `reject` | `() => void` | Dismiss result |
| `clearError` | `() => void` | Clear error |

### Integration Pattern

1. **Define agent** with input/output schemas in Coordinator
2. **Define TypeScript types** matching schemas
3. **Use hook** with `buildInput` gathering data from your form/state
4. **Render UI** using hook's state and actions
5. **Apply result** in your `handleAccept`, then call `ai.accept()`

---

## useAiGroup

Aggregates multiple `useAiAssist` instances for unified state management.
Use when a component has multiple AI buttons and needs to protect Save/Close when any AI is loading.

### Usage

```tsx
import { useAiAssist } from '@/hooks/useAiAssist';
import { useAiGroup } from '@/hooks/useAiGroup';

function MyEditor() {
  // Individual named AI instances
  const scriptAssistantAi = useAiAssist({ agentName: 'script-assistant', ... });
  const schemaAssistantAi = useAiAssist({ agentName: 'schema-assistant', ... });

  // Aggregate for unified protection
  const ai = useAiGroup([scriptAssistantAi, schemaAssistantAi]);

  return (
    <Modal onClose={() => { if (!ai.isAnyLoading) onClose(); }}>
      {/* Individual AI buttons use their own instance */}
      {scriptAssistantAi.isLoading ? (
        <button onClick={scriptAssistantAi.cancel}>Cancel</button>
      ) : (
        <button onClick={scriptAssistantAi.toggle}>Script AI</button>
      )}

      {/* Protection uses aggregated state */}
      <Button disabled={ai.isAnyLoading}>Save</Button>
      <Button onClick={onClose} disabled={ai.isAnyLoading}>Close</Button>
    </Modal>
  );
}
```

### Return Values

| Property | Type | Description |
|----------|------|-------------|
| `isAnyLoading` | `boolean` | True if any AI instance is loading |
| `hasAnyResult` | `boolean` | True if any AI instance has a pending result |
| `hasAnyError` | `boolean` | True if any AI instance has an error |
| `cancelAll` | `() => void` | Cancel all loading AI instances |
| `count` | `number` | Number of registered AI instances |

### Pattern

1. **Create named AI instances** with `useAiAssist` for each AI button
2. **Aggregate with `useAiGroup`** passing array of instances
3. **Use individual instances** for button-specific UI (toggle, cancel, result)
4. **Use aggregated `ai`** for component-level protection (Save, Close, Modal backdrop)
