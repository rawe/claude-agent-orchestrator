You are a helpful agent and use the agent orchestrator mcp wisely to help the user.

You check for available specialist agents before starting an agent.


---

Test the callback delivery mechanism of the agent orchestrator framework:

1. Start 4 child agents in parallel, all with async_mode=true and callback=true:
   - wait-10-sec: Wait for 10 seconds, then respond "Done 10s"
   - wait-15-sec: Wait for 15 seconds, then respond "Done 15s"
   - wait-20-sec: Wait for 20 seconds, then respond "Done 20s"
   - wait-25-sec: Wait for 25 seconds, then respond "Done 25s"

2. Immediately after starting all 4 agents, execute a blocking command: `sleep 20`

3. After the sleep completes, wait for the user to give you further instructions. Do NOT proceed with any analysis yet.

Second prompt (to give after callbacks arrive):

Now review your conversation history and document:
- Which callbacks did you explicitly receive (look for "## Child Result" messages)?
- Which callbacks are missing?

For any missing callbacks, use get_agent_session_status and get_agent_session_result to verify the agents actually completed.

Report your findings: How many callbacks were lost during your busy state vs. delivered successfully?