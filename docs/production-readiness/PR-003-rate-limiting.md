# PR-003: Rate Limiting & Abuse Protection

**Priority**: P1 (High)
**Status**: Pending
**Effort**: Low

## Problem

No rate limiting on API endpoints. Malicious or buggy clients can overwhelm coordinator.

## Current State

- All endpoints accept unlimited requests
- Authentication required but no per-user limits
- No protection against runaway agent loops

## Why Address

1. **Denial of service**: Single user can exhaust coordinator resources
2. **Cost control**: Each agent run consumes Claude API credits
3. **Runaway agents**: Bug in agent can create infinite child sessions

## Why NOT Address (Counter-argument)

- Trusted user base initially
- Auth0 provides some rate limiting at auth layer
- Can add reactively when abuse detected

## Recommendation

**Address before public launch.** Basic rate limiting is low effort and prevents obvious abuse vectors.

## Implementation Notes

### Endpoint Priorities

| Endpoint | Risk | Recommended Limit |
|----------|------|-------------------|
| `POST /runs` | High (creates work) | 10/min per user |
| `POST /sessions/*/events` | Medium (DB writes) | 100/min per session |
| `GET /runner/runs` | Low (long-poll) | 5 concurrent |
| `GET /sse/sessions` | Low | 3 concurrent per user |

### Options

1. **FastAPI middleware**: `slowapi` library (recommended for simplicity)
2. **API Gateway**: If using cloud provider (AWS API Gateway, etc.)
3. **Redis-based**: For distributed rate limiting across instances

### Agent Loop Protection

Add max child session depth:
```python
if session.depth > MAX_DEPTH:
    raise HTTPException(400, "Max session depth exceeded")
```

## Acceptance Criteria

- [ ] Rate limiting on `POST /runs`
- [ ] Concurrent connection limits on SSE
- [ ] Max session depth enforced
- [ ] Rate limit errors return 429 with retry-after header
