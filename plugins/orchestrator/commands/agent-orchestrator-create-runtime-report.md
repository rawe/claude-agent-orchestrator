# Create Runtime Report from Agent Sessions

Generate a comprehensive runtime analysis report from CLI agent session files, accounting for parallel execution.

## Instructions

Follow these steps to create a runtime report:

### Step 1: Get Wall Clock Time

Get file timestamps to determine when the workflow started and ended:

```bash
stat -f "%Sm %N" -t "%Y-%m-%d %H:%M:%S" .agent-orchestrator/agent-sessions/*.jsonl | sort
```

The earliest timestamp is the start time, the latest is the end time.

### Step 2: Extract All Session Data

Use this Python script to extract timing data from all sessions:

```bash
python3 << 'EOF'
import json
from pathlib import Path

sessions_dir = Path(".agent-orchestrator/agent-sessions")
session_files = sorted(sessions_dir.glob("*.jsonl"))

results = []

for session_file in session_files:
    name = session_file.stem
    with open(session_file, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get('type') == 'result':
                    results.append({
                        'name': name,
                        'duration_ms': data.get('duration_ms', 0),
                        'duration_s': data.get('duration_ms', 0) / 1000,
                        'api_time_ms': data.get('duration_api_ms', 0),
                        'api_time_s': data.get('duration_api_ms', 0) / 1000,
                        'turns': data.get('num_turns', 0),
                        'cost': data.get('total_cost_usd', 0),
                    })
                    break
            except json.JSONDecodeError:
                continue

for result in results:
    print(f"=== {result['name']} ===")
    print(f"Duration: {result['duration_ms']}ms ({result['duration_s']:.1f}s)")
    print(f"API Time: {result['api_time_ms']}ms ({result['api_time_s']:.1f}s)")
    print(f"Turns: {result['turns']}")
    print(f"Cost: ${result['cost']:.5f}")
    print()

print("=== TOTALS ===")
total_duration = sum(r['duration_ms'] for r in results)
total_api_time = sum(r['api_time_ms'] for r in results)
total_cost = sum(r['cost'] for r in results)
total_turns = sum(r['turns'] for r in results)

print(f"Total Duration: {total_duration}ms ({total_duration/1000:.1f}s, {total_duration/60000:.1f}m)")
print(f"Total API Time: {total_api_time}ms ({total_api_time/1000:.1f}s, {total_api_time/60000:.1f}m)")
print(f"Total Turns: {total_turns}")
print(f"Total Cost: ${total_cost:.5f}")
print(f"Number of Sessions: {len(results)}")
EOF
```

### Step 3: Generate Formatted Report

Use the timestamps from Step 1 and data from Step 2 to create a final report. Update the start/end times based on your actual data:

```bash
python3 << 'EOF'
from datetime import datetime

# UPDATE THESE with actual timestamps from Step 1
start_time = datetime.strptime("2025-11-02 17:35:23", "%Y-%m-%d %H:%M:%S")
end_time = datetime.strptime("2025-11-02 18:04:46", "%Y-%m-%d %H:%M:%S")

wall_clock_seconds = (end_time - start_time).total_seconds()
wall_clock_minutes = wall_clock_seconds / 60

# UPDATE THESE with totals from Step 2
total_agent_time_s = 2837.3
total_agent_time_m = 47.3
total_cost = 2.65816
total_turns = 233

efficiency_gain = ((total_agent_time_m - wall_clock_minutes) / total_agent_time_m) * 100

print("# Runtime Analysis Report")
print()
print("## Wall Clock Time")
print(f"- **Start**: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"- **End**: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"- **Total**: {wall_clock_minutes:.1f} minutes ({wall_clock_seconds:.0f} seconds)")
print()
print("## Overall Summary")
print()
print(f"- **Total Agent Execution Time**: {total_agent_time_s:.1f}s ({total_agent_time_m:.1f} min)")
print(f"- **Actual Wall Clock Time**: {wall_clock_seconds:.0f}s ({wall_clock_minutes:.1f} min)")
print(f"- **Total Cost**: ${total_cost:.5f}")
print(f"- **Total Conversation Turns**: {total_turns}")
print(f"- **Efficiency Gain**: {efficiency_gain:.1f}% faster due to parallel execution")
print(f"- **Time Saved**: {total_agent_time_m - wall_clock_minutes:.1f} minutes")
EOF
```

## Report Output Structure

The report should include:

1. **Wall Clock Time**: Start, end, and total elapsed time
2. **Phase-by-Phase Breakdown**: Individual session metrics with completion timestamps
3. **Overall Summary**:
   - Total agent execution time (sum of all sessions)
   - Actual wall clock time (real elapsed time)
   - Total cost and conversation turns
   - Efficiency gain percentage from parallel execution
   - Time saved by running agents in parallel

## Key Metrics

- **Wall Clock Time**: Real-world time from start to finish
- **Agent Execution Time**: Sum of all individual agent runtimes
- **Efficiency Gain**: Percentage reduction due to parallel execution
- **Time Saved**: Difference between sequential and parallel execution

## Notes

- Use Python heredoc (`<< 'EOF'`) to avoid bash quoting issues
- The script automatically handles missing or incomplete session files
- Efficiency gain > 0% indicates agents ran in parallel
- Update the timestamps and totals in Step 3 with actual values from Steps 1 and 2
