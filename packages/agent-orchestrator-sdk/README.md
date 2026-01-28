# @rawe/agent-orchestrator-sdk

[![npm version](https://img.shields.io/npm/v/@rawe/agent-orchestrator-sdk.svg)](https://www.npmjs.com/package/@rawe/agent-orchestrator-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

TypeScript SDK for the [Agent Orchestrator](https://github.com/rawe/claude-agent-orchestrator) - a framework for orchestrating AI agent workflows.

## Installation

```bash
npm install @rawe/agent-orchestrator-sdk
```

## Quick Start

```typescript
import { CoordinatorClient } from '@rawe/agent-orchestrator-sdk';

const client = new CoordinatorClient({
  baseUrl: 'http://localhost:8765',
});

// Start an agent run
const run = await client.startRun({
  parameters: { prompt: 'Help me with a task' },
});

// Wait for completion
const result = await run.waitForResult();

if (result.status === 'completed') {
  console.log(result.resultText);
}
```

## Authentication

For authenticated endpoints, provide a token getter:

```typescript
const client = new CoordinatorClient({
  baseUrl: 'http://localhost:8765',
  getToken: async () => {
    // Return your auth token (e.g., from Auth0, OAuth, etc.)
    return await getAccessToken();
  },
});
```

## API Reference

### CoordinatorClient

Main client for interacting with the Agent Orchestrator.

```typescript
const client = new CoordinatorClient(config: CoordinatorClientConfig);
```

#### Configuration

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `baseUrl` | `string` | Yes | Agent Orchestrator API URL |
| `getToken` | `() => Promise<string \| null>` | No | Async function returning auth token |

#### Methods

##### `startRun(options): Promise<RunHandle>`

Start a new agent run.

```typescript
const run = await client.startRun({
  parameters: { prompt: 'Your task description' },
  agentName: 'my-agent',      // Optional: specific agent
  projectDir: '/path/to/dir', // Optional: working directory
});
```

##### `resumeSession(sessionId, parameters): Promise<RunHandle>`

Resume an existing session with new input.

```typescript
const run = await client.resumeSession('session-id', {
  prompt: 'Follow-up message',
});
```

### RunHandle

Handle returned from `startRun()` or `resumeSession()`.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `runId` | `string` | Unique run identifier |
| `sessionId` | `string` | Session identifier |

#### Methods

##### `waitForResult(): Promise<RunResult>`

Poll until the run completes and return the result.

```typescript
const result = await run.waitForResult();
```

##### `stop(): Promise<void>`

Stop a running agent.

```typescript
await run.stop();
```

### RunResult

Result returned from `waitForResult()`.

```typescript
interface RunResult {
  status: 'completed' | 'failed' | 'stopped';
  resultText?: string;           // Text output from agent
  resultData?: Record<string, unknown>; // Structured output
  error?: string;                // Error message if failed
}
```

## Error Handling

```typescript
try {
  const run = await client.startRun({ parameters: { prompt: 'Task' } });
  const result = await run.waitForResult();

  if (result.status === 'failed') {
    console.error('Run failed:', result.error);
  }
} catch (error) {
  // Network or API errors
  console.error('Request failed:', error.message);
}
```

## TypeScript

This package is written in TypeScript and includes type definitions. All types are exported:

```typescript
import type {
  CoordinatorClientConfig,
  StartRunOptions,
  RunResult,
  SessionStatus,
} from '@rawe/agent-orchestrator-sdk';
```

## Requirements

- Node.js 18+ (uses native `fetch`)
- Agent Orchestrator backend running

## License

MIT
