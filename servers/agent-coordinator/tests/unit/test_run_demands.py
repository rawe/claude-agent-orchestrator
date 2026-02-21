from datetime import datetime, timezone

from services.run_queue import capabilities_satisfy_demands
from services.runner_registry import RunnerInfo


def _make_runner(**overrides) -> RunnerInfo:
    """Helper to create a RunnerInfo with sensible defaults."""
    ts = datetime.now(timezone.utc).isoformat()
    defaults = dict(
        runner_id="runner-test",
        registered_at=ts,
        last_heartbeat=ts,
        hostname="host1",
        project_dir="/proj",
        executor_profile="coding",
        executor={"type": "autonomous"},
        tags=[],
        require_matching_tags=False,
    )
    defaults.update(overrides)
    return RunnerInfo(**defaults)


class TestDemandMatching:
    def test_empty_demands_matches_any_runner(self):
        """No demands = any runner qualifies."""
        runner = _make_runner()
        assert capabilities_satisfy_demands(runner, None) is True

    def test_hostname_demand_filters(self):
        """Only matching hostname passes."""
        runner = _make_runner(hostname="host1")

        # Matching hostname
        assert capabilities_satisfy_demands(runner, {"hostname": "host1"}) is True

        # Non-matching hostname
        assert capabilities_satisfy_demands(runner, {"hostname": "host2"}) is False

    def test_tag_demand_requires_subset(self):
        """Runner tags must include all demanded tags."""
        runner = _make_runner(tags=["gpu", "linux", "fast"])

        # Subset of runner tags — should match
        assert capabilities_satisfy_demands(runner, {"tags": ["gpu", "linux"]}) is True

        # Single tag — should match
        assert capabilities_satisfy_demands(runner, {"tags": ["gpu"]}) is True

        # Demanded tag not in runner tags — should NOT match
        assert capabilities_satisfy_demands(runner, {"tags": ["gpu", "windows"]}) is False

        # Empty demanded tags — should match
        assert capabilities_satisfy_demands(runner, {"tags": []}) is True
