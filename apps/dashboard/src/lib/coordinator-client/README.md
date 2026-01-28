# Coordinator Client SDK

Lightweight SDK for programmatic interaction with the Agent Coordinator API.

## Quick Start

```typescript
import { CoordinatorClient } from '@/lib/coordinator-client';

const client = new CoordinatorClient({
  baseUrl: 'http://localhost:8765',
  getToken: async () => getAccessToken(), // Optional, for auth
});

// Start a run
const run = await client.startRun({
  parameters: { prompt: 'Hello, help me with a task' },
});

// Wait for completion (polls every 1s)
const result = await run.waitForResult();

if (result.status === 'completed') {
  console.log(result.resultText);
}
```

## API

### `CoordinatorClient`

```typescript
const client = new CoordinatorClient({
  baseUrl: string,              // Required: API base URL
  getToken?: () => Promise<string | null>,  // Optional: auth token getter
});
```

**Methods:**

| Method | Description |
|--------|-------------|
| `startRun(options)` | Start a new run, returns `RunHandle` |
| `resumeSession(sessionId, params)` | Resume existing session, returns `RunHandle` |

### `StartRunOptions`

```typescript
{
  parameters: Record<string, unknown>,  // Required: input params (e.g., { prompt: "..." })
  agentName?: string,                   // Optional: specific agent, omit for generic
  projectDir?: string,                  // Optional: project directory context
}
```

### `RunHandle`

```typescript
const run = await client.startRun({ ... });

run.runId;       // Run ID
run.sessionId;   // Session ID

await run.waitForResult();  // Poll until complete, returns RunResult
await run.stop();           // Stop the run
```

### `RunResult`

```typescript
{
  status: 'completed' | 'failed' | 'stopped',
  resultText?: string,
  resultData?: Record<string, unknown>,
  error?: string,
}
```

## Example: AI-Assisted Script Creation

```typescript
import { CoordinatorClient } from '@/lib/coordinator-client';

const client = new CoordinatorClient({ baseUrl: API_URL });

async function generateScript(
  currentScript: string,
  schema: object | null,
  userRequest: string
): Promise<string> {
  const prompt = `You are a script assistant.

Current script content:
\`\`\`
${currentScript}
\`\`\`

Parameter schema:
${schema ? JSON.stringify(schema, null, 2) : 'None defined'}

User request: ${userRequest}

Return ONLY the updated script content, no explanations.`;

  const run = await client.startRun({
    parameters: { prompt },
  });

  const result = await run.waitForResult();

  if (result.status !== 'completed') {
    throw new Error(result.error || 'Generation failed');
  }

  return result.resultText || '';
}
```
