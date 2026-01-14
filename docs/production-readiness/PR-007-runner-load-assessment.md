# PR-007: Runner Load Assessment (Message Queue?)

**Priority**: P2 (Medium)
**Status**: Pending
**Effort**: Analysis only

## Question

Do we need a message queue (Redis, RabbitMQ) for run dispatch when scaling to many runners?

## Current Architecture

```
Runners (N) ──long-poll──► Coordinator (1)
             GET /runner/runs
             30s timeout
             Returns: pending runs or empty
```

Each runner:
- Holds one HTTP connection (30s timeout)
- Reconnects immediately after response
- Heartbeat every 60s (separate request)

## Load Analysis

### Connections Per Runner

| Activity | Connections | Frequency |
|----------|-------------|-----------|
| Run polling | 1 | Continuous (30s hold) |
| Heartbeat | 1 | Every 60s |
| Status report | 1 | Per run completion |

### Coordinator Load at Scale

| Runners | Concurrent Connections | Requests/min |
|---------|----------------------|--------------|
| 10 | ~10 | ~20 (heartbeats + status) |
| 50 | ~50 | ~100 |
| 100 | ~100 | ~200 |
| 500 | ~500 | ~1000 |

### FastAPI/Uvicorn Capacity

- Async framework handles 1000s of concurrent connections
- Long-poll is efficient (connection held, not spamming)
- Bottleneck is typically database, not HTTP connections

## Assessment

### Message Queue NOT Needed When

- < 100 runners (likely scenario)
- Run creation rate < 100/minute
- Single coordinator instance sufficient
- PostgreSQL handles write load

### Message Queue Consider When

- 500+ runners
- Multiple coordinator instances required (cross-instance run notification)
- Complex routing rules (beyond tag matching)
- Push-based dispatch needed (instead of runner polling)

## Recommendation

**Do not add message queue initially.** Current long-poll pattern is efficient and well-suited for expected scale.

### Monitor These Metrics First

1. Coordinator CPU under runner load
2. Database write latency during peak
3. Run claim latency (time from creation to runner pickup)
4. Failed run claims (race conditions)

### Trigger for Reassessment

- Run claim latency > 5 seconds consistently
- Database write queue backing up
- Need for coordinator horizontal scaling (PR-004)

## If Message Queue Needed Later

### Options

| Option | Pros | Cons |
|--------|------|------|
| Redis Streams | Simple, fast, can use for other state | Single point of failure |
| RabbitMQ | Durable, routing features | Operational overhead |
| AWS SQS | Managed, scalable | Vendor lock-in, latency |

### Migration Path

1. Add queue behind same API interface
2. Runners continue using HTTP
3. Coordinator publishes to queue
4. New "queue worker" claims and assigns

## Acceptance Criteria

- [ ] Load testing performed at 50+ runners
- [ ] Metrics collected for assessment
- [ ] Decision documented based on data
