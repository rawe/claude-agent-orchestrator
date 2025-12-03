# ADO MCP HTTP Wrapper - Development & Troubleshooting Guide

**Audience:** Developers maintaining, enhancing, or debugging the HTTP wrapper

---

## Architecture Overview

### Core Components

```
HTTP Request → Express Server → stdin/stdout Bridge → @azure-devops/mcp Process → Azure DevOps API
```

**Key Files:**
- `src/server.ts` - HTTP server, request routing, stdio bridge logic
- `src/utils/process-manager.ts` - MCP child process lifecycle
- `src/utils/error-handler.ts` - Centralized error handling & logging
- `src/config.ts` - Environment variable loading

### Design Pattern

**Adapter/Proxy Pattern:** Minimal wrapper that translates HTTP ↔ stdio without modifying MCP messages.

---

## Critical Implementation Details

### 1. JSON-RPC Notification Handling

**Issue:** JSON-RPC distinguishes between requests (expect response) and notifications (no response).

```typescript
// WRONG: id=0 is falsy in JavaScript
const isNotification = !req.body.id && req.body.method;

// CORRECT: Explicit undefined check
const isNotification = req.body.id === undefined && req.body.method;
```

**Behavior:**
- **Request** (has `id` field) → Wait for stdout response
- **Notification** (no `id` field) → Return HTTP 204 immediately

**Example notifications:**
```json
{"jsonrpc": "2.0", "method": "notifications/initialized"}
{"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}}
```

### 2. Line-Buffered stdout Parsing

**Problem:** MCP responses are newline-delimited JSON. stdout chunks may contain:
- Partial lines
- Multiple complete lines
- Mixed stderr output

**Solution:** Buffer and parse line-by-line

```typescript
let buffer = '';

const onData = (data: Buffer) => {
  buffer += data.toString();
  const lines = buffer.split('\n');

  // Process all complete lines (all except last)
  for (let i = 0; i < lines.length - 1; i++) {
    const line = lines[i].trim();
    if (line) {
      try {
        const parsed = JSON.parse(line);
        // Handle response
        return;
      } catch (err) {
        // Not JSON, ignore or log
      }
    }
  }

  // Keep incomplete last line in buffer
  buffer = lines[lines.length - 1];
};
```

### 3. Docker Container Networking

**Critical:** Server MUST bind to `0.0.0.0` inside container, not `127.0.0.1`.

```typescript
// WRONG: Won't accept connections from host
app.listen(3000, '127.0.0.1');

// CORRECT: Bind to all interfaces inside container
app.listen(3000, '0.0.0.0');
```

**Security:** Port mapping in docker-compose provides external localhost binding:
```yaml
ports:
  - "127.0.0.1:3000:3000"  # Only accessible on host's 127.0.0.1
```

### 4. MCP Process Lifecycle

**Single Long-Running Process:**
- Started on first `/mcp` request (lazy initialization)
- Reused for all subsequent requests
- Restart on crash/exit via `restart: unless-stopped` in docker-compose

**Environment Variables:**
```typescript
spawn('npx', ['-y', '@azure-devops/mcp', org, '-d', 'core', 'work', 'work-items', '--authentication', 'envvar'], {
  env: {
    ADO_MCP_AUTH_TOKEN: pat  // CRITICAL: Official env var name
  }
});
```

---

## Common Issues & Solutions

### Issue: Timeout on Second Request

**Symptom:** First request succeeds, subsequent requests timeout after 30s.

**Causes:**
1. **Notification mishandled** - Check `id === undefined` logic
2. **stdout listener not cleaned up** - Ensure `removeListener('data', onData)` is called
3. **Buffer contamination** - stderr mixing with stdout

**Debug:**
```bash
docker logs ado-mcp-http --tail=100
# Look for:
# - [MCP Request] to see what was sent
# - [MCP stdout chunk] to see raw output
# - [MCP Response] to see parsed response
```

### Issue: Empty Reply from Server (curl error 52)

**Symptom:** `curl: (52) Empty reply from server`

**Cause:** Server binding to wrong interface inside Docker.

**Solution:** Verify `app.listen()` binds to `0.0.0.0`:
```bash
docker exec ado-mcp-http netstat -tuln | grep 3000
# Should show: tcp6  0  0  :::3000  :::*  LISTEN
```

### Issue: MCP Process Fails to Start

