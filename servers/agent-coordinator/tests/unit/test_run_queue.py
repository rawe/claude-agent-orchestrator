import threading
from datetime import datetime, timezone

import database
from services.run_queue import RunCreate, RunType, RunStatus
from services.runner_registry import RunnerInfo


def _make_runner(runner_id="runner-A", hostname="host1", **overrides) -> RunnerInfo:
    """Helper to create a RunnerInfo with sensible defaults."""
    ts = datetime.now(timezone.utc).isoformat()
    defaults = dict(
        runner_id=runner_id,
        registered_at=ts,
        last_heartbeat=ts,
        hostname=hostname,
        project_dir="/proj",
        executor_profile="coding",
        executor={"type": "autonomous"},
        tags=[],
        require_matching_tags=False,
    )
    defaults.update(overrides)
    return RunnerInfo(**defaults)


class TestRunQueue:
    def test_add_run(self, fresh_run_queue):
        """Run appears in queue with pending status."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_rq_01", timestamp=ts)

        run_create = RunCreate(
            type=RunType.START_SESSION,
            session_id="ses_rq_01",
            agent_name="test-agent",
            parameters={"prompt": "hello"},
        )
        run = fresh_run_queue.add_run(run_create, run_id="run_rq_01")

        assert run.run_id == "run_rq_01"
        assert run.session_id == "ses_rq_01"
        assert run.status == RunStatus.PENDING
        assert run.parameters == {"prompt": "hello"}
        assert run.agent_name == "test-agent"

        # Verify also retrievable from cache
        cached = fresh_run_queue.get_run("run_rq_01")
        assert cached is not None
        assert cached.status == RunStatus.PENDING

    def test_claim_next_run_with_matching_demands(self, fresh_run_queue):
        """Returns the run when demands match (no demands = any runner)."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_rq_02", timestamp=ts)

        run_create = RunCreate(
            type=RunType.START_SESSION,
            session_id="ses_rq_02",
            parameters={"prompt": "hello"},
        )
        fresh_run_queue.add_run(run_create, run_id="run_rq_02")

        runner = _make_runner(runner_id="runner-A")
        claimed = fresh_run_queue.claim_run(runner)

        assert claimed is not None
        assert claimed.run_id == "run_rq_02"
        assert claimed.status == RunStatus.CLAIMED
        assert claimed.runner_id == "runner-A"
        assert claimed.claimed_at is not None

    def test_claim_next_run_no_match(self, fresh_run_queue):
        """Returns None when demands don't match runner capabilities."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_rq_03", timestamp=ts)

        run_create = RunCreate(
            type=RunType.START_SESSION,
            session_id="ses_rq_03",
            parameters={"prompt": "hello"},
        )
        fresh_run_queue.add_run(run_create, run_id="run_rq_03")

        # Set demands requiring a specific hostname
        fresh_run_queue.set_run_demands("run_rq_03", {"hostname": "special-host"})

        # Runner is on a different host
        runner = _make_runner(runner_id="runner-B", hostname="other-host")
        claimed = fresh_run_queue.claim_run(runner)

        assert claimed is None

        # Run should still be pending
        run = fresh_run_queue.get_run("run_rq_03")
        assert run.status == RunStatus.PENDING

    def test_claim_atomicity(self, fresh_run_queue):
        """Two threads race to claim — exactly one succeeds."""
        ts = datetime.now(timezone.utc).isoformat()
        database.create_session(session_id="ses_rq_04", timestamp=ts)

        run_create = RunCreate(
            type=RunType.START_SESSION,
            session_id="ses_rq_04",
            parameters={"prompt": "hello"},
        )
        fresh_run_queue.add_run(run_create, run_id="run_rq_04")

        results = []

        def claim_as(runner_id):
            runner = _make_runner(runner_id=runner_id)
            result = fresh_run_queue.claim_run(runner)
            results.append(result)

        t1 = threading.Thread(target=claim_as, args=("runner-1",))
        t2 = threading.Thread(target=claim_as, args=("runner-2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        claimed = [r for r in results if r is not None]
        nones = [r for r in results if r is None]
        assert len(claimed) == 1
        assert len(nones) == 1
        assert claimed[0].run_id == "run_rq_04"
        assert claimed[0].status == RunStatus.CLAIMED
