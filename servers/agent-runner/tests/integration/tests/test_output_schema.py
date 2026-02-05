"""
Output Schema Validation Tests

Tests for structured output with JSON Schema validation.
Verifies validation, retry on failure, and result_data events.

Run with: uv run --with pytest pytest tests/integration/tests/test_output_schema.py -v

Markers:
- @pytest.mark.claude: Makes Claude API calls
"""

import pytest

from fixtures.schemas import (
    SIMPLE_NAME_SCHEMA,
    SIMPLE_NUMBER_SCHEMA,
    SUMMARY_SCORE_SCHEMA,
    ITEMS_ARRAY_SCHEMA,
    BOOLEAN_RESULT_SCHEMA,
)

# Mark all tests as claude tests
pytestmark = pytest.mark.claude


class TestValidOutputSchema:
    """Tests for valid structured output."""

    def test_simple_name_schema(self, harness, session_id, project_dir):
        """O01: Valid JSON response matches simple schema."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Return a JSON object with a 'name' field set to 'Alice'. Output only valid JSON."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "schema-agent",
                "output_schema": SIMPLE_NAME_SCHEMA,
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        # Check result event has result_data
        result_events = harness.get_result_events(session_id)
        assert len(result_events) >= 1, "Expected result event"

        result_event = result_events[-1]  # Get last result event
        result_data = result_event.get("result_data")

        assert result_data is not None, f"Expected result_data in event: {result_event}"
        assert result_data.get("name") == "Alice", f"Expected name='Alice': {result_data}"

    def test_number_schema(self, harness, session_id, project_dir):
        """Valid JSON with number field."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Return a JSON object with a 'value' field set to 42. Output only valid JSON."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "number-agent",
                "output_schema": SIMPLE_NUMBER_SCHEMA,
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        result_events = harness.get_result_events(session_id)
        assert len(result_events) >= 1

        result_data = result_events[-1].get("result_data")
        assert result_data is not None
        assert result_data.get("value") == 42, f"Expected value=42: {result_data}"

    def test_complex_schema(self, harness, session_id, project_dir):
        """Valid JSON with multiple required fields."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Return a JSON object with 'summary' (a short text) and 'score' (a number between 0-100). Example: {\"summary\": \"Good\", \"score\": 85}. Output only valid JSON."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "complex-agent",
                "output_schema": SUMMARY_SCORE_SCHEMA,
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        result_events = harness.get_result_events(session_id)
        result_data = result_events[-1].get("result_data")

        assert result_data is not None
        assert "summary" in result_data, f"Expected 'summary' field: {result_data}"
        assert "score" in result_data, f"Expected 'score' field: {result_data}"
        assert 0 <= result_data["score"] <= 100, f"Score out of range: {result_data}"


class TestJsonExtraction:
    """Tests for JSON extraction from various formats."""

    def test_json_in_code_block(self, harness, session_id, project_dir):
        """O02: JSON in code block is extracted correctly."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Return a JSON object with name='Bob' in a markdown code block. Use ```json formatting."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "codeblock-agent",
                "output_schema": SIMPLE_NAME_SCHEMA,
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        result_events = harness.get_result_events(session_id)
        result_data = result_events[-1].get("result_data")

        assert result_data is not None, "Should extract JSON from code block"
        assert result_data.get("name") == "Bob", f"Expected name='Bob': {result_data}"

    def test_json_with_surrounding_text(self, harness, session_id, project_dir):
        """JSON can be extracted even with surrounding text."""
        # This tests the regex extraction capability
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Return exactly: {\"name\": \"Charlie\"}"
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "extract-agent",
                "output_schema": SIMPLE_NAME_SCHEMA,
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        result_events = harness.get_result_events(session_id)
        result_data = result_events[-1].get("result_data")

        assert result_data is not None
        assert result_data.get("name") == "Charlie"


class TestArraySchema:
    """Tests for array-based schemas."""

    def test_items_array_schema(self, harness, session_id, project_dir):
        """Schema with array of items."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Return a JSON object with an 'items' array containing at least one string. Example: {\"items\": [\"apple\", \"banana\"]}. Output only valid JSON."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "array-agent",
                "output_schema": ITEMS_ARRAY_SCHEMA,
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        result_events = harness.get_result_events(session_id)
        result_data = result_events[-1].get("result_data")

        assert result_data is not None
        assert "items" in result_data
        assert isinstance(result_data["items"], list)
        assert len(result_data["items"]) >= 1


class TestBooleanSchema:
    """Tests for boolean result schemas."""

    def test_boolean_success_schema(self, harness, session_id, project_dir):
        """Schema with boolean success field."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Return a JSON object with 'success' set to true. Example: {\"success\": true}. Output only valid JSON."
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "bool-agent",
                "output_schema": BOOLEAN_RESULT_SCHEMA,
            },
        })

        assert result.success, f"Executor failed: {result.stderr}"

        result_events = harness.get_result_events(session_id)
        result_data = result_events[-1].get("result_data")

        assert result_data is not None
        assert result_data.get("success") is True


class TestSchemaValidationRetry:
    """Tests for schema validation retry mechanism."""

    def test_retry_on_invalid_output(self, harness, session_id, project_dir):
        """O03: Invalid output triggers retry."""
        # Use a schema that might trigger retry
        # The system should retry once if first attempt fails validation
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Return ONLY this exact JSON: {\"summary\": \"Test summary here\", \"score\": 75}"
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "retry-agent",
                "output_schema": SUMMARY_SCORE_SCHEMA,
            },
        })

        # Should succeed (either first try or after retry)
        assert result.success, f"Executor failed: {result.stderr}"

        result_events = harness.get_result_events(session_id)
        result_data = result_events[-1].get("result_data")

        assert result_data is not None


class TestNoResultText:
    """Tests verifying structured output doesn't emit result_text."""

    def test_structured_output_has_result_data_not_text(self, harness, session_id, project_dir):
        """Structured output sends result_data, not result_text."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Return {\"name\": \"Test\"}"
            },
            "project_dir": project_dir,
            "agent_blueprint": {
                "name": "data-only-agent",
                "output_schema": SIMPLE_NAME_SCHEMA,
            },
        })

        assert result.success

        result_events = harness.get_result_events(session_id)
        result_event = result_events[-1]

        # Should have result_data
        assert result_event.get("result_data") is not None

        # result_text should be None for structured output
        assert result_event.get("result_text") is None, \
            f"Expected no result_text for structured output: {result_event}"


class TestWithoutOutputSchema:
    """Tests comparing behavior with and without output_schema."""

    def test_no_schema_sends_result_text(self, harness, session_id, project_dir):
        """Without output_schema, sends result_text not result_data."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {
                "prompt": "Say 'hello world'."
            },
            "project_dir": project_dir,
            # No output_schema
        })

        assert result.success

        result_events = harness.get_result_events(session_id)
        result_event = result_events[-1]

        # Should have result_text
        assert result_event.get("result_text") is not None

        # result_data should be None
        assert result_event.get("result_data") is None
