# Architectural Evaluation: Observability Backend Persistence

## Executive Summary

This document evaluates the current persistence approach in the Agent Orchestrator observability backend and analyzes alternative architectures, including the introduction of a message bus like RabbitMQ.

**Current State**: Direct HTTP POST to FastAPI → SQLite + WebSocket broadcast
**Key Question**: Is SQLite the right approach, or would a message bus provide better scalability, reliability, and decoupling?

---

## 1. Current Architecture Analysis

### 1.1 System Overview

```
┌─────────────────────┐     HTTP POST      ┌─────────────────────────────────────────┐
│   ao-* Commands     │ ──────────────────►│          FastAPI Backend                │
│ (observability.py)  │                    │                                         │
│  - send_event()     │                    │  POST /events                           │
│  - httpx.post()     │                    │    ├─► insert_event() → SQLite          │
│  - timeout: 2s      │                    │    └─► broadcast() → WebSocket clients  │
│  - silent failure   │                    │                                         │
└─────────────────────┘                    │  WebSocket /ws                          │
                                           │    └─► connections: set[WebSocket]      │
                                           └───────────────────────────────────────────┘
                                                          │
                                           ┌──────────────┼──────────────┐
                                           ▼              ▼              ▼
                                       ┌──────┐    ┌──────────────┐  ┌──────────────┐
                                       │SQLite│    │Frontend (WS) │  │Future clients│
                                       │.db   │    │React app     │  │(e.g. metrics)│
                                       └──────┘    └──────────────┘  └──────────────┘
```

### 1.2 Current Data Flow

1. **Event Generation**: `ao-*` commands (Python) call hook functions during SDK execution
2. **Event Transmission**: `httpx.post()` sends events to `POST /events` (2s timeout, silent failure)
3. **Event Processing**: FastAPI handler:
   - Persists to SQLite (synchronous)
   - Broadcasts via WebSocket (async, best-effort)
4. **Event Consumption**: React frontend receives via WebSocket

### 1.3 Key Characteristics

| Aspect | Implementation |
|--------|----------------|
| **Coupling** | Tight - producer directly calls backend API |
| **Persistence** | SQLite file-based database |
| **Delivery** | Fire-and-forget with silent failure |
| **Real-time** | WebSocket broadcast to connected clients |
| **Scalability** | Single-instance, single-database |
| **Durability** | Events lost if backend is down |

---

## 2. How ao-* Commands Interact with Observability

### 2.1 Integration Points

The `ao-*` commands integrate with observability through **programmatic SDK hooks**:

```python
# claude_client.py
options.hooks = {
    "UserPromptSubmit": [HookMatcher(hooks=[user_prompt_hook])],
    "PostToolUse": [HookMatcher(hooks=[post_tool_hook])],
}
```

### 2.2 Event Flow from Commands

```
ao-new/ao-resume
     │
     ├─► Claude SDK starts
     │
     ├─► user_prompt_hook fires
     │      └─► send_session_start() → HTTP POST /events
     │      └─► send_message() → HTTP POST /events
     │
     ├─► SDK executes tools
     │      └─► post_tool_hook fires (per tool)
     │            └─► send_post_tool() → HTTP POST /events
     │
     ├─► SDK returns result
     │      └─► send_message() → HTTP POST /events (assistant)
     │
     └─► Session completes
            └─► send_session_stop() → HTTP POST /events
```

### 2.3 Critical Design Decisions

| Decision | Implementation | Rationale |
|----------|---------------|-----------|
| Silent failure | `except Exception: pass` | Don't block agent execution |
| 2s timeout | `httpx.post(..., timeout=2.0)` | Prevent hanging on network issues |
| Synchronous HTTP | No async queue | Simplicity, immediate delivery |
| Per-event POST | Individual HTTP calls | Real-time visibility |

### 2.4 Current Limitations