**Symptom:** `[MCP] Process exited with code 1`

**Debug Steps:**
```bash
# 1. Check environment variables
docker exec ado-mcp-http env | grep ADO

# 2. Test MCP server directly
docker exec -it ado-mcp-http sh
npx -y @azure-devops/mcp $ADO_ORG -d core work work-items --authentication envvar
# Send test message: {"jsonrpc":"2.0","method":"initialize","params":{},"id":1}

# 3. Check stderr output
docker logs ado-mcp-http 2>&1 | grep stderr
```

**Common Causes:**
- Missing/invalid `ADO_PAT` or `ADO_ORG`
- PAT expired or lacks permissions
- Network connectivity to Azure DevOps

### Issue: Authentication Errors

**Symptom:** 401 errors or "unauthorized" in logs

**Checklist:**
1. **PAT Permissions:** Work Items (Read), Project and Team (Read)
2. **Env Var Name:** Must be `ADO_MCP_AUTH_TOKEN` (not `ADO_PAT`)
3. **PAT Format:** Plain token string, no "Bearer" prefix
4. **Organization Name:** Short name only (e.g., `contoso`, not `https://dev.azure.com/contoso`)

**Verify:**
```bash
docker exec ado-mcp-http printenv ADO_MCP_AUTH_TOKEN
# Should output the PAT token
```

### Issue: High Memory Usage

**Symptom:** Container using excessive memory over time

**Causes:**
- stdout buffer leaks (listeners not removed)
- MCP process accumulating state

**Solutions:**
1. **Monitor listeners:**
```typescript
console.log('Active listeners:', mcpProcess.stdout.listenerCount('data'));
```

2. **Implement periodic restart:**
```typescript
// Stop and restart MCP process every N requests
let requestCount = 0;
if (++requestCount > 1000) {
  stopMcpProcess();
  requestCount = 0;
}
```

---

## Development Workflow

### Local Development (without Docker)

```bash
# 1. Install dependencies
npm install

# 2. Set environment
cp .env.example .env
# Edit .env with real credentials

# 3. Run in dev mode
npm run dev

# 4. Test
curl http://127.0.0.1:3000/health
```

### Docker Development

```bash
# Rebuild and restart
docker-compose up -d --build

# View logs (follow)
docker logs -f ado-mcp-http

# Shell into container
docker exec -it ado-mcp-http sh

# Quick restart without rebuild
docker-compose restart
```

### Debugging Techniques

**1. Enable Verbose Logging:**
```typescript
// Add to server.ts
mcpProcess.stdout.on('data', (data) => {
  console.log('[RAW stdout]', data.toString());
});

mcpProcess.stderr.on('data', (data) => {
  console.error('[RAW stderr]', data.toString());
});
```

**2. Test MCP Protocol Manually:**
```bash
# Send initialize request
curl -X POST http://127.0.0.1:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{}},"id":1}'

# Send notification
curl -X POST http://127.0.0.1:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# List tools
curl -X POST http://127.0.0.1:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}'
```

**3. Monitor Process State:**
```bash
# Check if MCP process is running
docker exec ado-mcp-http ps aux | grep mcp

# Check file descriptors (detect leaks)
docker exec ado-mcp-http ls -l /proc/$(pgrep node | head -1)/fd
```

---

## Testing Strategy

### Unit Tests

**Key Areas:**
- Config validation
- Notification detection logic
- Line buffering parser
- Error handler responses

**Example:**
```typescript
describe('Notification Detection', () => {
  test('id=0 is not a notification', () => {
    expect(isNotification({id: 0, method: 'test'})).toBe(false);
  });

  test('no id field is a notification', () => {
    expect(isNotification({method: 'test'})).toBe(true);
  });
});
```

### Integration Tests

**Test Flow:**
1. Start container
2. Send initialize request
3. Send notification
4. Send tools/list request
5. Verify responses and timing

### Manual Testing Checklist

- [ ] Health endpoint returns 503 before first request
- [ ] Health endpoint returns 200 after MCP starts
- [ ] Initialize request succeeds (~1s)
- [ ] Notification returns 204 immediately
- [ ] Subsequent requests don't timeout
- [ ] Graceful shutdown on SIGTERM
- [ ] Container restarts automatically on crash

---

## Performance Considerations

### Current Limitations

