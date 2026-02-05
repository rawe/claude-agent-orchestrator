"""
Pytest Configuration for Executor Integration Tests

Provides fixtures for:
- ExecutorTestHarness (session-scoped)
- Payload builders
- Test markers

Usage:
    def test_basic_start(harness):
        result = harness.run_executor(minimal_start_payload())
        assert result.success
"""

import pytest
import sys
from pathlib import Path

# Add infrastructure to path
sys.path.insert(0, str(Path(__file__).parent))

from infrastructure import ExecutorTestHarness, ExecutorResult
from fixtures import (
    minimal_start_payload,
    start_with_blueprint_payload,
    start_with_mcp_payload,
    start_with_output_schema_payload,
    start_with_custom_params_payload,
    resume_payload,
    SIMPLE_NAME_SCHEMA,
    SIMPLE_NUMBER_SCHEMA,
    SUMMARY_SCORE_SCHEMA,
)
from fixtures.payloads import generate_session_id, PROMPTS, get_test_project_dir


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "claude: marks tests that make real Claude API calls (costs money)"
    )
    config.addinivalue_line(
        "markers", "mcp: marks tests that use MCP server integration"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests that take >10 seconds"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their module."""
    for item in items:
        # Tests in test_error_handling.py don't need Claude
        if "test_error_handling" in item.nodeid:
            continue

        # All other integration tests use Claude
        if "integration/tests" in item.nodeid:
            item.add_marker(pytest.mark.claude)

        # MCP tests
        if "test_mcp" in item.nodeid:
            item.add_marker(pytest.mark.mcp)


# ============================================================================
# Harness Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def harness():
    """
    Session-scoped test harness.

    Starts fake gateway and MCP server once per test session.
    All tests share the same harness (cleared between tests).
    """
    h = ExecutorTestHarness()
    h.start()
    yield h
    h.stop()


@pytest.fixture(autouse=True)
def clear_harness(harness):
    """Clear harness recordings before each test."""
    harness.clear()


@pytest.fixture
def fresh_harness():
    """
    Function-scoped harness for tests that need isolation.

    Use this instead of `harness` when tests might interfere with each other.
    """
    h = ExecutorTestHarness()
    h.start()
    yield h
    h.stop()


# ============================================================================
# Session ID Fixture
# ============================================================================

@pytest.fixture
def session_id():
    """Generate a unique session ID for each test."""
    return generate_session_id()


@pytest.fixture
def project_dir():
    """Get a valid project directory for tests."""
    return get_test_project_dir()


# ============================================================================
# Payload Fixtures
# ============================================================================

@pytest.fixture
def basic_start_payload(session_id):
    """Basic start payload with generated session ID."""
    return minimal_start_payload(session_id=session_id)


@pytest.fixture
def mcp_start_payload(session_id, harness):
    """Start payload with MCP server configured."""
    return start_with_mcp_payload(
        session_id=session_id,
        mcp_url=harness.mcp_url,
    )


@pytest.fixture
def schema_start_payload(session_id):
    """Start payload with output schema."""
    return start_with_output_schema_payload(
        session_id=session_id,
        output_schema=SIMPLE_NAME_SCHEMA,
    )


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def prompts():
    """Access to deterministic test prompts."""
    return PROMPTS


@pytest.fixture
def schemas():
    """Access to test schemas."""
    return {
        "simple_name": SIMPLE_NAME_SCHEMA,
        "simple_number": SIMPLE_NUMBER_SCHEMA,
        "summary_score": SUMMARY_SCORE_SCHEMA,
    }
