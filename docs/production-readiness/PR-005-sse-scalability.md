# PR-005: SSE Broadcast Scalability

**Priority**: P2 (Medium)
**Status**: Pending
**Effort**: Medium

## Problem

SSE broadcasts all events to all connected clients. No user-based filtering.

## Current State

- `SSEManager` broadcasts to all connections
- Dashboard receives every session event (no user filtering)
- `created_by_filter` field exists in SSEConnection but is NOT implemented
- Sessions have no `user_id` or `owner_id` column in database

## Why Address

1. **Bandwidth waste**: User receives events for other users' sessions
2. **Privacy risk**: Event data contains `tool_input`, `tool_output`, `content`, `result_text`, `result_data` - actual execution data, not just metadata. In multi-tenant production, users could see other users' agent conversations.
3. **Client overload**: Dashboard processing irrelevant events

## Why NOT Address (Counter-argument)

- Dashboard displays all sessions without user filtering (by design currently)
- Low concurrent user count initially
- Privacy depends on agent use case (internal tools may be acceptable)

## Recommendation

**Address when user count grows.** Client-side filtering works for small user counts. Server-side filtering needed for privacy at scale.

## Implementation Options

### Option A: User-Scoped SSE Endpoints

```
GET /sse/sessions?user_id={user_id}
```

- Filter events server-side before broadcast
- Requires session ownership tracking

### Option B: Separate SSE Channels

```
GET /sse/users/{user_id}/sessions
```

- Each user gets dedicated channel
- Cleaner separation, more connections to manage

### Option C: WebSocket with Subscriptions

- Client subscribes to specific sessions
- More complex but most flexible
- Note: ADR-013 moved away from WebSocket for simplicity

## Implementation Notes

- Add `user_id` or `owner_id` to session model
- Extract user from JWT token on session creation
- Filter SSE events by ownership before broadcast

## Acceptance Criteria

- [ ] Users only receive their own session events
- [ ] Admin role can receive all events
- [ ] No performance regression on broadcast
