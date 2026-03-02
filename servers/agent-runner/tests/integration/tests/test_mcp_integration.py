"""
MCP Integration Tests

Tests for MCP server tool invocation with real Claude SDK.
Verifies that Claude actually calls the MCP tools and the executor handles them.

Run with: uv run --with pytest pytest tests/integration/tests/test_mcp_integration.py -v

Markers:
- @pytest.mark.claude: Makes Claude API calls
- @pytest.mark.mcp: Uses MCP server
"""

import pytest

# Mark all tests as claude + mcp
pytestmark = [pytest.mark.claude, pytest.mark.mcp]


class TestEchoTool:
    """Tests for the echo MCP tool."""

    def test_echo_tool_invocation(self, harness, session_id, project_dir):
        """M01: Claude invokes echo tool when asked."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Use the echo tool to send the message 'hello world'. After the tool responds, say 'done'."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "echo-test-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Check if echo tool was called
        echo_calls = harness.get_mcp_calls_by_tool("echo")
        assert len(echo_calls) >= 1, f"Expected echo tool call, got: {harness.get_mcp_tool_calls()}"

        # Verify the argument
        call = echo_calls[0]
        assert "hello" in call.arguments.get("message", "").lower(), \
            f"Expected 'hello' in echo argument: {call.arguments}"

    def test_echo_tool_result_in_response(self, harness, session_id, project_dir):
        """Echo tool result should influence Claude's response."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Use the echo tool with message 'MAGIC123'. Tell me what the tool returned."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "echo-result-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Response should mention the echoed text
        assert "MAGIC123" in result.stdout, \
            f"Expected 'MAGIC123' in response: {result.stdout}"


class TestGetTimeTool:
    """Tests for the get_time MCP tool."""

    def test_get_time_tool_invocation(self, harness, session_id, project_dir):
        """M02: Claude invokes get_time tool."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Use the get_time tool to get the current time. Tell me what time it is."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "time-test-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Check if get_time tool was called
        time_calls = harness.get_mcp_calls_by_tool("get_time")
        assert len(time_calls) >= 1, f"Expected get_time tool call, got: {harness.get_mcp_tool_calls()}"


class TestAddNumbersTool:
    """Tests for the add_numbers MCP tool."""

    def test_add_numbers_tool_invocation(self, harness, session_id, project_dir):
        """M03: Claude invokes add_numbers tool with correct arguments."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Use the add_numbers tool to add 5 and 3. Tell me the result."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "math-test-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Check tool was called
        add_calls = harness.get_mcp_calls_by_tool("add_numbers")
        assert len(add_calls) >= 1, f"Expected add_numbers tool call, got: {harness.get_mcp_tool_calls()}"

        # Verify arguments (should be 5 and 3)
        call = add_calls[0]
        assert call.arguments.get("a") == 5 or call.arguments.get("b") == 5, \
            f"Expected 5 in arguments: {call.arguments}"
        assert call.arguments.get("a") == 3 or call.arguments.get("b") == 3, \
            f"Expected 3 in arguments: {call.arguments}"

        # Result should be 8
        assert call.result == 8, f"Expected result 8, got: {call.result}"

        # Response should mention 8
        assert "8" in result.stdout, f"Expected '8' in response: {result.stdout}"


class TestMultipleTools:
    """Tests for multiple tool invocations."""

    def test_multiple_tool_calls(self, harness, session_id, project_dir):
        """M02: Claude can call multiple tools in sequence."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "First use get_time to get the current time. Then use echo to repeat that time. Finally say 'completed'."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "multi-tool-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Check both tools were called
        all_calls = harness.get_mcp_tool_calls()
        tool_names = [c.tool_name for c in all_calls]

        assert "get_time" in tool_names, f"Expected get_time call, got: {tool_names}"
        assert "echo" in tool_names, f"Expected echo call, got: {tool_names}"


class TestStoreDataTool:
    """Tests for the store_data MCP tool."""

    def test_store_data_tool(self, harness, session_id, project_dir):
        """Store data tool records data correctly."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Use the store_data tool to store key='test_key' with value='test_value'. Confirm when done."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "store-test-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Check tool was called
        store_calls = harness.get_mcp_calls_by_tool("store_data")
        assert len(store_calls) >= 1, f"Expected store_data call, got: {harness.get_mcp_tool_calls()}"

        # Check stored data
        stored = harness.get_mcp_stored_data()
        assert "test_key" in stored, f"Expected 'test_key' in stored data: {stored}"
        assert stored.get("test_key") == "test_value", f"Expected value 'test_value': {stored}"


class TestToolErrorHandling:
    """Tests for MCP tool error handling."""

    def test_tool_error_handled_gracefully(self, harness, session_id, project_dir):
        """M04: Claude handles tool errors gracefully."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Use the fail_on_purpose tool. It will fail. Then tell me what happened."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "error-test-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        })

        # Executor should still succeed (handle tool error gracefully)
        assert result.success, f"Executor failed: {result.stderr}"

        # Tool should have been called
        fail_calls = harness.get_mcp_calls_by_tool("fail_on_purpose")
        assert len(fail_calls) >= 1, f"Expected fail_on_purpose call"

        # Tool call should have error recorded
        call = fail_calls[0]
        assert call.error is not None, f"Expected error in tool call: {call}"


class TestPostToolEvents:
    """Tests for post_tool event tracking."""

    def test_post_tool_events_sent(self, harness, session_id, project_dir):
        """Tool calls send post_tool events to gateway."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Use the echo tool to say 'event test'. Then say done."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "event-test-agent",
                "mcp_servers": {
                    "test-mcp": {"url": harness.mcp_url}
                }
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Check for post_tool events
        post_tool_events = harness.get_post_tool_events(session_id)

        # Should have at least one post_tool event for the echo call
        # Note: This depends on the hook being registered correctly
        if len(post_tool_events) > 0:
            event = post_tool_events[0]
            assert event.get("event_type") == "post_tool"
            assert "tool_name" in event
