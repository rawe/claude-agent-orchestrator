# Hooks → Backend API

Interface between hook scripts and the observability backend.

## Endpoint

**URL:** `http://127.0.0.1:8765/events`
**Method:** `POST`
**Content-Type:** `application/json`

## Request Body

See [Event model](DATA_MODELS.md#event) in DATA_MODELS.md

## Response

**Success:**
```json
{
  "ok": true
}
```
**Status Code:** `200 OK`

## Configuration

**Environment Variable:**
```bash
OBSERVABILITY_BACKEND_URL="http://127.0.0.1:8765/events"
```

Default: `http://127.0.0.1:8765/events` (used if not set)

## Error Handling

Hooks fail gracefully - if backend is unreachable, they log a warning but don't block agent execution.