1. **Event Loss**: If backend is down, events are silently lost
2. **No Buffering**: Events not queued locally if backend unavailable
3. **Performance**: HTTP overhead per event (tool calls can be frequent)
4. **No Replay**: Lost events cannot be recovered

---

## 3. Alternative Architectural Approaches

### Approach A: Current (SQLite + Direct HTTP)

**Keep the existing architecture as-is.**

```
[Producers] ──HTTP POST──► [FastAPI] ──► [SQLite] + [WebSocket Broadcast]
```

#### Pros
- **Simple**: Minimal infrastructure, easy to understand
- **Zero dependencies**: No external services to manage
- **Works offline**: SQLite is file-based, no network dependency
- **Low latency**: Direct path from event to consumer
- **Easy debugging**: Single codebase, single log stream
- **Docker-friendly**: No additional containers needed

#### Cons
- **Event loss**: No durability guarantee if backend is down
- **Tight coupling**: Producers must know backend URL
- **No backpressure**: Backend can be overwhelmed
- **Single point of failure**: Backend crash = no observability
- **Limited scalability**: Single SQLite instance
- **No replay**: Lost events cannot be recovered

---

### Approach B: Message Bus (RabbitMQ)

**Introduce RabbitMQ as an intermediary for event delivery.**

```
[Producers] ──AMQP──► [RabbitMQ] ──► [Consumer] ──► [SQLite/PostgreSQL]
                          │
                          └──► [WebSocket Bridge] ──► [Frontend]
```

#### Architecture Changes

1. **Producers**: Publish events to RabbitMQ exchange
2. **Event Queue**: Persistent queue with delivery guarantees
3. **Consumer Service**: Subscribes to queue, writes to database
4. **WebSocket Bridge**: Separate service or integrated consumer

#### Pros
- **Durability**: Events persisted in queue until consumed
- **Decoupling**: Producers independent of backend availability
- **Backpressure**: Queue absorbs traffic spikes
- **Replay capability**: Dead letter queues for failed processing
- **Scalability**: Multiple consumers can process events
- **Reliability**: RabbitMQ clustering for high availability

#### Cons
- **Complexity**: Additional service to deploy and manage
- **Latency**: Extra hop increases event delivery time
- **Infrastructure**: RabbitMQ requires maintenance, monitoring
- **Learning curve**: AMQP protocol, exchange types, queue bindings
- **Resource overhead**: RabbitMQ process consumes memory/CPU
- **Overkill**: May be excessive for single-user/small-scale use

---

### Approach C: Redis Streams

**Use Redis Streams for lightweight, persistent event streaming.**

```
[Producers] ──XADD──► [Redis Stream] ──► [Consumer] ──► [SQLite/PostgreSQL]
                            │
                            └──► [WebSocket via Pub/Sub] ──► [Frontend]
```

#### Pros
- **Lightweight**: Simpler than RabbitMQ, easy to operate
- **Persistence**: Streams persist to disk (AOF/RDB)
- **Consumer groups**: Multiple consumers with acknowledgment
- **Fast**: In-memory with optional persistence
- **Pub/Sub**: Built-in real-time notification mechanism
- **Flexible**: Can act as both queue and cache

#### Cons
- **Less mature**: Streams feature newer than RabbitMQ queues
- **Memory-bound**: Large volumes require significant RAM
- **Single-threaded**: Redis core is single-threaded
- **Limited routing**: No topic exchanges like RabbitMQ
- **Operational complexity**: Requires tuning for persistence

---

### Approach D: Local Event Log + Async Sync

**Buffer events locally in a log file, sync asynchronously to backend.**

```
[Producers] ──append──► [Local .jsonl] ──► [Sync Service] ──► [Backend]
                              │
                              └──► Already exists! (.jsonl session files)
```

#### Architecture Changes

1. **Leverage existing .jsonl files**: Already logging all SDK messages
2. **Add sync service**: Periodic or triggered sync to backend
3. **Track position**: Maintain read offset per session file

