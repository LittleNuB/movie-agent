import asyncio

import httpx
import pytest
from test_api_boundary import MemoryVault

from movie_agent import providers
from movie_agent.config import Binding, Configuration
from movie_agent.jobs import Jobs
from movie_agent.providers import ProviderError
from movie_agent.store import Store


async def test_fake_dns_only_routes_known_provider_hosts_through_explicit_loopback_proxy(monkeypatch):
    async def synthetic_dns(*args, **kwargs):
        return [(2, 1, 6, "", ("198.18.0.241", 443))]
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", synthetic_dns)
    monkeypatch.setattr(providers, "getproxies", lambda: {"https": "http://127.0.0.1:7897"})
    assert await providers.media_proxy("https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/video") == "http://127.0.0.1:7897"
    with pytest.raises(ProviderError):
        await providers.media_proxy("https://unknown.example/video")
    with pytest.raises(ProviderError):
        await providers.media_proxy("https://127.0.0.1/private")
    async def private_dns(*args, **kwargs):
        return [(2, 1, 6, "", ("10.0.0.1", 443))]
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", private_dns)
    with pytest.raises(ProviderError):
        await providers.media_proxy("https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/video")


async def test_saved_result_recovery_does_not_require_the_removed_provider_connection(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    path = tmp_path / "media" / "saved.wav"
    path.parent.mkdir()
    path.write_bytes(b"controlled already-saved file; decode is tested separately")
    class ControlledMedia:
        async def probe(self, source):
            assert source == path
            return {"duration": 1, "streams": []}
    jobs = Jobs(store, Configuration(store, MemoryVault()), ControlledMedia())
    await jobs.client.aclose()
    async def no_request(request):
        raise AssertionError("Saved local output must not query or generate again")
    jobs.client = httpx.AsyncClient(transport=httpx.MockTransport(no_request))
    job = store.put_record(pid, "jobs", {"purpose": "voice", "title": "Saved output", "request_key": "saved1", "args": {},
        "status": "downloading", "epoch": 0, "started": None, "external_id": "known", "binding": {"connection_id": "removed"},
        "result": {"state": "succeeded", "extension": ".wav", "usage": {}, "local_result": "media/saved.wav"}})
    await jobs._run(job["id"])
    assert store.record(job["id"])["status"] == "succeeded"
    assert len(store.record(job["id"])["artifact_ids"]) == 1
    await jobs.close()


async def test_expired_saved_url_is_refreshed_by_query_without_regeneration(tmp_path, monkeypatch):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    calls = []
    async def public_dns(*args, **kwargs):
        return [(2, 1, 6, "", ("8.8.8.8", 443))]
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", public_dns)
    async def remote(request):
        calls.append((request.method, request.url.path))
        if request.url.path == "/old":
            return httpx.Response(403)
        if request.url.path == "/v2/query/video_generation/known":
            return httpx.Response(200, json={"task": {"status": "succeeded", "content": {"url": "https://media.example/new"}}})
        assert request.url.path == "/new"
        return httpx.Response(200, content=b"Controlled download bytes; decode checked separately")
    class ControlledMedia:
        async def probe(self, source):
            assert source.read_bytes().startswith(b"Controlled download")
            return {"duration": 1, "streams": []}
    jobs = Jobs(store, Configuration(store, MemoryVault()), ControlledMedia())
    jobs.binding = lambda job: Binding("test", "minimax_video", "https://api.example/v2", "MiniMax-H3", {}, "test")
    await jobs.client.aclose()
    jobs.client = httpx.AsyncClient(transport=httpx.MockTransport(remote))
    job = store.put_record(pid, "jobs", {"purpose": "video", "title": "Expired URL", "request_key": "expired", "args": {},
        "status": "downloading", "epoch": 0, "started": None, "external_id": "known", "binding": {},
        "result": {"state": "succeeded", "extension": ".mp4", "usage": {}, "urls": ["https://media.example/old"]}})
    await jobs._run(job["id"])
    assert store.record(job["id"])["status"] == "download_failed"
    await jobs.recover(pid, job["id"])
    await jobs._run(job["id"])
    assert store.record(job["id"])["status"] == "succeeded"
    assert calls == [("GET", "/old"), ("GET", "/v2/query/video_generation/known"), ("GET", "/new")]
    await jobs.close()
