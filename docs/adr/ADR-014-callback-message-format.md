# ADR-014: Callback Message Format with XML Tags

**Status:** Proposed
**Date:** 2026-01-06
**Decision Makers:** Architecture Review

## Context

The Agent Orchestrator framework uses a callback mechanism to notify parent agents when child agents complete (see [ADR-003](./ADR-003-callback-based-async.md)). When a child completes, the Callback Processor creates a `RESUME_SESSION` run that delivers a notification message to the parent agent.

Currently, callback messages are delivered as **user messages** via `ao-resume -p "{message}"`. The message uses plain markdown formatting:

```
The child agent session "ses_abc123" has completed.

## Child Result

{result content}

Please continue with the orchestration based on this result.
```

### The Problem

Using user interaction as a callback channel creates **ambiguity for AI agents**:

1. **Role Confusion**: The agent cannot distinguish "framework callback" from "user input" at the message role level
2. **Response Uncertainty**: Should the agent acknowledge the callback? Thank someone? Or just process it silently?
3. **Trust Model**: In orchestration scenarios, callbacks should be trusted implicitly, while user messages might require validation or clarification
4. **Parsing Difficulty**: Plain text callbacks are harder to reliably detect and parse programmatically

This was observed when testing the callback mechanism - agents sometimes responded with social niceties ("Thank you for the update!") rather than proceeding directly with orchestration logic.

## Decision

**Wrap callback messages in XML-style tags** to clearly distinguish them from user input.

### New Callback Message Format

**Single child completion (success):**
```xml
<agent-callback session="{child_session_id}" status="completed">
## Child Result

{child_result}
</agent-callback>

Please continue with the orchestration based on this result.
```

**Single child failure:**
```xml
<agent-callback session="{child_session_id}" status="failed">
## Error

{child_error}
</agent-callback>

Please handle this failure and continue with the orchestration.
```

**Multiple children (aggregated):**
```xml
<agent-callback type="aggregated" count="{count}">
{children_results}
</agent-callback>

Please continue with the orchestration based on these results.
```

### Implementation Location

Update template strings in `servers/agent-coordinator/services/callback_processor.py`:

```python
CALLBACK_PROMPT_TEMPLATE = """<agent-callback session="{child_session_id}" status="completed">
## Child Result

{child_result}
</agent-callback>

Please continue with the orchestration based on this result."""

CALLBACK_FAILED_PROMPT_TEMPLATE = """<agent-callback session="{child_session_id}" status="failed">
## Error

{child_error}
</agent-callback>

Please handle this failure and continue with the orchestration."""

AGGREGATED_CALLBACK_PROMPT_TEMPLATE = """<agent-callback type="aggregated" count="{count}">
{children_results}
</agent-callback>

Please continue with the orchestration based on these results."""
```

## Options Considered

### Option 1: XML-Style Tags (Selected)

```xml
<agent-callback session="ses_xxx" status="completed">
  Result content here
</agent-callback>
```

**Pros:**
- Visually distinct from casual user text
- Machine-parseable with clear structure
- Claude models handle XML tags natively (already used in system prompts, tool results)
- Preserves human readability of the result content
- Simple implementation (template string changes only)

**Cons:**
- Still delivered as "user" message role
- Requires agents to recognize the tag pattern

### Option 2: Explicit Source Indicator

```
[SYSTEM CALLBACK - agent-orchestrator]
Session ses_xxx completed.
Result: ...
```

**Pros:**
- Human readable
- Clear source indication

**Cons:**
- Less structured, harder to parse programmatically
- Could be mimicked by malicious user input
- No clear end delimiter

### Option 3: Structured JSON Block

```json
{"type": "agent_callback", "session_id": "ses_xxx", "status": "completed", "result": "..."}
```

**Pros:**
- Highly structured, trivial to parse
- Unambiguous format

**Cons:**
- Less human-readable for debugging
- Looks like code rather than a message
- Result content becomes escaped, harder to read

### Option 4: Different Message Role

Use `system` role instead of `user` role for callback delivery.

**Pros:**
- Semantically correct - callbacks ARE system infrastructure, not user input
- Unambiguous at the API level
- Cleanest separation of concerns

**Cons:**
- Requires changes to Claude Agent SDK integration
- `ao-resume` would need new mechanism to inject system messages
- System messages have specific behavior (always considered, may not be truncated)
- More invasive architectural change
- May not be possible with all executor types

## Rationale

### Why XML Tags (Option 1)?

1. **Native to Claude**: XML tags are already used extensively in Claude's prompts for structured data (e.g., `<example>`, `<context>`, `<instructions>`). Models are trained to recognize and respect these boundaries.

2. **Balance of Structure and Readability**: XML tags provide clear delimiters while keeping the result content in natural, readable format.

3. **Simple Implementation**: Only requires changing template strings in one file (`callback_processor.py`). No SDK changes, no protocol changes.

4. **Graceful Degradation**: Even if an agent doesn't specifically handle the XML tags, the content remains meaningful and actionable.

5. **Extensible**: The tag attributes (`session`, `status`, `type`, `count`) can easily be extended with additional metadata without breaking existing behavior.

### Why Not Option 4 (Different Role)?

Option 4 is semantically the cleanest solution and was seriously considered. However:

1. **SDK Constraints**: The Claude Agent SDK (via `ao-resume`) currently injects messages as user input. Supporting system message injection would require protocol changes.

2. **Executor Abstraction**: Different executors (Claude Code, future alternatives) may have different capabilities for message injection. XML tags work universally.

3. **Effort vs. Benefit**: Option 1 achieves 90% of the benefit with 10% of the effort. The practical disambiguation is sufficient for current needs.

4. **Future Path**: If Option 4 becomes necessary, it can be implemented later as an enhancement. Option 1 is not a dead-end.

## Consequences

### Positive

- **Clear Distinction**: Agents can immediately recognize callback messages by the `<agent-callback>` tag
- **Improved Response Quality**: Agents will process callbacks procedurally rather than conversationally
- **Parseability**: Framework components can reliably extract callback metadata from messages
- **Backward Compatible**: No changes to the callback flow architecture, only message formatting
- **Debugging**: Easier to identify callbacks in conversation logs

### Negative

- **Still User Role**: Message role remains "user", which may still cause some confusion in edge cases
- **Agent Dependency**: Relies on agent training to recognize XML patterns (mitigated by Claude's native XML handling)
- **Template Coupling**: Agents that parse callbacks are coupled to the specific tag format

### Neutral

- **Documentation**: Agent system prompts should mention that callbacks arrive in `<agent-callback>` tags
- **Testing**: Integration tests should verify callback message format

## References

- [ADR-003: Callback-Based Async for Agent Orchestration](./ADR-003-callback-based-async.md)
- [ADR-005: Parent Session Context Propagation](./ADR-005-parent-session-context-propagation.md)
- [Callback Processor Implementation](../../servers/agent-coordinator/services/callback_processor.py)
- [Agent Callback Architecture](../features/agent-callback-architecture.md)
