import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db_module


@pytest.fixture(autouse=True)
def fast_timeouts(monkeypatch):
    monkeypatch.setenv("POLL_TIMEOUT", "1")
    monkeypatch.setenv("HEARTBEAT_INTERVAL", "2")
    monkeypatch.setenv("RUNNER_STALE_THRESHOLD", "5")
    monkeypatch.setenv("RUNNER_REMOVE_THRESHOLD", "10")
    monkeypatch.setenv("RUNNER_LIFECYCLE_INTERVAL", "1")
    monkeypatch.setenv("RUN_NO_MATCH_TIMEOUT", "5")
    monkeypatch.setenv("REAPER_INTERVAL", "1")
    monkeypatch.setenv("REAPER_GRACE_PERIOD", "2")
    monkeypatch.setenv("RUN_RECOVERY_MODE", "none")


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Fresh SQLite DB for each test."""
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    db_module.init_db()
    return test_db


@pytest.fixture
def file_storage(tmp_path, monkeypatch):
    """Fresh file-based storage dirs for each test."""
    ao_root = tmp_path / ".agent-orchestrator"
    agents_dir = ao_root / "agents"
    scripts_dir = ao_root / "scripts"
    capabilities_dir = ao_root / "capabilities"
    mcp_dir = ao_root / "mcp-servers"
    for d in [agents_dir, scripts_dir, capabilities_dir, mcp_dir]:
        d.mkdir(parents=True)
    monkeypatch.setenv("AGENT_ORCHESTRATOR_AGENTS_DIR", str(agents_dir))
    return ao_root


@pytest.fixture
def fresh_run_queue(db_path, monkeypatch):
    """Fresh RunQueue using temp DB."""
    import services.run_queue as rq_module
    monkeypatch.setattr(rq_module, "run_queue", None)
    queue = rq_module.init_run_queue(recovery_mode="none")
    return queue


@pytest.fixture
def coordinator_client(db_path, file_storage, monkeypatch):
    """FastAPI TestClient with fresh DB, fresh file storage, and reset services."""
    from fastapi.testclient import TestClient
    import services.run_queue as rq_module
    import main as coordinator_main

    monkeypatch.setattr(rq_module, "run_queue", None)
    fresh_queue = rq_module.init_run_queue(recovery_mode="none")
    monkeypatch.setattr(coordinator_main, "run_queue", fresh_queue)

    with TestClient(coordinator_main.app) as client:
        yield client
