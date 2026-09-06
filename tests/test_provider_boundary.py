import httpx
import pytest

from movie_agent.config import Binding
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
