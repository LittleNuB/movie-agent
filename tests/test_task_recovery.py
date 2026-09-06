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
    assert len(store.records(pid, "inputs")) == 1
    assert store.records(pid, "inputs")[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_completed_media_keeps_delivery_when_bus_is_unavailable(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    jobs = Jobs(store, Configuration(store, MemoryVault()), Media(store))
    job = await jobs.submit(pid, "compose", "Local render", "render1", {})
    async def broken_bus(*args, **kwargs):
        raise RuntimeError("injected between commit and wake")
    jobs.notify = broken_bus
    artifact = store.create_artifact(pid, "trial", "Actual result identity")
    await jobs._finish(job, [artifact["id"]], {})
    reopened = Store(tmp_path)
    assert reopened.record(job["id"])["status"] == "succeeded"
    assert reopened.record("result-" + job["id"] + "-succeeded")["status"] == "pending"
    await jobs.close()


async def test_policy_failure_recovery_queries_once_and_does_not_resubmit(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    jobs = Jobs(store, Configuration(store, MemoryVault()), Media(store))
    jobs.binding = lambda job: Binding("test", "ark", "https://api.example.test", "chosen-model", {}, "test")
    await jobs.client.aclose()
    methods = []
    async def remote(request):
        methods.append(request.method)
        return httpx.Response(200, json={"id": "cloud1", "status": "failed", "error": {
            "code": "OutputVideoSensitiveContentDetected.PolicyViolation"}})
    jobs.client = httpx.AsyncClient(transport=httpx.MockTransport(remote))
    args = {"prompt": "original request", "references": [], "unit_id": "SH1", "parameters": {"resolution": "720p"}}
    job = store.put_record(pid, "jobs", {"purpose": "video", "title": "Known task", "request_key": "attempt1", "args": args,
        "status": "query_failed", "epoch": 0, "started": None, "external_id": "cloud1", "binding": {}})
    await jobs.recover(pid, job["id"])
    await jobs._run(job["id"])
    final = store.record(job["id"])
    assert final["status"] == "failed" and final["failure_code"] == "content_policy"
    with pytest.raises(ValueError, match="审核拒绝"):
        await jobs.submit(pid, "videoFallback", "Same rejected input", "attempt2", args)
    assert methods == ["GET"]
    await jobs.close()


async def test_queued_high_resolution_request_cannot_post_after_720p_change(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    jobs = Jobs(store, Configuration(store, MemoryVault()), Media(store))
    jobs.binding = lambda job: Binding("test", "ark", "https://api.example.test", "chosen-model", {}, "test")
    await jobs.client.aclose()
    calls = []
    async def remote(request):
        calls.append(request.method)
        raise AssertionError("Old high-resolution request must not reach provider")
    jobs.client = httpx.AsyncClient(transport=httpx.MockTransport(remote))
    job = store.put_record(pid, "jobs", {"purpose": "video", "title": "Old pending request", "request_key": "old-request",
        "args": {"prompt": "A ship", "parameters": {"resolution": "1080p"}}, "status": "pending",
        "epoch": 0, "started": None, "external_id": None, "binding": {}})
    await jobs._run(job["id"])
    assert store.record(job["id"])["status"] == "failed"
    assert "720P" in store.record(job["id"])["error"]
    assert calls == []
    await jobs.close()


async def test_planned_fallback_cannot_silently_submit_primary_model(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    config = Configuration(store, MemoryVault())
    config.save(ConnectionInput.model_validate({"id": "primary", "name": "Primary", "protocol": "minimax_video",
        "base_url": "https://example.com/v2", "no_key": True,
        "models": [{"uid": "h3", "id": "MiniMax-H3", "capability": "video"}]}))
    config.assign({"video": "primary/h3"})
    jobs = Jobs(store, config, Media(store))
    with pytest.raises(ValueError, match="计划型号"):
        await jobs.submit(pid, "video", "Planned fallback", "wrong-purpose", {"expected_model": "chosen-fallback-model"})
    assert store.records(pid, "jobs") == []
    await jobs.close()


async def test_unsubmitted_old_model_does_not_post_after_assignment_changes(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    config = Configuration(store, MemoryVault())
    config.save(ConnectionInput.model_validate({"id": "ark", "name": "Video", "protocol": "ark",
        "base_url": "https://example.com/v3", "no_key": True,
        "models": [{"uid": "old", "id": "old-standard", "capability": "video"},
                   {"uid": "fast", "id": "new-fast", "capability": "video"}]}))
    config.assign({"video": "ark/old"})
    jobs = Jobs(store, config, Media(store))
    job = await jobs.submit(pid, "video", "Queued before change", "old-pending", {"prompt": "A ship", "parameters": {"resolution": "720p"}})
    config.assign({"video": "ark/fast"})
    await jobs.client.aclose()
    calls = []
    async def remote(request):
        calls.append(request.method)
        raise AssertionError("Old unsubmitted model must not be used")
    jobs.client = httpx.AsyncClient(transport=httpx.MockTransport(remote))
    await jobs._run(job["id"])
    assert store.record(job["id"])["status"] == "failed" and calls == []
    assert "模型用途已改变" in store.record(job["id"])["error"]
    await jobs.close()
