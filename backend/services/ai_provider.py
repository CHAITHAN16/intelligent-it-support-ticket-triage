from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIProviderError(RuntimeError):
    """Base error for safe handling of AI provider failures."""


class AIProviderNotConfigured(AIProviderError):
    pass


class AIProviderRateLimited(AIProviderError):
    pass


class AIProviderUnavailable(AIProviderError):
    pass


class TextGenerationProvider(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


@dataclass(frozen=True)
class GroqCloudProvider:
    api_key: str
    model: str
    timeout_seconds: float = 20.0

    @classmethod
    def from_environment(cls) -> GroqCloudProvider:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise AIProviderNotConfigured("AI resolution is not configured")
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        if not model:
            raise AIProviderNotConfigured(
                "AI resolution model is not configured")
        return cls(api_key=api_key, model=model)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            }
        ).encode("utf-8")
        request = Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read())
        except HTTPError as error:
            if error.code == 429:
                raise AIProviderRateLimited(
                    "AI provider rate limit reached") from None
            raise AIProviderUnavailable("AI provider request failed") from None
        except (TimeoutError, URLError):
            raise AIProviderUnavailable(
                "AI provider timed out or is unavailable") from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise AIProviderUnavailable(
                "AI provider returned an invalid response") from None

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise AIProviderUnavailable(
                "AI provider returned an invalid response") from None
        if not isinstance(content, str) or not content.strip():
            raise AIProviderUnavailable(
                "AI provider returned an empty response")
        return content.strip()
