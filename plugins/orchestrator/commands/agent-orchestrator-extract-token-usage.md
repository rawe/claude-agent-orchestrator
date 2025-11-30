# Extract Token Usage Statistics from Agent Sessions

Extract context window sizes and token usage statistics from CLI agent session files.

## Context Window Analysis

This script calculates the **context window size** for each agent by summing `input_tokens + cache_creation_input_tokens` across all invocations. This represents the fresh token budget used by each agent.

```bash
python3 << 'EOF'
import json
from pathlib import Path

sessions_dir = Path(".agent-orchestrator/agent-sessions")
results = []

for session_file in sorted(sessions_dir.glob("*.jsonl")):
    agent_name = session_file.stem
    total_fresh_tokens = 0
    num_invocations = 0
    invocation_details = []

    with open(session_file, 'r') as f:
        for line in f:
            if '"type":"result"' not in line:
                continue
            try:
                data = json.loads(line)
                if data.get('type') == 'result':
                    num_invocations += 1
                    usage = data.get('usage', {})
                    input_tokens = usage.get('input_tokens', 0)
                    cache_creation = usage.get('cache_creation_input_tokens', 0)
                    fresh_tokens = input_tokens + cache_creation
                    total_fresh_tokens += fresh_tokens
                    invocation_details.append({
                        'num': num_invocations,
                        'input': input_tokens,
                        'cache_creation': cache_creation,
                        'fresh_tokens': fresh_tokens
                    })
            except json.JSONDecodeError:
                continue

    if num_invocations > 0:
        results.append({
            'name': agent_name,
            'total_fresh_tokens': total_fresh_tokens,
            'num_invocations': num_invocations,
            'invocations': invocation_details
        })

# Detailed per-agent breakdown
print("=" * 80)
print("CONTEXT WINDOW ANALYSIS: FRESH TOKENS (input + cache_creation)")
print("=" * 80)
print()

for result in results:
    print(f"=== {result['name']} ===")
    print(f"Number of Invocations: {result['num_invocations']}")

    if result['num_invocations'] > 1:
        print("\nPer-Invocation Breakdown:")
        for inv in result['invocations']:
            print(f"  Invocation #{inv['num']}:")
            print(f"    Input tokens:          {inv['input']:>10,}")
            print(f"    Cache creation tokens: {inv['cache_creation']:>10,}")
            print(f"    Fresh tokens total:    {inv['fresh_tokens']:>10,}")

    print(f"\nTotal Fresh Tokens (Context Window): {result['total_fresh_tokens']:>10,}")
    print()

# Summary table
print("=" * 80)
print("SUMMARY TABLE")
print("=" * 80)
print()
print("| Agent | Invocations | Total Fresh Tokens (Context) |")
print("|-------|------------:|-----------------------------:|")

for result in results:
    print(f"| {result['name']} | {result['num_invocations']} | "
          f"{result['total_fresh_tokens']:,} |")

print()

# Aggregate statistics
print("=" * 80)
print("AGGREGATE STATISTICS")
print("=" * 80)
total_agents = len(results)
total_invocations = sum(r['num_invocations'] for r in results)
total_fresh_tokens = sum(r['total_fresh_tokens'] for r in results)
avg_fresh_tokens = total_fresh_tokens / total_agents if total_agents > 0 else 0
max_fresh_tokens = max(r['total_fresh_tokens'] for r in results) if results else 0
min_fresh_tokens = min(r['total_fresh_tokens'] for r in results) if results else 0

print(f"Total Agents:                {total_agents}")
print(f"Total Invocations:           {total_invocations}")
print(f"Total Fresh Tokens:          {total_fresh_tokens:,}")
print(f"Average Fresh Tokens/Agent:  {avg_fresh_tokens:,.0f}")
print(f"Maximum Fresh Tokens:        {max_fresh_tokens:,}")
print(f"Minimum Fresh Tokens:        {min_fresh_tokens:,}")
print()
EOF
```

## Key Metrics

- **Fresh Tokens (Context Window)**: `input_tokens + cache_creation_input_tokens`
  - Represents the actual context window size used by the agent
  - Accumulated across all invocations if an agent was called multiple times
  - Excludes cached reads (which don't count toward new context)

- **Invocations**: Number of times an agent was executed
  - Agents may be invoked multiple times if they need additional iterations
  - Context window is summed across all invocations for total agent workload

## Assessment Guidelines

Use these context window sizes to determine if tasks were appropriately sized:

- **< 50K tokens**: Well-sized task, plenty of headroom
- **50K - 100K tokens**: Moderate task size, comfortable range
- **100K - 150K tokens**: Large task, approaching upper limits
- **> 150K tokens**: Very large task, consider splitting into smaller agents

## Notes

- Script efficiently reads only result lines from JSONL files
- Handles multiple invocations per agent automatically
- All calculations handle division by zero safely
- Output includes both detailed breakdown and summary table