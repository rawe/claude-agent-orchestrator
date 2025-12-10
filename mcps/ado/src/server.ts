import express, { Request, Response } from 'express';
import { loadConfig } from './config';
import { errorHandler, logRequest } from './utils/error-handler';
import { startMcpProcess, stopMcpProcess, getMcpProcess } from './utils/process-manager';

const app = express();
app.use(express.json());
app.use(logRequest);

let config: ReturnType<typeof loadConfig>;

try {
  config = loadConfig();
} catch (error) {
  console.error('[CONFIG] Failed to load configuration:', (error as Error).message);
  process.exit(1);
}

app.get('/health', (req: Request, res: Response) => {
  const mcpProcess = getMcpProcess();
  const isHealthy = mcpProcess !== null && !mcpProcess.killed;

  res.status(isHealthy ? 200 : 503).json({
    status: isHealthy ? 'healthy' : 'unhealthy',
    mcp_process: mcpProcess ? 'running' : 'stopped',
  });
});

app.post('/mcp', async (req: Request, res: Response, next) => {
  try {
    let mcpProcess = getMcpProcess();

    if (!mcpProcess || mcpProcess.killed) {
      mcpProcess = startMcpProcess({
        adoOrg: config.adoOrg,
        adoPat: config.adoPat,
      });
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    if (!mcpProcess.stdin || !mcpProcess.stdout) {
      throw new Error('MCP process stdio not available');
    }

    const message = JSON.stringify(req.body) + '\n';
    console.log('[MCP Request]', req.body);
    mcpProcess.stdin.write(message);

    const isNotification = req.body.id === undefined && req.body.method;

    if (isNotification) {
      console.log('[MCP] Notification sent, no response expected');
      res.status(204).end();
      return;
    }

    const response = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout waiting for MCP response'));
      }, 30000);

      let buffer = '';

      const onData = (data: Buffer) => {
        const chunk = data.toString();
        console.log('[MCP stdout chunk]', chunk);
        buffer += chunk;
        const lines = buffer.split('\n');

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (line) {
            try {
              const parsed = JSON.parse(line);
              console.log('[MCP Response]', parsed);
              clearTimeout(timeout);
              mcpProcess!.stdout!.removeListener('data', onData);
              resolve(parsed);
              return;
            } catch (err) {
              console.log('[MCP] Not valid JSON, buffering:', line);
            }
          }
        }

        buffer = lines[lines.length - 1];
      };

      mcpProcess!.stdout!.on('data', onData);
    });

    res.json(response);
  } catch (error) {
    next(error);
  }
});

app.use(errorHandler);

const server = app.listen(config.port, '0.0.0.0', () => {
  console.log(`[SERVER] ADO MCP HTTP Wrapper listening on port ${config.port}`);
  console.log(`[SERVER] Health check: /health`);
  console.log(`[SERVER] MCP endpoint: /mcp`);
});

process.on('SIGTERM', () => {
  console.log('[SERVER] SIGTERM received, shutting down gracefully...');
  server.close(() => {
    stopMcpProcess();
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('[SERVER] SIGINT received, shutting down gracefully...');
  server.close(() => {
    stopMcpProcess();
    process.exit(0);
  });
});
