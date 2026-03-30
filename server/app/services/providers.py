from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(slots=True)
class ProviderResponse:
    content: str


class BaseProvider:
    name = "base"

    async def complete(self, prompt: str, tool_output: str | None = None) -> ProviderResponse:
        raise NotImplementedError


class MockProvider(BaseProvider):
    name = "mock"

    async def complete(self, prompt: str, tool_output: str | None = None) -> ProviderResponse:
        suffix = f" Tool result: {tool_output}." if tool_output else ""
        clean = re.sub(r"\s+", " ", prompt.strip())
        return ProviderResponse(content=f"Mock assistant reply to: {clean}.{suffix}".strip())


class OpenAICompatibleProvider(BaseProvider):
    name = "openai-compatible"

    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete(self, prompt: str, tool_output: str | None = None) -> ProviderResponse:
        content = prompt if tool_output is None else f"{prompt}\n\nTool output:\n{tool_output}"
        payload = {
            "model": self.settings.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful conversation tree assistant. Be concise and explicit.",
                },
                {"role": "user", "content": content},
            ],
        }
        async with httpx.AsyncClient(
            base_url=self.settings.openai_base_url.rstrip("/"),
            timeout=self.settings.request_timeout_seconds,
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
        ) as client:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        message = data["choices"][0]["message"]["content"]
        if isinstance(message, list):
            text = "".join(part.get("text", "") for part in message)
        else:
            text = str(message)
        return ProviderResponse(content=text)


def build_provider() -> BaseProvider:
    settings = get_settings()
    if settings.enable_mock_provider or settings.openai_api_key == "change-me":
        return MockProvider()
    return OpenAICompatibleProvider()


def dump_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)
