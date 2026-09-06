import httpx
import pytest

from movie_agent.config import Binding, Configuration
from movie_agent.providers import Provider, ProviderError


async def test_lost_submit_response_is_unknown_and_not_retried():
    sent = []

    async def remote(request):
        sent.append(request)
        raise httpx.ReadTimeout("response lost", request=request)

    binding = Binding("test", "minimax_video", "https://api.example.test/v2", "user-model", {}, "test-key")
    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as client:
        with pytest.raises(ProviderError) as caught:
            await Provider(binding, client).submit("video", {"prompt": "A ship departs", "duration": 5})
    assert caught.value.unknown is True
    assert len(sent) == 1
    assert "test-key" not in str(caught.value)


async def test_connect_failure_is_known_unsent_but_read_failure_is_not():
    async def remote(request):
        raise httpx.ConnectTimeout("connection not established", request=request)
    binding = Binding("test", "minimax_video", "https://api.example.test/v2", "MiniMax-H3", {}, "test-key")
    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as client:
        with pytest.raises(ProviderError) as caught:
            await Provider(binding, client).submit("video", {"prompt": "A ship", "duration": 4})
    assert caught.value.unknown is False
    assert caught.value.error_type == "ConnectTimeout"


async def test_720p_is_sent_to_compatible_provider_without_silent_upgrade():
    bodies = []
    async def remote(request):
        import json
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "cloud-720", "task_id": "cloud-768"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as client:
        provider = Provider(Binding("test", "ark", "https://api.example.test", "chosen-model", {}, "test"), client)
        result = await provider.submit("video", {"prompt": "A ship", **Configuration.video_parameters({"duration": 5})})
        assert result.external_id == "cloud-720"
        with pytest.raises(ValueError, match="720P"):
            Configuration.video_parameters({"resolution": "1080p"})
        h3 = Provider(Binding("test", "minimax_video", "https://api.example.test", "MiniMax-H3", {}, "test"), client)
        with pytest.raises(ProviderError, match="支持的分辨率"):
            await h3.submit("video", {"prompt": "A ship", **Configuration.video_parameters({})})
        result = await h3.submit("video", {"prompt": "A ship", **Configuration.video_parameters({}, h3.binding)})
        assert result.external_id == "cloud-768"
        with pytest.raises(ValueError, match="768P"):
            Configuration.video_parameters({"resolution": "2K"}, h3.binding)
        fast = Provider(Binding("test", "ark", "https://api.example.test", "doubao-seedance-2-0-fast-260128", {}, "test"), client)
        with pytest.raises(ProviderError):
            fast.validate("video", {"resolution": "1080p"})
    assert [b["resolution"] for b in bodies] == ["720p", "768P"]


async def test_terminal_ark_failure_is_distinct_from_failed_query():
    async def remote(request):
        return httpx.Response(200, json={"id": "cloud1", "status": "failed", "error": {
            "code": "OutputVideoSensitiveContentDetected.PolicyViolation", "message": "untrusted body test-key"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as client:
        provider = Provider(Binding("test", "ark", "https://api.example.test", "chosen-model", {}, "test-key"), client)
        result = await provider.query("cloud1")
        assert result.state == "failed" and result.failure_code == "content_policy"
        assert "test-key" not in repr(result)
        with pytest.raises(ProviderError):
            await provider.query("wrong-id")
