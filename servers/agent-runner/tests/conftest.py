"""
Shared fixtures for agent-runner tests.

Provides FakeCoordinator, ProcessRegistry, echo executor profile,
and test environment configuration.
"""

import os
import sys
import pytest

# Add lib/ to path so tests can import runner modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
# Add tests/ to path for infrastructure imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fakes.fake_coordinator import FakeCoordinator


@pytest.fixture
def fake_coordinator():
    """FakeCoordinator with fast poll timeout for tests."""
    coordinator = FakeCoordinator(poll_timeout=0.3)
    coordinator.start()
    yield coordinator
    coordinator.stop()


@pytest.fixture
def echo_executor_path():
    """Path to the echo executor script."""
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "executors",
        "echo-executor",
        "ao-echo-exec",
    )


@pytest.fixture
def runner_dir():
    """Path to the agent-runner directory."""
    return os.path.join(os.path.dirname(__file__), "..")
