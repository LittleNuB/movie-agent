import asyncio

import pytest
from test_api_boundary import MemoryVault

from movie_agent.config import Configuration
from movie_agent.runtime import Runtime
from movie_agent.store import Store


async def test_failed_turn_preserves_a_new_message_arriving_during_failure(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    store.accept_message(pid, "old", "First input", [])
    runtime = Runtime(store, Configuration(store, MemoryVault()))
    async def failing_agent(*args):
        store.accept_message(pid, "new", "New input during old failure", [])
        raise RuntimeError("Injected SDK connection failure")
    runtime.make_agent = failing_agent
    await runtime.bus.__aenter__()
    await runtime._run(pid)
    assert store.record("input-old")["status"] == "failed"
    assert store.record("input-new")["status"] == "pending"
    assert store.record("new")["text"] == "New input during old failure"
    await runtime.bus.aclose()


async def test_late_media_delivery_waits_during_stop_and_wakes_after_resume(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    store.stop(pid)
    job = store.put_record(pid, "jobs", {"status": "running"})
    store.update_record(job["id"], status="succeeded", delivery=("late-result", "Keep this result", "media_task"))
    runtime = Runtime(store, Configuration(store, MemoryVault()))
    woke = asyncio.Event()
    async def controlled_run(project_id):
        assert project_id == pid
        store.update_record("late-result", status="done")
        woke.set()
    runtime._run = controlled_run
    await runtime.start()
    await asyncio.sleep(0.6)
    assert not woke.is_set()
    store.update_project(pid, production_paused=False, status="idle")
    await asyncio.wait_for(woke.wait(), timeout=3)
    await runtime.close()


async def test_delegation_cannot_relabel_old_observations_as_the_new_script(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    original = store.create_artifact(pid, "script", "Old")
    store.adopt(pid, original["id"], None)
    observed = store.project(pid)["adopted"]
    new = store.create_artifact(pid, "script", "New")
    store.adopt(pid, new["id"], original["id"])
    runtime = Runtime(store, Configuration(store, MemoryVault()))
    with pytest.raises(ValueError, match="采用版本已改变"):
        await runtime.delegate(pid, "visual", "Plan the old script", basis=observed)
    assert store.records(pid, "runs") == []
