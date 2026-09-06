import httpx
import pytest
from test_api_boundary import MemoryVault

from movie_agent.config import Binding, Configuration, ConnectionInput
from movie_agent.jobs import Jobs
from movie_agent.media import Media
from movie_agent.providers import Provider
from movie_agent.store import Store


@pytest.mark.asyncio
async def test_h3_nested_task_receipt_preserves_result_identity():
    async def handler(request):
        assert request.method == "GET"
        return httpx.Response(200, json={"task": {"id": "known-task", "status": "succeeded",
            "content": {"url": "https://media.example.com/movie.mp4"}, "usage": {"output_seconds": 5}}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await Provider(Binding("test", "minimax_video", "https://example.com/v2", "model", {}, "test"), client).query("known-task")
    assert result.state == "succeeded"
    assert result.external_id == "known-task"
    assert result.usage["output_seconds"] == 5


@pytest.mark.asyncio
async def test_interrupted_submission_is_not_resubmitted_and_late_result_stays_candidate(tmp_path):
    store = Store(tmp_path)
    vault = MemoryVault()
    config = Configuration(store, vault)
    config.save(ConnectionInput.model_validate({"id": "video", "name": "Test", "protocol": "minimax_video",
        "base_url": "https://example.com/v2", "api_key": "test", "models": [{"uid": "h3", "id": "model", "capability": "video"}]}))
    config.assign({"video": "video/h3"})
    pid = store.create_project()["id"]
    jobs = Jobs(store, config, Media(store))
    job = await jobs.submit(pid, "video", "Ambiguous submission", "shot-1", {"prompt": "A scene", "parameters": {}, "references": [], "unit_id": "SH1"})
    duplicate = await jobs.submit(pid, "video", "Ambiguous submission", "shot-1", job["args"])
    assert duplicate["id"] == job["id"]
    store.update_record(job["id"], status="submitting")
    await jobs.start()
    assert store.record(job["id"])["status"] == "unknown"
    await jobs.close()
    with pytest.raises(ValueError, match="同一制作对象"):
        await jobs.submit(pid, "video", "Retry under a new request key", "shot-1-v2", job["args"])
    with pytest.raises(ValueError):
        await jobs.recover(pid, job["id"])
    store.stop(pid)
    completed = store.create_artifact(pid, "video", "Late cloud result")
    await jobs._finish(job, [completed["id"]], {"output_seconds": 5})
    assert store.record(job["id"])["candidate_only"] is True
    assert store.project(pid)["adopted"] == {}
    assert store.project(pid)["production_paused"] is True
    assert store.records(pid, "inputs") == []
