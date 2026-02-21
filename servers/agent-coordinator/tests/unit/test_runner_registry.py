import pytest
from datetime import datetime, timezone, timedelta

from services.runner_registry import (
    RunnerRegistry,
    DuplicateRunnerError,
    RunnerStatus,
    derive_runner_id,
)


class TestRunnerRegistry:
    def test_register_runner(self):
        """Returns runner entry with deterministic ID."""
        registry = RunnerRegistry(heartbeat_timeout_seconds=120)
        runner = registry.register_runner(
            hostname="host1",
            project_dir="/proj",
            executor_profile="coding",
            executor={"type": "autonomous", "command": "/usr/bin/executor"},
            tags=["gpu"],
        )

        assert runner.runner_id.startswith("lnch_")
        assert runner.hostname == "host1"
        assert runner.project_dir == "/proj"
        assert runner.executor_profile == "coding"
        assert runner.status == RunnerStatus.ONLINE
        assert runner.tags == ["gpu"]

        # Verify deterministic: same inputs -> same ID
        expected_id = derive_runner_id("host1", "/proj", "coding", "/usr/bin/executor")
        assert runner.runner_id == expected_id

    def test_duplicate_runner_conflict(self):
        """Second register with same online identity raises DuplicateRunnerError."""
        registry = RunnerRegistry(heartbeat_timeout_seconds=120)
        registry.register_runner(
            hostname="host1",
            project_dir="/proj",
            executor_profile="coding",
            executor={"type": "autonomous", "command": "/usr/bin/executor"},
        )

        with pytest.raises(DuplicateRunnerError):
            registry.register_runner(
                hostname="host1",
                project_dir="/proj",
                executor_profile="coding",
                executor={"type": "autonomous", "command": "/usr/bin/executor"},
            )

    def test_heartbeat_updates_timestamp(self):
        """Heartbeat refreshes last_heartbeat."""
        registry = RunnerRegistry(heartbeat_timeout_seconds=120)
        runner = registry.register_runner(
            hostname="host1",
            project_dir="/proj",
            executor_profile="coding",
            executor={"type": "autonomous", "command": "/usr/bin/executor"},
        )
        original_heartbeat = runner.last_heartbeat

        result = registry.heartbeat(runner.runner_id)
        assert result is True

        updated = registry.get_runner(runner.runner_id)
        assert updated.last_heartbeat >= original_heartbeat

    def test_lifecycle_marks_stale(self):
        """Runner with old timestamp is marked stale after threshold."""
        registry = RunnerRegistry(heartbeat_timeout_seconds=120)
        runner = registry.register_runner(
            hostname="host1",
            project_dir="/proj",
            executor_profile="coding",
            executor={"type": "autonomous", "command": "/usr/bin/executor"},
        )

        # Manually set last_heartbeat to the past (beyond stale threshold)
        old_time = (datetime.now(timezone.utc) - timedelta(seconds=200)).isoformat()
        runner.last_heartbeat = old_time

        stale_ids, removed_ids = registry.update_lifecycle(
            stale_threshold_seconds=120,
            remove_threshold_seconds=600,
        )

        assert runner.runner_id in stale_ids
        assert len(removed_ids) == 0

        # Verify status changed to stale
        updated = registry.get_runner(runner.runner_id)
        assert updated.status == RunnerStatus.STALE
