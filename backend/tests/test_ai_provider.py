import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from services.ai_provider import (
    AIProviderNotConfigured,
    AIProviderRateLimited,
    AIProviderUnavailable,
    GroqCloudProvider,
)


def test_provider_reads_configuration_from_environment(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "test-model")

    provider = GroqCloudProvider.from_environment()

    assert provider.api_key == "test-key"
    assert provider.model == "test-model"


def test_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(AIProviderNotConfigured):
        GroqCloudProvider.from_environment()


def test_provider_sends_chat_request_and_returns_content(monkeypatch):
    observed = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "  Try again.  "}}]}).encode()

    def fake_urlopen(request, timeout):
        observed["url"] = request.full_url
        observed["headers"] = request.headers
        observed["body"] = json.loads(request.data)
        observed["timeout"] = timeout
        return Response()

    monkeypatch.setattr("services.ai_provider.urlopen", fake_urlopen)
    provider = GroqCloudProvider(api_key="test-key", model="test-model", timeout_seconds=4)

    assert provider.generate("system", "user") == "Try again."
    assert observed["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert observed["headers"]["Authorization"] == "Bearer test-key"
    assert observed["body"]["model"] == "test-model"
    assert observed["body"]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    assert observed["timeout"] == 4


def test_provider_handles_rate_limit_without_exposing_provider_body(monkeypatch):
    def fail_urlopen(*_args, **_kwargs):
        raise HTTPError("url", 429, "limited", {}, BytesIO(b"sensitive provider detail"))

    monkeypatch.setattr("services.ai_provider.urlopen", fail_urlopen)

    with pytest.raises(AIProviderRateLimited, match="rate limit") as error:
        GroqCloudProvider(api_key="test-key", model="test-model").generate("system", "user")
    assert "sensitive" not in str(error.value)


def test_provider_handles_timeout_and_invalid_response(monkeypatch):
    def timeout(*_args, **_kwargs):
        raise TimeoutError()

    monkeypatch.setattr("services.ai_provider.urlopen", timeout)
    with pytest.raises(AIProviderUnavailable, match="timed out"):
        GroqCloudProvider(api_key="test-key", model="test-model").generate("system", "user")

    class InvalidResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"{}"

    monkeypatch.setattr("services.ai_provider.urlopen", lambda *_args, **_kwargs: InvalidResponse())
    with pytest.raises(AIProviderUnavailable, match="invalid response"):
        GroqCloudProvider(api_key="test-key", model="test-model").generate("system", "user")