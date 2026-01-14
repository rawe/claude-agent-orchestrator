# PR-006: Monitoring & Observability

**Priority**: P1 (High)
**Status**: Pending
**Effort**: Medium

## Problem

Limited visibility into system health and performance in production.

## Current State

- Basic logging to stdout
- `DEBUG_LOGGING` flag for verbose output
- No metrics, no alerting
- Runner heartbeat tracked (available via `GET /runners` API) but not as metrics

## Why Address

1. **Incident detection**: Can't detect problems before users report
2. **Capacity planning**: No data on resource usage trends
3. **Debugging**: Hard to trace issues across components
4. **SLA tracking**: Can't measure availability or latency

## Why NOT Address (Counter-argument)

- Small user base can report issues directly
- Adds operational overhead
- Cloud platforms provide basic monitoring

## Recommendation

**Address before production launch.** Monitoring is essential for operating a multi-user service. Start with basics, expand as needed.

## Metrics to Track

### Coordinator Metrics

| Metric | Type | Purpose |
|--------|------|---------|
| `runs_created_total` | Counter | Work volume |
| `runs_completed_total` | Counter | Success rate |
| `runs_failed_total` | Counter | Error rate |
| `runs_pending_count` | Gauge | Queue depth |
| `runners_online_count` | Gauge | Capacity |
| `sse_connections_count` | Gauge | Client load |
| `request_latency_seconds` | Histogram | Performance |

### Runner Metrics

| Metric | Type | Purpose |
|--------|------|---------|
| `runs_executed_total` | Counter | Work done |
| `run_duration_seconds` | Histogram | Execution time |
| `heartbeat_failures_total` | Counter | Connection health |

## Implementation Options

### Option A: Prometheus + Grafana (Recommended)

- `prometheus-fastapi-instrumentator` for auto metrics
- Custom metrics for business logic
- Standard, well-supported stack

### Option B: Cloud-Native

- AWS CloudWatch / GCP Cloud Monitoring
- Less setup, vendor lock-in
- May lack custom metric flexibility

## Alerting Priorities

| Alert | Condition | Severity |
|-------|-----------|----------|
| No online runners | `runners_online_count == 0` | Critical |
| High failure rate | `runs_failed / runs_total > 0.1` | High |
| Queue backing up | `runs_pending_count > 50` | Medium |
| Coordinator down | Health check fails | Critical |

## Acceptance Criteria

- [ ] Prometheus metrics endpoint exposed
- [ ] Key metrics defined and tracked
- [ ] Grafana dashboard for overview
- [ ] Critical alerts configured