#### Pros
- **Already exists**: .jsonl files already contain full event history
- **No new dependencies**: No external services needed
- **Offline-first**: Works without any network connectivity
- **Recovery**: Full replay from .jsonl files if needed
- **Minimal changes**: Enhance existing infrastructure

#### Cons
- **Not real-time**: Sync introduces delay
- **Duplicate handling**: Need idempotent writes
- **File management**: Log rotation, cleanup complexity
- **State tracking**: Must track sync position per file

---

### Approach E: Hybrid - SQLite + Local Buffer

**Add a local event buffer to survive transient failures.**

```
[Producers] ──► [Local Buffer] ──► [HTTP POST] ──► [Backend]
                     │
                     └──► Retry queue with exponential backoff
```

#### Implementation

```python
# Enhanced send_event with local buffering
def send_event(base_url: str, event: dict) -> None:
    try:
        response = httpx.post(f"{base_url}/events", json=event, timeout=2.0)
        response.raise_for_status()
    except Exception:
        # Buffer locally for retry
        buffer_event(event)  # Write to local file/SQLite
        schedule_retry()      # Background retry task
```

#### Pros
- **Minimal changes**: Enhance existing code
- **Resilience**: Survives transient backend failures
- **Eventual delivery**: Events eventually reach backend
- **No new services**: No infrastructure additions
- **Preserves simplicity**: Same mental model

#### Cons
- **Complexity in client**: Buffer management in producer
- **Ordering challenges**: Retried events may arrive out of order
- **Resource usage**: Local buffer consumes disk/memory
- **Partial solution**: Still single backend, no scalability

---

## 4. Detailed Comparison Matrix

| Criteria | A: Current | B: RabbitMQ | C: Redis | D: Local Log | E: Hybrid |
|----------|------------|-------------|----------|--------------|-----------|
| **Complexity** | Low | High | Medium | Low | Medium |
| **Infrastructure** | None | RabbitMQ | Redis | None | None |
| **Durability** | Poor | Excellent | Good | Excellent | Good |
| **Real-time** | Yes | Yes (extra hop) | Yes | No (delayed) | Yes |
| **Scalability** | Limited | Excellent | Good | Limited | Limited |
| **Offline support** | No | No (queue offline) | No | Yes | Partial |
| **Event replay** | No | Yes (DLQ) | Yes (streams) | Yes (.jsonl) | Partial |
| **Setup effort** | Done | High | Medium | Low | Low |
| **Operational cost** | Low | High | Medium | Low | Low |

---

## 5. Suitability Analysis by Use Case

### 5.1 Single Developer / Local Development

**Recommended: Approach A (Current) or E (Hybrid)**

Rationale:
- Simplicity is paramount
- No external services to manage
- Event loss is acceptable (can re-run agents)
- Low operational overhead

### 5.2 Small Team / CI/CD Integration

**Recommended: Approach E (Hybrid) or C (Redis)**

Rationale:
- Need reliability for automated pipelines
- Multiple concurrent sessions possible
- Some event durability important
- Moderate scalability needs

### 5.3 Production / Multi-User Platform

**Recommended: Approach B (RabbitMQ) or C (Redis)**

Rationale:
- High availability required
- Multiple concurrent users
- Event loss unacceptable
- Horizontal scaling needed
- Audit trail requirements

### 5.4 Offline-First / Edge Deployment

**Recommended: Approach D (Local Log)**

Rationale:
- Network connectivity unreliable
- Must work fully offline
- Sync when connection available
- Full event replay capability

---

## 6. Evaluation of ao-* Command Integration

### 6.1 Is the Current Approach Right?

The current integration via HTTP POST from hooks is **pragmatic but has limitations**:

| Aspect | Assessment |
|--------|------------|
| **Simplicity** | ✓ Excellent - clear, direct path |
| **Real-time** | ✓ Good - events arrive immediately |
| **Reliability** | ✗ Poor - silent failure, no retry |
| **Performance** | ~ Acceptable - HTTP overhead per event |
| **Decoupling** | ✗ Poor - tight coupling to backend URL |

