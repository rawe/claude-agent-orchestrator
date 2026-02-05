"""
Error Handling Tests

Fast tests that verify executor error handling WITHOUT making Claude API calls.
These tests validate input parsing, schema validation, and error messages.

Run with: uv run --with pytest pytest tests/integration/tests/test_error_handling.py -v
"""

import pytest
import json


class TestInvalidPayload:
    """Tests for invalid JSON payload handling."""

    def test_empty_stdin(self, harness):
        """E01: Empty input raises error."""
        # Run executor with empty string (simulated by passing empty dict won't work,
        # so we need to use a subprocess approach differently)
        # For now, test with whitespace-only which the executor handles
        result = harness.run_executor.__self__._gateway  # Access gateway to verify harness works

        # Actually run with missing required fields
        result = harness.run_executor({})

        assert not result.success
        assert result.exit_code == 1
        # Empty dict is valid JSON but missing required fields
        assert "Missing required field" in result.stderr or "schema_version" in result.stderr

    def test_missing_schema_version(self, harness):
        """E02: Missing schema_version raises error."""
        result = harness.run_executor({
            "mode": "start",
            "session_id": "ses_test123",
            "parameters": {"prompt": "Hello"},
        })

        assert not result.success
        assert result.exit_code == 1
        assert "schema_version" in result.stderr

    def test_missing_session_id(self, harness):
        """E02: Missing session_id raises error."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "parameters": {"prompt": "Hello"},
        })

        assert not result.success
        assert result.exit_code == 1
        assert "session_id" in result.stderr

    def test_missing_parameters(self, harness):
        """E03: Missing parameters raises error."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": "ses_test123",
        })

        assert not result.success
        assert result.exit_code == 1
        assert "parameters" in result.stderr

    def test_missing_mode(self, harness):
        """E03: Missing mode raises error."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "session_id": "ses_test123",
            "parameters": {"prompt": "Hello"},
        })

        assert not result.success
        assert result.exit_code == 1
        assert "mode" in result.stderr

    def test_unsupported_schema_version(self, harness):
        """E04: Unsupported schema version raises error."""
        result = harness.run_executor({
            "schema_version": "99.0",
            "mode": "start",
            "session_id": "ses_test123",
            "parameters": {"prompt": "Hello"},
        })

        assert not result.success
        assert result.exit_code == 1
        assert "Unsupported schema version" in result.stderr
        assert "99.0" in result.stderr

    def test_invalid_mode(self, harness):
        """E05: Invalid mode raises error."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "invalid_mode",
            "session_id": "ses_test123",
            "parameters": {"prompt": "Hello"},
        })

        assert not result.success
        assert result.exit_code == 1
        assert "Invalid mode" in result.stderr or "mode" in result.stderr.lower()


class TestResumeErrors:
    """Tests for resume mode error handling."""

    def test_resume_session_not_found(self, harness):
        """R03: Resume with non-existent session raises error."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": "ses_nonexistent_session_12345",
            "parameters": {"prompt": "Continue"},
        })

        assert not result.success
        assert result.exit_code == 1
        assert "not found" in result.stderr.lower() or "404" in result.stderr

    def test_resume_no_executor_session_id(self, harness):
        """R04: Resume session without executor_session_id raises error."""
        from infrastructure.fake_gateway import SessionState

        # Pre-create a session without executor_session_id
        session = SessionState(
            session_id="ses_no_executor_id",
            executor_session_id=None,  # No executor session ID
            status="pending",
        )
        harness.set_session(session)

        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "resume",
            "session_id": "ses_no_executor_id",
            "parameters": {"prompt": "Continue"},
        })

        assert not result.success
        assert result.exit_code == 1
        assert "executor_session_id" in result.stderr.lower() or "no executor" in result.stderr.lower()


class TestPayloadValidation:
    """Tests for payload field validation."""

    def test_old_schema_version_rejected(self, harness):
        """Old schema versions (1.0, 2.0, 2.1) are rejected."""
        for version in ["1.0", "2.0", "2.1"]:
            result = harness.run_executor({
                "schema_version": version,
                "mode": "start",
                "session_id": "ses_test",
                "parameters": {"prompt": "Hello"},
            })

            assert not result.success, f"Version {version} should be rejected"
            assert "Unsupported schema version" in result.stderr

    def test_valid_minimal_payload_structure(self, harness, session_id):
        """Valid minimal payload has correct structure (may fail at Claude call)."""
        # This test verifies the payload passes validation
        # It will fail when trying to call Claude if no API key is set
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            "session_id": session_id,
            "parameters": {"prompt": "Hello"},
            "project_dir": "/tmp/test",
        })

        # Either succeeds (has API key) or fails at Claude call (not validation)
        if not result.success:
            # Should NOT be a validation error
            assert "Missing required field" not in result.stderr
            assert "Unsupported schema version" not in result.stderr
            assert "Invalid mode" not in result.stderr


class TestExecutorOutput:
    """Tests for executor output format."""

    def test_error_output_goes_to_stderr(self, harness):
        """Errors are written to stderr, not stdout."""
        result = harness.run_executor({
            "schema_version": "99.0",  # Invalid
            "mode": "start",
            "session_id": "ses_test",
            "parameters": {"prompt": "Hello"},
        })

        assert result.exit_code == 1
        assert "Error:" in result.stderr
        # stdout should be empty or minimal for errors
        assert len(result.stdout.strip()) < len(result.stderr.strip())

    def test_exit_code_1_on_validation_error(self, harness):
        """Validation errors return exit code 1."""
        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            # Missing session_id and parameters
        })

        assert result.exit_code == 1


class TestGatewayInteraction:
    """Tests for gateway interaction on errors."""

    def test_no_gateway_calls_on_validation_error(self, harness):
        """No gateway calls are made when payload validation fails."""
        harness.clear()

        result = harness.run_executor({
            "schema_version": "99.0",  # Invalid
            "mode": "start",
            "session_id": "ses_test",
            "parameters": {"prompt": "Hello"},
        })

        assert not result.success
        # No gateway calls should have been made
        assert len(harness.get_gateway_calls()) == 0

    def test_no_bind_on_missing_fields(self, harness):
        """No bind call when required fields are missing."""
        harness.clear()

        result = harness.run_executor({
            "schema_version": "2.2",
            "mode": "start",
            # Missing session_id
            "parameters": {"prompt": "Hello"},
        })

        assert not result.success
        assert len(harness.get_bind_calls()) == 0
