import { spawn, ChildProcess } from 'child_process';

let mcpProcess: ChildProcess | null = null;

export interface ProcessManagerConfig {
  adoOrg: string;
  adoPat: string;
}

export function startMcpProcess(config: ProcessManagerConfig): ChildProcess {
  if (mcpProcess) {
    console.log('[MCP] Process already running');
    return mcpProcess;
  }

  console.log('[MCP] Starting Azure DevOps MCP server...');

  mcpProcess = spawn('npx', [
    '-y',
    '@azure-devops/mcp',
    config.adoOrg,
    '-d', 'core', 'work', 'work-items', 'search',
    '--authentication', 'envvar'
  ], {
    env: {
      ...process.env,
      ADO_MCP_AUTH_TOKEN: config.adoPat,
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  mcpProcess.on('error', (error) => {
    console.error('[MCP] Process error:', error);
    mcpProcess = null;
  });

  mcpProcess.on('exit', (code, signal) => {
    console.log(`[MCP] Process exited with code ${code}, signal ${signal}`);
    mcpProcess = null;
  });

  mcpProcess.stderr?.on('data', (data) => {
    console.error('[MCP stderr]', data.toString());
  });

  console.log('[MCP] Process started with PID:', mcpProcess.pid);
  return mcpProcess;
}

export function stopMcpProcess(): void {
  if (mcpProcess) {
    console.log('[MCP] Stopping process...');
    mcpProcess.kill('SIGTERM');
    mcpProcess = null;
  }
}

export function getMcpProcess(): ChildProcess | null {
  return mcpProcess;
}