### 6.2 Recommended Improvements (Regardless of Architecture)

1. **Add circuit breaker**: Stop trying after N failures
2. **Log failures**: At least record lost events for debugging
3. **Batch events**: Reduce HTTP calls for tool-heavy sessions
4. **Health check**: Verify backend availability before session

```python
# Proposed enhancement
def send_event(base_url: str, event: dict) -> bool:
    """Send event with failure tracking."""
    global _failure_count

    if _failure_count > MAX_FAILURES:
        return False  # Circuit breaker open

    try:
        response = httpx.post(f"{base_url}/events", json=event, timeout=2.0)
        response.raise_for_status()
        _failure_count = 0
        return True
    except Exception as e:
        _failure_count += 1
        logger.warning(f"Observability event failed: {e}")
        return False
```

---

## 7. Conclusion and Recommendations

### 7.1 Assessment Summary

The current SQLite + direct HTTP architecture is **appropriate for the current use case** (single-developer, local development tool). Introducing RabbitMQ would be **premature optimization** unless the system needs to:

1. Support multiple concurrent users/sessions
2. Guarantee zero event loss
3. Scale horizontally
4. Integrate with other event consumers

### 7.2 Recommended Path Forward

#### Short-term (Current Phase)
**Keep Approach A (Current) with minor enhancements:**

1. Add circuit breaker to prevent hammering dead backend
2. Log event failures for debugging (instead of silent `pass`)
3. Add optional event batching for high-frequency tool calls
4. Consider health check endpoint before session start

#### Medium-term (If Scaling Needed)
**Evolve to Approach E (Hybrid) or D (Local Log):**

1. Leverage existing .jsonl files as event source of truth
2. Add background sync service to populate observability DB
3. Implement idempotent writes with event IDs
4. Support event replay from historical sessions

#### Long-term (If Production Platform)
**Consider Approach C (Redis) or B (RabbitMQ):**

1. Redis if already using Redis for other purposes (caching, sessions)
2. RabbitMQ if complex routing/multi-consumer scenarios needed
3. PostgreSQL for production database (replace SQLite)
4. Kubernetes deployment with horizontal scaling

### 7.3 Final Recommendation

**Do not introduce RabbitMQ at this stage.**

The current architecture is well-suited for the agent orchestrator's current scope. The engineering investment in a message bus would be better spent on:

1. Improving the existing event capture reliability
2. Leveraging the already-existing .jsonl session logs
3. Building better event replay/debugging capabilities
4. Adding session analytics on top of SQLite

**If durability becomes critical**, the lowest-effort path is:
- Approach D: Use .jsonl files as source of truth
- Add a sync service to populate the observability database
- This provides replay capability without new infrastructure

---

## Appendix: Implementation Notes

### A.1 Quick Win: Circuit Breaker Implementation

```python
# In observability.py

_failure_count = 0
_circuit_open_until = 0
MAX_FAILURES = 5
CIRCUIT_RESET_SECONDS = 60

def send_event(base_url: str, event: dict) -> None:
    global _failure_count, _circuit_open_until

    now = time.time()
    if now < _circuit_open_until:
        return  # Circuit still open

    try:
        httpx.post(f"{base_url}/events", json=event, timeout=2.0)
        _failure_count = 0  # Reset on success
    except Exception:
        _failure_count += 1
        if _failure_count >= MAX_FAILURES:
            _circuit_open_until = now + CIRCUIT_RESET_SECONDS
            _failure_count = 0  # Reset for next cycle
```

### A.2 Leveraging .jsonl Files

The existing session .jsonl files already contain:
- User messages
- System messages (with session_id)
- Result messages
- All streamed SDK output

A sync service could:
1. Watch for new .jsonl files
2. Parse and extract events
3. POST to observability backend
4. Track position for incremental sync

This provides event durability "for free" using existing infrastructure.

---

*Document generated: 2024*
*Author: Architectural Review*
*Status: Final*
