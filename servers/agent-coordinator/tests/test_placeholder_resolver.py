"""
Tests for PlaceholderResolver.

Tests cover:
- Resolution of ${params.X} placeholders
- Resolution of ${scope.X} placeholders
- Resolution of ${env.X} placeholders
- Resolution of ${runtime.X} placeholders
- Preservation of ${runner.X} placeholders
- Nested dict and list handling
"""

import os
import pytest
import sys
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.placeholder_resolver import PlaceholderResolver


class TestParamsResolution:
    """Tests for ${params.X} placeholder resolution."""

    def test_params_simple(self):
        """Resolves ${params.X} from parameters."""
        resolver = PlaceholderResolver(
            params={"repo_url": "https://github.com/example/repo"},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {
            "name": "test-agent",
            "mcp_servers": {
                "git": {
                    "type": "http",
                    "url": "http://localhost:8000/mcp",
                    "config": {
                        "repo": "${params.repo_url}"
                    }
                }
            }
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["mcp_servers"]["git"]["config"]["repo"] == "https://github.com/example/repo"

    def test_params_missing_keeps_placeholder(self):
        """Unresolved ${params.X} is kept as-is when param not found."""
        resolver = PlaceholderResolver(
            params={},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {"value": "${params.missing}"}
        resolved = resolver.resolve(blueprint)

        assert resolved["value"] == "${params.missing}"


class TestScopeResolution:
    """Tests for ${scope.X} placeholder resolution."""

    def test_scope_simple(self):
        """Resolves ${scope.X} from scope."""
        resolver = PlaceholderResolver(
            params={},
            scope={"context_id": "ctx-789"},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {
            "mcp_servers": {
                "context-store": {
                    "type": "http",
                    "url": "http://localhost:9501/mcp",
                    "config": {
                        "context_id": "${scope.context_id}"
                    }
                }
            }
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["mcp_servers"]["context-store"]["config"]["context_id"] == "ctx-789"


class TestEnvResolution:
    """Tests for ${env.X} placeholder resolution."""

    def test_env_from_environment(self, monkeypatch):
        """Resolves ${env.X} from environment variables."""
        monkeypatch.setenv("TEST_API_KEY", "sk-secret-key-123")

        resolver = PlaceholderResolver(
            params={},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {
            "mcp_servers": {
                "api": {
                    "type": "http",
                    "url": "http://api.example.com",
                    "headers": {
                        "Authorization": "Bearer ${env.TEST_API_KEY}"
                    }
                }
            }
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["mcp_servers"]["api"]["headers"]["Authorization"] == "Bearer sk-secret-key-123"

    def test_env_missing_keeps_placeholder(self, monkeypatch):
        """Unresolved ${env.X} is kept as-is when env var not found."""
        # Ensure variable doesn't exist
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)

        resolver = PlaceholderResolver(
            params={},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {"value": "${env.NONEXISTENT_VAR}"}
        resolved = resolver.resolve(blueprint)

        assert resolved["value"] == "${env.NONEXISTENT_VAR}"


class TestRuntimeResolution:
    """Tests for ${runtime.X} placeholder resolution."""

    def test_runtime_session_id(self):
        """Resolves ${runtime.session_id}."""
        resolver = PlaceholderResolver(
            params={},
            scope={},
            run_id="run_abc123",
            session_id="ses_def456",
        )

        blueprint = {
            "mcp_servers": {
                "orchestrator": {
                    "type": "http",
                    "url": "http://localhost:8765/mcp",
                    "headers": {
                        "X-Session-Id": "${runtime.session_id}"
                    }
                }
            }
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["mcp_servers"]["orchestrator"]["headers"]["X-Session-Id"] == "ses_def456"

    def test_runtime_run_id(self):
        """Resolves ${runtime.run_id}."""
        resolver = PlaceholderResolver(
            params={},
            scope={},
            run_id="run_abc123",
            session_id="ses_def456",
        )

        blueprint = {
            "mcp_servers": {
                "orchestrator": {
                    "config": {
                        "run_id": "${runtime.run_id}"
                    }
                }
            }
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["mcp_servers"]["orchestrator"]["config"]["run_id"] == "run_abc123"


class TestRunnerPlaceholderPreservation:
    """Tests for ${runner.X} placeholder preservation."""

    def test_runner_orchestrator_mcp_url_preserved(self):
        """${runner.orchestrator_mcp_url} is NOT resolved at Coordinator."""
        resolver = PlaceholderResolver(
            params={},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {
            "mcp_servers": {
                "orchestrator": {
                    "type": "http",
                    "url": "${runner.orchestrator_mcp_url}",
                }
            }
        }

        resolved = resolver.resolve(blueprint)

        # Should remain unresolved - Runner will handle it
        assert resolved["mcp_servers"]["orchestrator"]["url"] == "${runner.orchestrator_mcp_url}"


class TestNestedStructures:
    """Tests for handling nested dicts and lists."""

    def test_nested_dict(self):
        """Resolves placeholders in deeply nested dicts."""
        resolver = PlaceholderResolver(
            params={"value": "resolved"},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {
            "level1": {
                "level2": {
                    "level3": {
                        "key": "${params.value}"
                    }
                }
            }
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["level1"]["level2"]["level3"]["key"] == "resolved"

    def test_list_of_strings(self):
        """Resolves placeholders in lists of strings."""
        resolver = PlaceholderResolver(
            params={"arg1": "value1", "arg2": "value2"},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {
            "args": ["--config", "${params.arg1}", "--output", "${params.arg2}"]
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["args"] == ["--config", "value1", "--output", "value2"]

    def test_list_of_dicts(self):
        """Resolves placeholders in lists of dicts."""
        resolver = PlaceholderResolver(
            params={"url1": "http://a.com", "url2": "http://b.com"},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {
            "servers": [
                {"url": "${params.url1}"},
                {"url": "${params.url2}"},
            ]
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["servers"][0]["url"] == "http://a.com"
        assert resolved["servers"][1]["url"] == "http://b.com"


class TestMultiplePlaceholders:
    """Tests for multiple placeholders in single string."""

    def test_multiple_in_same_string(self):
        """Resolves multiple placeholders in same string."""
        resolver = PlaceholderResolver(
            params={"host": "example.com", "port": "8080"},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        blueprint = {
            "url": "http://${params.host}:${params.port}/api"
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["url"] == "http://example.com:8080/api"

    def test_mixed_sources(self):
        """Resolves placeholders from different sources in same blueprint."""
        resolver = PlaceholderResolver(
            params={"name": "test"},
            scope={"tenant": "acme"},
            run_id="run_xyz",
            session_id="ses_abc",
        )

        blueprint = {
            "name": "${params.name}",
            "tenant": "${scope.tenant}",
            "session": "${runtime.session_id}",
            "orchestrator_url": "${runner.orchestrator_mcp_url}",
        }

        resolved = resolver.resolve(blueprint)

        assert resolved["name"] == "test"
        assert resolved["tenant"] == "acme"
        assert resolved["session"] == "ses_abc"
        assert resolved["orchestrator_url"] == "${runner.orchestrator_mcp_url}"  # Preserved


class TestOriginalNotMutated:
    """Tests that original blueprint is not mutated."""

    def test_original_unchanged(self):
        """Original blueprint dict is not modified."""
        resolver = PlaceholderResolver(
            params={"value": "resolved"},
            scope={},
            run_id="run_123",
            session_id="ses_456",
        )

        original = {"key": "${params.value}"}
        resolved = resolver.resolve(original)

        # Original should be unchanged
        assert original["key"] == "${params.value}"
        # Resolved should have new value
        assert resolved["key"] == "resolved"