- **Sequential Requests:** Single MCP process handles one request at a time
- **No Connection Pooling:** One process for all clients
- **No Caching:** Every request hits Azure DevOps API

**Acceptable for:** <10 req/sec, local development use

### Future Enhancements

**If scaling needed:**

1. **Process Pool:**
```typescript
const mcpPool: ChildProcess[] = [];
const POOL_SIZE = 5;

function getAvailableProcess() {
  // Round-robin or least-busy selection
}
```

2. **Request Queueing:**
```typescript
const requestQueue: Array<{req, res, next}> = [];

async function processQueue() {
  while (requestQueue.length > 0) {
    const {req, res, next} = requestQueue.shift();
    await handleMcpRequest(req, res, next);
  }
}
```

3. **Response Caching:**
```typescript
// Cache tools/list response (doesn't change often)
const cache = new Map<string, {data: any, expires: number}>();
```

---

## Common Modifications

### Add New Endpoint

```typescript
app.get('/tools', async (req, res) => {
  // Call MCP tools/list and return simplified format
});
```

### Add Request Logging

```typescript
app.use((req, res, next) => {
  const requestId = crypto.randomUUID();
  req.requestId = requestId;
  console.log(`[${requestId}] ${req.method} ${req.path}`);
  next();
});
```

### Add Authentication

```typescript
const AUTH_TOKEN = process.env.HTTP_AUTH_TOKEN;

app.use('/mcp', (req, res, next) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (token !== AUTH_TOKEN) {
    return res.status(401).json({error: 'Unauthorized'});
  }
  next();
});
```

### Change Timeout

```typescript
// In server.ts
const TIMEOUT_MS = 60000;  // 60 seconds

const timeout = setTimeout(() => {
  reject(new Error('Timeout waiting for MCP response'));
}, TIMEOUT_MS);
```

---

## Security Notes

### Threat Model (Local Use Only)

**Assumptions:**
- Server runs on trusted machine
- Only local processes can connect (127.0.0.1 binding)
- No exposure to network/internet

**No Security Features:**
- No authentication on /mcp endpoint
- No rate limiting
- No input validation beyond JSON parsing
- PAT stored in environment (acceptable for local use)

### If Exposing Externally (NOT RECOMMENDED)

**Required additions:**
1. **Authentication:** Bearer tokens, API keys
2. **Rate Limiting:** Per-client request throttling
3. **Input Validation:** Whitelist allowed MCP methods
4. **TLS:** HTTPS with valid certificates
5. **Secrets Management:** Vault integration for PAT storage

---

## Useful Commands

```bash
# Build image
docker-compose build

# Start in background
docker-compose up -d

# View logs
docker logs ado-mcp-http --tail=100 -f

# Restart after code changes
docker-compose up -d --build

# Stop and remove
docker-compose down

# Check container health
docker inspect ado-mcp-http --format='{{.State.Health.Status}}'

# Execute commands in container
docker exec ado-mcp-http ps aux
docker exec ado-mcp-http netstat -tuln

# Clean rebuild (no cache)
docker-compose build --no-cache

# View resource usage
docker stats ado-mcp-http
```

---

## Troubleshooting Checklist

When something goes wrong, check in this order:

1. **Container Running?**
   ```bash
   docker ps | grep ado-mcp-http
   ```

2. **Server Listening?**
   ```bash
   curl http://127.0.0.1:3000/health
   ```

3. **Environment Set?**
   ```bash
   docker exec ado-mcp-http env | grep ADO
   ```

4. **MCP Process Alive?**
   ```bash
   docker exec ado-mcp-http ps aux | grep mcp-server
   ```

5. **Check Logs:**
   ```bash
   docker logs ado-mcp-http --tail=50
   ```

6. **Test MCP Directly:**
   ```bash
   docker exec -it ado-mcp-http sh
   echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | npx -y @azure-devops/mcp $ADO_ORG
   ```

7. **Network Connectivity:**
   ```bash
   docker exec ado-mcp-http wget -O- https://dev.azure.com/$ADO_ORG
   ```

---

## Additional Resources

- **MCP Specification:** https://spec.modelcontextprotocol.io/
- **Azure DevOps MCP Server:** https://github.com/microsoft/azure-devops-mcp
- **JSON-RPC 2.0 Spec:** https://www.jsonrpc.org/specification
- **Architecture Doc:** `docs/ado-mcp-http-wrapper-architecture.md`
