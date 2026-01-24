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
| `accept` | `() => void` | Clear result (call after applying) |
| `reject` | `() => void` | Dismiss result |
| `clearError` | `() => void` | Clear error |

### Integration Pattern

1. **Define agent** with input/output schemas in Coordinator
2. **Define TypeScript types** matching schemas
3. **Use hook** with `buildInput` gathering data from your form/state
4. **Render UI** using hook's state and actions
5. **Apply result** in your `handleAccept`, then call `ai.accept()`
